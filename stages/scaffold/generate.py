"""Build product/ from app.json and ui.json. Same bytes in, same bytes out."""

import json
import os
import re
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from contracts.stage import StageOutput

from .api import api_cases, dbcontext_cs, endpoints_cs, notifications_cs, timers_cs
from .domain import SCALARS, hook_input, model_cs, param_type, params_cs
from .models import HookContract, HookExample, HookSpec

# ponytail: kafka topics and EF migrations are out of this stage.

_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_METHODS = {
    "calculator": "Evaluate",
    "validator": "Validate",
    "decider": "Decide",
    "policy": "Allow",
    "reaction": "React",
}
_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char",
    "checked", "class", "const", "continue", "decimal", "default", "delegate",
    "do", "double", "else", "enum", "event", "explicit", "extern", "false",
    "finally", "fixed", "float", "for", "foreach", "goto", "if", "implicit",
    "in", "int", "interface", "internal", "is", "lock", "long", "namespace",
    "new", "null", "object", "operator", "out", "override", "params", "private",
    "protected", "public", "readonly", "ref", "return", "sbyte", "sealed",
    "short", "sizeof", "stackalloc", "static", "string", "struct", "switch",
    "this", "throw", "true", "try", "typeof", "uint", "ulong", "unchecked",
    "unsafe", "ushort", "using", "virtual", "void", "volatile", "while",
}


def execute(inp, workspace: Path, llm, sandbox) -> StageOutput:
    """Scaffold product/. llm and sandbox are unused."""
    _ = (llm, sandbox)
    workspace = Path(workspace)
    artifacts = _mapping(_field(inp, "artifacts"), "artifacts")
    app = _load(workspace, _rel(artifacts, "app", "app.json"), "app.json")
    ui = _load(workspace, _rel(artifacts, "ui", "ui.json"), "ui.json")
    _copy_template(workspace)
    _write(workspace, "product/backend/src/App.Domain/Generated/Model.cs", model_cs(app))
    _write(workspace, "product/backend/src/App.Domain/Generated/Params.cs", params_cs(app))
    _write(workspace, "product/infra/roles.json", _dump(sorted((app.get("roles") or {}).keys())))
    built = _hooks(app)
    for hook in built:
        _write(workspace, f"product/backend/src/App.Domain/Generated/I{hook['name']}Hook.cs", hook["interface"])
        _write(
            workspace,
            f"product/backend/src/App.Domain/Hooks/{hook['name']}Hook.cs",
            hook["stub"],
            keep=True,
        )
    _write(workspace, "product/hooks.json", _dump(_normalize([hook["spec"] for hook in built])))
    _write(workspace, "product/openapi.json", _dump(_openapi(app)))
    _write(workspace, "product/backend/src/App.Api/seed.json", _dump(_seed(app)))
    screens = []
    for target, mobile in (("admin-web", False), ("mobile-web", True)):
        chosen = _web_screens(ui, mobile=mobile)
        screens += chosen
        _write(workspace, f"product/{target}/src/app/generated/routes.ts", _routes_ts(chosen))
        _write(workspace, f"product/{target}/src/app/generated/model.ts", _model_ts(app, ui, chosen, mobile))
        for name, screen in chosen:
            _write(
                workspace,
                f"product/{target}/e2e/pages/{name}.ts",
                _page_ts(name, _testids(screen)),
            )
    _write(workspace, "product/backend/src/App.Api/Features/Generated/Endpoints.cs", endpoints_cs(app))
    _write(workspace, "product/backend/src/App.Infrastructure/Generated/AppDbContext.Model.cs", dbcontext_cs(app))
    _write(workspace, "product/backend/src/App.Infrastructure/Generated/Notifications.cs", notifications_cs(app))
    _write(workspace, "product/backend/src/App.Infrastructure/Generated/Timers.cs", timers_cs(app))
    _write(workspace, "product/backend/tests/App.Generated.Tests/cases/api.json", _dump(api_cases(app)))
    entities = app.get("entities") if isinstance(app.get("entities"), dict) else {}
    summary = "Scaffolded " + ", ".join((
        _counted(len(built), "hook", "hooks"),
        _counted(len(entities), "entity", "entities"),
        _counted(len(screens), "screen", "screens"),
    )) + "."
    return StageOutput(
        artifacts={
            "hooks": "product/hooks.json",
            "openapi": "product/openapi.json",
            "product": "product",
        },
        summary=summary,
    )


def _counted(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _field(inp, key):
    if isinstance(inp, Mapping):
        try:
            return inp[key]
        except KeyError:
            raise ValueError(f"missing {key}") from None
    try:
        return getattr(inp, key)
    except AttributeError:
        raise ValueError(f"missing {key}") from None


def _mapping(value, label):
    if isinstance(value, Mapping):
        return value
    raise ValueError(f"{label} must be a mapping")


def _rel(artifacts, key: str, label: str) -> str:
    try:
        rel = artifacts[key]
    except KeyError:
        raise ValueError(f"missing {label}") from None
    if not isinstance(rel, str) or rel == "":
        raise ValueError(f"missing {label}")
    return rel


def _load(workspace: Path, rel: str, label: str) -> dict:
    path = _inside(workspace, rel)
    if not path.is_file():
        raise ValueError(f"missing {label}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label}") from exc
    if not isinstance(data, dict):
        _contract_error(f"{label} must be an object")
    version = data.get("schema_version")
    if type(version) is not int or version != 1:
        _contract_error(f"{label} schema_version must be 1")
    return data


def _contract_error(message: str):
    found = None
    try:
        from contracts.stage import ContractError as found
    except ImportError:
        found = None
    if isinstance(found, type) and issubclass(found, BaseException):
        raise found(message)
    raise ValueError(message)


def _inside(workspace: Path, rel: str) -> Path:
    if rel.startswith(("/", "\\")):
        raise ValueError(f"path escapes workspace: {rel}")
    root = workspace.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"path escapes workspace: {rel}")
    return path


def _write(workspace: Path, rel: str, text: str, *, keep: bool = False) -> None:
    if not rel.startswith("product/"):
        raise ValueError(f"refusing to write outside product: {rel}")
    dest = _inside(workspace, rel)
    if keep and dest.is_file():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8", newline="\n")


def _dump(data) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "templates" / "product"


# ponytail: node_modules and compiler output are not the template. Copy source only.
_SKIP_DIRS = {".git", "__pycache__", "bin", "obj", "node_modules", "dist", ".angular", "coverage", ".venv"}


def _template_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in _SKIP_DIRS)
        for name in sorted(filenames):
            src = Path(dirpath) / name
            if src.is_symlink():
                continue
            yield src


def _skip_copy(rel: Path) -> bool:
    # ponytail: skip compiler output; the template that matters is source.
    return any(part in _SKIP_DIRS for part in rel.parts)


def _preserved(rel: Path) -> bool:
    parts = rel.parts
    if any(part in {"Hooks", "hooks", "Custom", "custom"} for part in parts):
        return True
    return any(parts[i] == "db" and parts[i + 1] == "seed" for i in range(len(parts) - 1))


def _copy_template(workspace: Path) -> None:
    root = _template_root()
    if not (root / "backend" / "App.sln").is_file():
        return
    for src in _template_files(root):
        rel = src.relative_to(root)
        if _skip_copy(rel):
            continue
        dest = _inside(workspace, (Path("product") / rel).as_posix())
        if dest.exists() and _preserved(rel):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)


def template_copy_paths() -> list[str]:
    """Workspace-relative files a first execute copies from templates/product."""
    root = _template_root()
    if not (root / "backend" / "App.sln").is_file():
        return []
    paths = []
    for src in _template_files(root):
        rel = src.relative_to(root)
        if _skip_copy(rel):
            continue
        paths.append("product/" + rel.as_posix())
    return paths


def _ident(text: str) -> str:
    if not _ID.fullmatch(text):
        _contract_error(f"name is not an identifier: {text}")
    return text


def _strs(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _contract_error("expected an array of strings")
    return value


def _camel(name: str) -> str:
    return name[:1].lower() + name[1:]


def _return_type(kind: str, hook: dict) -> str:
    if kind != "calculator":
        return {"validator": "bool", "policy": "bool", "decider": "string", "reaction": "void"}[kind]
    out = hook.get("out")
    if not isinstance(out, str) or out == "":
        return "DateTimeOffset"
    if out in SCALARS:
        return SCALARS[out]
    if _ID.fullmatch(out):
        return out
    return "DateTimeOffset"


def _parameters(kind: str, hook: dict, app: dict) -> list[tuple[str, str]]:
    used: set[str] = set()
    ordered: list[tuple[str, str]] = []

    def add(cs_type: str, raw: str, *, camel: bool) -> None:
        name = _camel(raw) if camel else raw
        if name in _KEYWORDS:
            name += "Arg"
        base = name
        number = 2
        while name in used:
            name = f"{base}{number}"
            number += 1
        used.add(name)
        ordered.append((cs_type, name))

    if kind == "decider":
        add("string", "initialState", camel=False)
    for token in sorted(set(_strs(hook.get("in")))):
        cs_type, name = hook_input(token, app)
        add(cs_type, name, camel=False)
    params = app.get("params") if isinstance(app.get("params"), dict) else {}
    for param in sorted(set(_strs(hook.get("params")))):
        _ident(param)
        add(param_type(params.get(param)), param, camel=False)
    return ordered


def _body(kind: str, ret: str) -> str:
    if kind == "calculator":
        return f"return default({ret});"
    if kind in {"validator", "policy"}:
        return "return true;"
    if kind == "decider":
        return "return initialState;"
    return "return;"


def _hooks(app: dict) -> list[dict]:
    hooks = app.get("hooks") or {}
    if not isinstance(hooks, dict):
        _contract_error("hooks must be an object")
    built = []
    for name in sorted(hooks):
        hook = hooks[name]
        if not isinstance(hook, dict):
            _contract_error("hook must be an object")
        _ident(name)
        kind = hook.get("kind")
        if kind not in _METHODS:
            _contract_error(f"unknown hook kind: {kind}")
        ret = _return_type(kind, hook)
        method = _METHODS[kind]
        params = _parameters(kind, hook, app)
        rendered = ", ".join(f"{cs_type} {param}" for cs_type, param in params)
        signature = f"public {ret} {method}({rendered})"
        rule = hook.get("rule") if isinstance(hook.get("rule"), str) else ""
        refs = sorted(set(_strs(hook.get("traces"))) | ({rule} if rule else set()))
        spec = {
            "allowed_api": sorted(set(_strs(hook.get("in"))) | set(_strs(hook.get("params")))),
            "contract": {"post": [], "pre": [], "summary": rule},
            "examples": [],
            "file": f"backend/src/App.Domain/Hooks/{name}Hook.cs",
            "id": name,
            "kind": kind,
            "language": "csharp",
            "max_lines": 60,
            "refs": refs,
            "signature": signature,
            "stub": "neutral",
            "method": method,
            "returns": ret,
            "parameters": [
                {"name": param, "type": cs_type,
                 "source": "param" if param in set(_strs(hook.get("params"))) else "input"}
                for cs_type, param in params
            ],
        }
        built.append({
            "name": name,
            "spec": spec,
            "interface": (
                "namespace App.Domain.Generated;\n"
                "\n"
                f"public interface I{name}Hook\n"
                "{\n"
                f"    {ret} {method}({rendered});\n"
                "}\n"
            ),
            "stub": (
                "namespace App.Domain.Hooks;\n"
                "\n"
                f"public sealed class {name}Hook : App.Domain.Generated.I{name}Hook\n"
                "{\n"
                f"    {signature}\n"
                "    {\n"
                f"        {_body(kind, ret)}\n"
                "    }\n"
                "}\n"
            ),
        })
    return built


def _normalize(specs: list[dict]) -> list[dict]:
    try:
        from contracts.hooks import HooksFile
    except ImportError:
        return [_local_spec(spec) for spec in specs]
    return HooksFile.model_validate(specs).model_dump(mode="json")


def _local_spec(spec: dict) -> dict:
    model = HookSpec(
        id=spec["id"],
        file=spec["file"],
        language=spec["language"],
        kind=spec["kind"],
        signature=spec["signature"],
        refs=list(spec["refs"]),
        contract=HookContract(**spec["contract"]),
        examples=[HookExample(**example) for example in spec["examples"]],
        allowed_api=list(spec["allowed_api"]),
        max_lines=spec["max_lines"],
        stub=spec["stub"],
        method=spec.get("method", ""),
        returns=spec.get("returns", ""),
        parameters=list(spec.get("parameters", [])),
    )
    return asdict(model)


def _roles_for(perms: list, op: str) -> list[str]:
    return sorted({
        perm["role"]
        for perm in perms
        if isinstance(perm, dict) and perm.get("op") == op and isinstance(perm.get("role"), str)
    })


def _operation(operation_id: str, roles: list[str], *, body: bool, path_id: bool) -> dict:
    operation = {
        "operationId": operation_id,
        "responses": {
            "200": {"description": "ok"},
            "403": {"description": "forbidden"},
        },
        "x-roles": roles,
    }
    if path_id:
        operation["parameters"] = [
            {"in": "path", "name": "id", "required": True, "schema": {"type": "string"}},
        ]
    if body:
        operation["requestBody"] = {
            "content": {"application/json": {"schema": {"type": "object"}}},
            "required": True,
        }
    return operation


def _openapi(app: dict) -> dict:
    meta = app.get("meta") if isinstance(app.get("meta"), dict) else {}
    title = meta.get("title") or meta.get("name") or "product"
    if not isinstance(title, str):
        title = "product"
    perms = app.get("permissions") if isinstance(app.get("permissions"), list) else []
    entities = app.get("entities") if isinstance(app.get("entities"), dict) else {}
    commands = app.get("commands") if isinstance(app.get("commands"), dict) else {}
    paths = {}
    for entity in sorted(entities):
        _ident(str(entity))
        paths[f"/api/{entity}"] = {
            "get": _operation(f"{entity}_list", _roles_for(perms, f"{entity}.read"), body=False, path_id=False),
            "post": _operation(f"{entity}_create", _roles_for(perms, f"{entity}.create"), body=True, path_id=False),
        }
        paths[f"/api/{entity}/{{id}}"] = {
            "delete": _operation(f"{entity}_delete", _roles_for(perms, f"{entity}.delete"), body=False, path_id=True),
            "get": _operation(f"{entity}_read", _roles_for(perms, f"{entity}.read"), body=False, path_id=True),
            "put": _operation(f"{entity}_update", _roles_for(perms, f"{entity}.update"), body=True, path_id=True),
        }
    for name in sorted(commands):
        _ident(str(name))
        command = commands[name] if isinstance(commands[name], dict) else {}
        entity = command.get("entity")
        if entity is None:
            path = f"/api/commands/{name}"
        else:
            if not isinstance(entity, str):
                _contract_error("command entity must be a string")
            _ident(entity)
            path = f"/api/{entity}/commands/{name}"
        paths[path] = {
            "post": _operation(name, _roles_for(perms, name), body=bool(command.get("input")), path_id=False),
        }
    return {"info": {"title": title, "version": "1.0.0"}, "openapi": "3.1.0", "paths": paths}


def _web_screens(ui: dict, *, mobile: bool = False) -> list[tuple[str, dict]]:
    screens = ui.get("screens") or {}
    if not isinstance(screens, dict):
        _contract_error("screens must be an object")
    chosen = []
    for name in sorted(screens):
        screen = screens[name]
        if not isinstance(screen, dict):
            _contract_error("screen must be an object")
        if (screen.get("platform") == "mobile") != mobile:
            continue
        _ident(str(name))
        chosen.append((str(name), screen))
    return chosen


def _testids(screen: dict) -> list[str]:
    found = []
    for key in ("actions", "widgets"):
        for item in screen.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("testid"), str):
                found.append(item["testid"])
    return sorted(set(found))


def _routes_ts(screens: list[tuple[str, dict]]) -> str:
    blocks = []
    for name, screen in screens:
        payload = {"path": name, "screen": name}
        if isinstance(screen.get("platform"), str):
            payload["platform"] = screen["platform"]
        roles = screen.get("roles")
        if isinstance(roles, list):
            payload["roles"] = sorted(role for role in roles if isinstance(role, str))
        if isinstance(screen.get("title"), str):
            payload["title"] = screen["title"]
        rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        blocks.append("\n".join(f"  {line}" for line in rendered.splitlines()))
    if not blocks:
        return "export const routes = [\n];\n"
    return "export const routes = [\n" + ",\n".join(blocks) + ",\n];\n"


# Seed rows get stable ids so the stand, the screens and the E2E walks agree on Ticket[0] without a lookup.
_SEED_NAMESPACE = uuid.UUID("5f0c6a52-8d7e-4c1b-9a43-2f6d1e0b7a10")


def _seed_id(entity: str, index: int) -> str:
    return str(uuid.uuid5(_SEED_NAMESPACE, f"{entity}[{index}]"))


def _seed(app: dict) -> dict:
    """app.json seed with ids; an integer in a ref field is the 0-based row of the referenced entity."""
    entities = app.get("entities") or {}
    result = {}
    for entity, rows in sorted((app.get("seed") or {}).items()):
        fields = (entities.get(entity) or {}).get("fields") or {}
        result[entity] = []
        for index, row in enumerate(rows if isinstance(rows, list) else []):
            item = {"id": _seed_id(entity, index)}
            for key, value in (row if isinstance(row, dict) else {}).items():
                field = fields.get(key) or {}
                ref = field.get("ref") if field.get("type") == "ref" else None
                item[key] = _seed_id(ref, value) if ref and isinstance(value, int) and not isinstance(value, bool) else value
            result[entity].append(item)
    return result


def _model_ts(app: dict, ui: dict, screens: list[tuple[str, dict]], mobile: bool) -> str:
    """Everything the generic screen renderer needs, as data: the app ships no hand-written screens."""
    platform = "mobile" if mobile else "web"
    seed = _seed(app)
    model = {
        "platform": platform,
        "lang": (app.get("meta") or {}).get("lang", "ru-RU"),
        "title": (app.get("meta") or {}).get("title") or (app.get("meta") or {}).get("name") or "",
        "device": (ui.get("device") or {}).get(platform, []),
        "screens": dict(screens),
        "menus": {role: (menu or {}).get(platform, []) for role, menu in (ui.get("menus") or {}).items()},
        "home": {role: (home or {}).get(platform) for role, home in (ui.get("home") or {}).items()},
        "copy": ui.get("copy") or {},
        "roles": {role: (data or {}).get("name", role) for role, data in (app.get("roles") or {}).items()},
        "entities": app.get("entities") or {},
        "types": app.get("types") or {},
        "queries": app.get("queries") or {},
        "commands": app.get("commands") or {},
        "machines": app.get("state_machines") or {},
        "seed_ids": {entity: [row["id"] for row in rows] for entity, rows in seed.items()},
    }
    return ("// Generated by the scaffold stage from app.json and ui.json. Do not edit.\n"
            "import type {AppModel} from '../screens/model';\n\n"
            # app.json carries more than the renderer reads; a named constant skips only the excess-property check.
            "const DATA = " + json.dumps(model, indent=2, sort_keys=True, ensure_ascii=False) + ";\n\n"
            "export const MODEL: AppModel = DATA;\n")


def _page_ts(name: str, testids: list[str]) -> str:
    lines = [f"export const {name}Page = {{", "  testids: ["]
    lines.extend(f"    {json.dumps(testid, ensure_ascii=False)}," for testid in testids)
    lines.extend(["  ],", "};", ""])
    return "\n".join(lines)
