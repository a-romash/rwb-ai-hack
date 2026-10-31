"""Audited, deterministic recovery of model formats and linked identifiers."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import tokenize
import unicodedata
from difflib import SequenceMatcher

VERSION = "1"
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CYRILLIC = dict(
    zip(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        [
            "a",
            "b",
            "v",
            "g",
            "d",
            "e",
            "yo",
            "zh",
            "z",
            "i",
            "y",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "r",
            "s",
            "t",
            "u",
            "f",
            "kh",
            "ts",
            "ch",
            "sh",
            "shch",
            "",
            "y",
            "",
            "e",
            "yu",
            "ya",
        ],
    )
)
SYMBOLS = (
    "types",
    "entities",
    "roles",
    "params",
    "hooks",
    "commands",
    "queries",
    "state_machines",
    "events",
    "integrations",
    "schedules",
    "notifications",
)


def pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def note(changes, path, before, after, reason, **extra):
    if before != after:
        changes.append(
            dict(
                path=path,
                before=copy.deepcopy(before),
                after=copy.deepcopy(after),
                reason=reason,
                **extra,
            )
        )


def folded(text):
    return "".join(c for c in str(text).casefold() if c.isalnum())


def identifier(text, *, field=False):
    if IDENT.fullmatch(text):
        return text
    chars = "".join(
        (CYRILLIC.get(c.lower(), c).capitalize() if c.isupper() else CYRILLIC.get(c, c))
        for c in text
    )
    chars = unicodedata.normalize("NFKD", chars).encode("ascii", "ignore").decode()
    words = re.findall(r"[A-Za-z0-9]+", chars)
    value = (
        "_".join(w.lower() for w in words)
        if field
        else "".join(w[:1].upper() + w[1:] for w in words)
    )
    if not value:
        value = "Generated" + hashlib.sha256(text.encode()).hexdigest()[:8]
    return ("N" + value) if value[0].isdigit() else value


def match_name(value, names, aliases=None):
    if value in names:
        return value
    if aliases and value in aliases and aliases[value] in names:
        return aliases[value]
    candidates = [
        n for n in names if folded(n) == folded(value) or n == identifier(value)
    ]
    if len(candidates) == 1:
        return candidates[0]
    ranked = sorted(
        ((SequenceMatcher(None, folded(value), folded(n)).ratio(), n) for n in names),
        reverse=True,
    )
    if (
        ranked
        and ranked[0][0] >= 0.9
        and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 0.1)
    ):
        return ranked[0][1]
    return value


def normalize_response(raw, model):
    """Use only the requested schema; free text and stable business IDs stay data."""
    changes = []
    value = copy.deepcopy(raw)
    if isinstance(value, str):
        text = value.strip()
        fence = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.S | re.I)
        if fence:
            text = fence[1].strip()
            note(changes, "", value, text, "json_fence")
        value = json.loads(text)
    schema = model.model_json_schema()
    defs = schema.get("$defs", {})

    def visit(v, s, path):
        while "$ref" in s:
            s = defs[s["$ref"].rsplit("/", 1)[-1]]
        variants = s.get("anyOf") or s.get("oneOf")
        if variants:

            def score(option):
                while "$ref" in option:
                    option = defs[option["$ref"].rsplit("/", 1)[-1]]
                t = option.get("type")
                fits = (
                    (v is None and t == "null")
                    or (isinstance(v, dict) and t == "object")
                    or (isinstance(v, list) and t == "array")
                    or (isinstance(v, str) and t == "string")
                    or (type(v) in (int, float) and t in ("number", "integer"))
                    or (type(v) is bool and t == "boolean")
                )
                points = 100 if fits else 0
                if isinstance(v, dict):
                    props = option.get("properties", {})
                    points += 3 * len(set(v) & set(props)) - 2 * len(
                        set(option.get("required", [])) - set(v)
                    )
                    for key, child in props.items():
                        if key in v and "const" in child:
                            points += 100 if v[key] == child["const"] else -1000
                return points

            ranked = sorted(
                enumerate(variants), key=lambda x: score(x[1]), reverse=True
            )
            if len(ranked) > 1 and score(ranked[0][1]) == score(ranked[1][1]):
                return v
            return visit(v, ranked[0][1], path)
        kind = s.get("type")
        if isinstance(v, dict) and len(v) == 1:
            key = next(iter(v))
            inside = v[key]
            wrappers = {
                "result",
                "data",
                "response",
                "output",
                "section",
                re.sub(r"Section$", "", model.__name__).lower(),
            }
            props = s.get("properties", {})
            # A dictionary's one real business symbol is not an envelope.
            if (
                key in wrappers
                and key not in props
                and (not path or props)
                and (
                    props
                    and isinstance(inside, dict)
                    or kind == "array"
                    and isinstance(inside, list)
                    or isinstance(inside, dict)
                    and "additionalProperties" in s
                    and all(isinstance(x, dict) for x in inside.values())
                )
            ):
                note(changes, path, v, inside, "unwrap")
                v = inside
        if kind == "object" and isinstance(v, dict):
            props = s.get("properties", {})
            result = {}
            for key, item in v.items():
                target = match_name(key, props) if props else key
                if target not in props:
                    aliases = {
                        "operations": "ops",
                        "ops": "operations",
                        "inputs": "input",
                        "input": "inputs",
                        "copy_texts": "copy",
                    }
                    if aliases.get(key) in props:
                        target = aliases[key]
                if target not in props and (
                    props or s.get("additionalProperties") is False
                ):
                    note(changes, pointer(path, key), item, None, "unknown_field")
                    continue
                if target in result and result[target] != item:
                    # Let validation/model repair resolve conflicting aliases, never overwrite silently.
                    result[key] = item
                    continue
                note(changes, pointer(path, key), key, target, "property_alias")
                child = props.get(target, s.get("additionalProperties", {}))
                result[target] = visit(
                    item,
                    child if isinstance(child, dict) else {},
                    pointer(path, target),
                )
            for key, child in props.items():
                if key not in result and "default" in child:
                    result[key] = copy.deepcopy(child["default"])
                    note(
                        changes, pointer(path, key), None, result[key], "schema_default"
                    )
            return result
        if kind == "array":
            if not isinstance(v, list) and v is not None:
                note(changes, path, v, [v], "singleton_list")
                v = [v]
            if isinstance(v, list):
                return [
                    visit(x, s.get("items", {}), pointer(path, i))
                    for i, x in enumerate(v)
                ]
        if (
            kind == "boolean"
            and isinstance(v, str)
            and v.lower() in ("true", "false", "yes", "no", "1", "0")
        ):
            out = v.lower() in ("true", "yes", "1")
            note(changes, path, v, out, "boolean")
            return out
        if kind in ("integer", "number") and isinstance(v, str):
            try:
                out = int(v) if kind == "integer" else float(v)
                note(changes, path, v, out, "number")
                return out
            except ValueError:
                pass
        pattern = s.get("pattern")
        if (
            isinstance(v, str)
            and pattern == r"^[A-Z][A-Za-z0-9]*$"
            and not re.fullmatch(pattern, v)
        ):
            out = "".join(w[:1].upper() + w[1:] for w in identifier(v).split("_"))
            note(changes, path, v, out, "screen_identifier")
            return out
        allowed = s.get("enum")
        if allowed and isinstance(v, str):
            alias = {
                "boolean": "bool",
                "integer": "int",
                "number": "decimal",
                "object": "json",
                "reference": "ref",
                "timestamp": "datetime",
            }
            candidate = alias.get(v.casefold(), v)
            matches = [
                x
                for x in allowed
                if isinstance(x, str) and folded(x) == folded(candidate)
            ]
            if len(matches) == 1:
                note(changes, path, v, matches[0], "enum_alias")
                return matches[0]
        return v

    value = visit(value, schema, "")
    if model.__name__ == "App" and model.__module__ == "contracts.app":
        value, linked_changes = normalize_app(value)
        changes.extend(linked_changes)
    if model.__name__ == "UiSpec" and model.__module__ == "contracts.ui":
        value, linked_changes = normalize_ui(value, {})
        changes.extend(linked_changes)
    return value, changes


def compatible(left, right):
    if left == right:
        return copy.deepcopy(left)
    if isinstance(left, dict) and isinstance(right, dict):
        result = copy.deepcopy(left)
        for key, value in right.items():
            if key in result:
                merged = compatible(result[key], value)
                if merged is NotImplemented:
                    return NotImplemented
                result[key] = merged
            else:
                result[key] = copy.deepcopy(value)
        return result
    return NotImplemented


def rename_map(items, namespace, changes, aliases, *, field=False, screen=False):
    if not isinstance(items, dict):
        return items
    result = {}
    # Reserve valid names first so adding an invalid alias never renames an existing symbol.
    valid = lambda n: (
        bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", n))
        if screen
        else bool(IDENT.fullmatch(n))
    )
    for old, item in sorted(items.items(), key=lambda x: not valid(x[0])):
        new = old if valid(old) else identifier(old, field=field)
        if screen and not re.fullmatch(r"[A-Z][A-Za-z0-9]*", new):
            new = "".join(x[:1].upper() + x[1:] for x in new.split("_"))
        if new in result:
            merged = compatible(result[new], item)
            if merged is not NotImplemented:
                result[new] = merged
                note(
                    changes, pointer("/" + namespace, old), old, new, "duplicate_merge"
                )
                aliases[old] = new
                continue
            original = new
            new = original + hashlib.sha256(old.encode()).hexdigest()[:8]
            note(
                changes,
                pointer("/" + namespace, old),
                old,
                new,
                "name_collision",
                conflict=result[original],
                candidate=item,
                target_path=pointer("/" + namespace, new),
                conflict_path=pointer("/" + namespace, original),
            )
        else:
            note(
                changes,
                pointer("/" + namespace, old),
                old,
                new,
                "identifier",
                target_path=pointer("/" + namespace, new),
            )
        aliases[old] = new
        result[new] = item
    return result


def normalize_app(raw, aliases=None):
    data = copy.deepcopy(raw)
    changes = []
    aliases = aliases if aliases is not None else {}
    for section in SYMBOLS:
        if section == "roles":
            continue  # ROLE-01 and other analysis IDs are stable.
        if section in data:
            data[section] = rename_map(
                data[section], section, changes, aliases.setdefault(section, {})
            )
    for entity, item in data.get("entities", {}).items():
        item["fields"] = rename_map(
            item.get("fields", {}),
            "entities/" + entity + "/fields",
            changes,
            aliases.setdefault("fields:" + entity, {}),
            field=True,
        )

    def ref(v, section, path):
        if not isinstance(v, str):
            return v
        out = match_name(v, data.get(section, {}), aliases.get(section))
        note(changes, path, v, out, "reference")
        return out

    def field_ref(v, entity, path):
        names = data.get("entities", {}).get(entity, {}).get("fields", {})
        out = (
            match_name(v, names, aliases.get("fields:" + entity))
            if isinstance(v, str)
            else v
        )
        note(changes, path, v, out, "field_reference")
        return out

    def operation(v, path):
        if not isinstance(v, str):
            return v
        if "." in v and v.rsplit(".", 1)[1] in ("create", "read", "update", "delete"):
            n, op = v.rsplit(".", 1)
            return ref(n, "entities", path) + "." + op
        return ref(v, "commands", path)

    def expression(v, path):
        if not isinstance(v, str):
            return v
        mappings = {}
        for section in SYMBOLS:
            for old, new in aliases.get(section, {}).items():
                if old != new:
                    mappings.setdefault(old, set()).add(new)
        # Tokenize strings first: never replace a name inside a quoted literal.
        try:
            spans = []
            offsets = [0]
            for line in v.splitlines(keepends=True):
                offsets.append(offsets[-1] + len(line))
            for tok in tokenize.generate_tokens(io.StringIO(v).readline):
                if tok.type == tokenize.STRING:
                    spans.append(
                        (
                            offsets[tok.start[0] - 1] + tok.start[1],
                            offsets[tok.end[0] - 1] + tok.end[1],
                        )
                    )
        except (tokenize.TokenError, IndentationError):
            changes.append(
                dict(path=path, before=v, after=v, reason="expression_needs_repair")
            )
            return v
        pattern = "|".join(
            re.escape(k)
            for k in sorted(mappings, key=len, reverse=True)
            if len(mappings[k]) == 1
        )
        if not pattern:
            return v

        def replace(m):
            if any(start <= m.start() < end for start, end in spans):
                return m[0]
            return next(iter(mappings[m[0]]))

        out = re.sub(r"(?<![\w])(?:" + pattern + r")(?![\w])", replace, v)
        note(changes, path, v, out, "expression_identifier")
        return out

    for entity, item in data.get("entities", {}).items():
        if item.get("owner"):
            item["owner"] = field_ref(
                item["owner"], entity, "/entities/" + entity + "/owner"
            )
        for name, f in item.get("fields", {}).items():
            p = "/entities/" + entity + "/fields/" + name
            if f.get("ref"):
                f["ref"] = ref(
                    f["ref"],
                    "types" if f.get("type") == "enum" else "entities",
                    p + "/ref",
                )
            for key, section in (
                ("computed_by", "hooks"),
                ("machine", "state_machines"),
            ):
                if f.get(key):
                    f[key] = ref(f[key], section, p + "/" + key)
    for section in ("commands", "queries", "state_machines"):
        for name, item in data.get(section, {}).items():
            p = "/" + section + "/" + name
            if item.get("entity"):
                item["entity"] = ref(item["entity"], "entities", p + "/entity")
            if "roles" in item:
                item["roles"] = [
                    ref(v, "roles", p + "/roles/" + str(i))
                    for i, v in enumerate(item["roles"])
                ]
            if "input" in item:
                item["input"] = rename_map(
                    item["input"],
                    section + "/" + name + "/input",
                    changes,
                    aliases.setdefault("input:" + name, {}),
                    field=True,
                )
            for key in ("filter", "order"):
                if item.get(key):
                    item[key] = expression(item[key], p + "/" + key)
            for i, effect in enumerate(item.get("effects", [])):
                item["effects"][i] = expression(effect, p + "/effects/" + str(i))
            for i, t in enumerate(item.get("transitions", [])):
                tp = p + "/transitions/" + str(i)
                if t.get("guard"):
                    t["guard"] = ref(t["guard"], "hooks", tp + "/guard")
                for key, namespace in (
                    ("command", "commands"),
                    ("event", "events"),
                    ("schedule", "schedules"),
                ):
                    if (t.get("trigger") or {}).get(key):
                        t["trigger"][key] = ref(
                            t["trigger"][key], namespace, tp + "/trigger/" + key
                        )
                for j, effect in enumerate(t.get("effects", [])):
                    t["effects"][j] = expression(effect, tp + "/effects/" + str(j))
    for i, p in enumerate(data.get("permissions", [])):
        p["op"] = operation(p.get("op"), "/permissions/" + str(i) + "/op")
        if p.get("role"):
            p["role"] = ref(p["role"], "roles", "/permissions/" + str(i) + "/role")
    for name, h in data.get("hooks", {}).items():
        p = "/hooks/" + name
        if "params" in h:
            h["params"] = [
                ref(v, "params", p + "/params/" + str(i))
                for i, v in enumerate(h["params"])
            ]
        for key in ("in",):
            if key in h:
                h[key] = [
                    linked(v, p + "/" + key + "/" + str(i), data, aliases, changes)
                    for i, v in enumerate(h[key])
                ]
        for key, namespace in (("select", "queries"),):
            if h.get(key):
                h[key] = ref(h[key], namespace, p + "/" + key)
    for name, item in data.get("notifications", {}).items():
        if item.get("on"):
            item["on"] = ref(item["on"], "events", "/notifications/" + name + "/on")
        if item.get("to"):
            item["to"] = ref(item["to"], "roles", "/notifications/" + name + "/to")
    for section in ("events", "schedules", "integrations"):
        for name, item in data.get(section, {}).items():
            for key, namespace in (
                ("entity", "entities"),
                ("command", "commands"),
                ("event", "events"),
                ("hook", "hooks"),
            ):
                if isinstance(item.get(key), str):
                    item[key] = ref(
                        item[key], namespace, "/" + section + "/" + name + "/" + key
                    )
    for section in ("seed",):
        if section in data:
            rows = {}
            for old, value in data[section].items():
                entity = ref(old, "entities", "/seed/" + old)
                rows[entity] = [
                    {
                        field_ref(
                            k, entity, "/seed/" + entity + "/" + str(i) + "/" + k
                        ): v
                        for k, v in row.items()
                    }
                    for i, row in enumerate(value)
                ]
            data[section] = rows
    return data, changes


def linked(value, path, app, aliases, changes):
    if not isinstance(value, str):
        return value
    if "." in value:
        entity, field = value.split(".", 1)
        new_entity = match_name(
            entity, app.get("entities", {}), aliases.get("entities")
        )
        if new_entity in app.get("entities", {}):
            fields = app["entities"][new_entity].get("fields", {})
            result = (
                new_entity
                + "."
                + match_name(field, fields, aliases.get("fields:" + new_entity))
            )
            note(changes, path, value, result, "field_reference")
            return result
    return value


def normalize_ui(raw, app, aliases=None):
    data = copy.deepcopy(raw)
    changes = []
    aliases = aliases or {}
    screen_aliases = {}
    data["screens"] = rename_map(
        data.get("screens", {}), "screens", changes, screen_aliases, screen=True
    )

    def screen(v, p):
        out = (
            match_name(v, data["screens"], screen_aliases) if isinstance(v, str) else v
        )
        note(changes, p, v, out, "screen_reference")
        return out

    def visit(value, path=""):
        if isinstance(value, list):
            return [visit(v, pointer(path, i)) for i, v in enumerate(value)]
        if not isinstance(value, dict):
            return value
        result = {}
        for k, v in value.items():
            p = pointer(path, k)
            if k in ("screen", "then", "open") and isinstance(v, str):
                result[k] = screen(v, p)
            elif k == "nav" and isinstance(v, list):
                result[k] = [screen(x, pointer(p, i)) for i, x in enumerate(v)]
            elif k in ("entity", "query", "command") and isinstance(v, str):
                section = {
                    "entity": "entities",
                    "query": "queries",
                    "command": "commands",
                }[k]
                result[k] = match_name(v, app.get(section, {}), aliases.get(section))
                note(changes, p, v, result[k], "ui_reference")
            elif k in ("field", "fill", "scan") and isinstance(v, str):
                result[k] = linked(v, p, app, aliases, changes)
            elif k == "tap" and isinstance(v, str):
                command = match_name(
                    v, app.get("commands", {}), aliases.get("commands")
                )
                result[k] = screen(command, p) if command == v else command
                note(changes, p, v, result[k], "action_reference")
            elif k == "error" and isinstance(v, str) and path.endswith("/expect"):
                result[k] = match_name(v, app.get("hooks", {}), aliases.get("hooks"))
                note(changes, p, v, result[k], "hook_reference")
            elif k in ("seed", "param") and isinstance(v, str):
                if k == "param":
                    result[k] = match_name(
                        v, app.get("params", {}), aliases.get("params")
                    )
                else:
                    m = re.fullmatch(r"(.+?)(\[\d+\])(?:\.(.+))?", v)
                    if m:
                        entity = match_name(
                            m[1], app.get("entities", {}), aliases.get("entities")
                        )
                        field = (
                            match_name(
                                m[3],
                                app.get("entities", {})
                                .get(entity, {})
                                .get("fields", {}),
                                aliases.get("fields:" + entity),
                            )
                            if m[3]
                            else None
                        )
                        result[k] = entity + m[2] + ("." + field if field else "")
                    else:
                        result[k] = v
                note(changes, p, v, result[k], "data_reference")
            else:
                result[k] = visit(v, p)
        return result

    data = visit(data)
    for key in ("menus", "home"):
        for role, platforms in data.get(key, {}).items():
            for platform, v in platforms.items():
                platforms[platform] = (
                    [screen(n, "/" + key + "/" + role + "/" + platform) for n in v]
                    if isinstance(v, list)
                    else screen(v, "/" + key + "/" + role + "/" + platform)
                )
    return data, changes


def record(workspace, changes, source, llm=None):
    if not changes:
        return
    if llm is not None and hasattr(llm, "event"):
        llm.event(
            "artifact.normalized",
            {"source": source, "version": VERSION, "changes": changes},
        )
    from pathlib import Path

    path = Path(workspace) / "reports/normalization-log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {"source": source, "version": VERSION, "changes": changes},
                ensure_ascii=False,
            )
            + "\n"
        )


def normalize_patch(raw, document):
    """Resolve paths against the current document; authorization still runs afterwards."""
    result = copy.deepcopy(raw)
    changes = []
    for op in result.get("operations", result.get("ops", [])):
        for key in ("path", "from"):
            path = op.get(key)
            if (
                not isinstance(path, str)
                or not path.startswith("/")
                or re.search(r"~(?![01])", path)
            ):
                continue
            current = document
            parts = []
            for token in path[1:].split("/"):
                old = token.replace("~1", "/").replace("~0", "~")
                new = match_name(old, current) if isinstance(current, dict) else old
                parts.append(new)
                if isinstance(current, dict):
                    current = current.get(new)
                elif (
                    isinstance(current, list)
                    and new.isdecimal()
                    and int(new) < len(current)
                ):
                    current = current[int(new)]
                else:
                    current = None
            new = "/" + "/".join(
                str(p).replace("~", "~0").replace("/", "~1") for p in parts
            )
            note(changes, path, path, new, "patch_pointer")
            op[key] = new
    return result, changes


def within(changes, allowed):
    """Any incidental reference updates must remain inside the patch's allowed roots."""
    return all(
        allowed(c["path"]) and (not c.get("target_path") or allowed(c["target_path"]))
        for c in changes
    )
