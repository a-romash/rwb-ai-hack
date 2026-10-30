"""HTTP API of the product from app.json: CRUD, commands with transitions, access by permissions.

Deterministic: business rules stay in hooks. A guard or computed field calls its hook only when
every hook argument can be bound from the command, the record, Params or the clock; otherwise the
endpoint carries a comment and the rule remains a hook to be wired in `custom`.
Also writes API test cases as JSON: role x operation -> expected status, valid and invalid bodies.
"""

import json
import re

from .domain import SCALARS, _section, camel, field_type, hook_input, pascal


def _cs(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _ops(app: dict) -> set[str]:
    return {f"{p['role']}|{p['op']}" for p in app.get("permissions") or [] if isinstance(p, dict)}


def _bindings(hook_name: str, app: dict, record: str, entity: str, command: str | None) -> list[str] | None:
    """C# argument expressions for a hook, or None when an argument has no source here."""
    hook = _section(app, "hooks").get(hook_name)
    if not isinstance(hook, dict) or hook.get("kind") == "decider":
        return None
    hook_params = set(hook.get("params") or [])
    arguments = []
    tokens = sorted(set(hook.get("in") or []))
    for token in tokens:
        if token == entity:
            arguments.append(record)
        elif command and token == command:
            arguments.append("cmd")
        elif token.startswith(entity + "."):
            field = token.split(".", 1)[1]
            if field not in (_section(app, "entities").get(entity) or {}).get("fields", {}):
                return None
            arguments.append(f"{record}.{pascal(field)}")
        elif token == "datetime":
            arguments.append("time.GetUtcNow()")
        else:
            return None
    arguments += [f"App.Domain.Params.{name}" for name in sorted(hook_params)]
    return arguments


def _computed(app: dict, entity: str) -> list[str]:
    lines = []
    fields = (_section(app, "entities").get(entity) or {}).get("fields", {})
    for name in sorted(fields):
        hook = fields[name].get("computed_by")
        if not hook:
            continue
        arguments = _bindings(hook, app, "item", entity, None)
        method = {"calculator": "Evaluate", "validator": "Validate", "policy": "Allow"}.get(
            (_section(app, "hooks").get(hook) or {}).get("kind"))
        if arguments is None or method is None:
            lines.append(f"        // {pascal(name)}: hook {hook} needs arguments the API does not have; wire it in custom.")
            continue
        lines.append(f"        item.{pascal(name)} = new App.Domain.Hooks.{pascal(hook)}Hook().{method}({', '.join(arguments)});")
    return lines


def _transitions(app: dict, command: str, spec: dict, entity: str) -> list[str]:
    """C# body applying the first transition of the command allowed from the current state."""
    machines = _section(app, "state_machines")
    fields = (_section(app, "entities").get(entity) or {}).get("fields", {})
    state_field = next((name for name, f in fields.items() if f.get("type") == "state"), None)
    lines = []
    for effect in spec.get("effects") or []:
        match = re.fullmatch(r"transition:([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", str(effect))
        if not match or state_field is None:
            continue
        machine = machines.get(match.group(1)) or {}
        transition = next((t for t in machine.get("transitions", []) if t.get("name") == match.group(2)), None)
        if not transition:
            continue
        enum = f"{pascal(match.group(1))}State"
        states = transition["from"] if isinstance(transition["from"], list) else [transition["from"]]
        condition = " || ".join(f"item.{pascal(state_field)} == {enum}.{pascal(s)}" for s in states)
        lines.append(f"        if (!moved && ({condition}))")
        lines.append("        {")
        guard = transition.get("guard")
        if guard:
            arguments = _bindings(guard, app, "item", entity, command)
            kind = (_section(app, "hooks").get(guard) or {}).get("kind")
            method = {"validator": "Validate", "policy": "Allow"}.get(kind)
            if arguments is not None and method:
                lines.append(f"            if (!new App.Domain.Hooks.{pascal(guard)}Hook().{method}({', '.join(arguments)}))")
                lines.append("            {")
                lines.append(f"                return Results.Problem(title: {_cs(guard)}, statusCode: StatusCodes.Status422UnprocessableEntity);")
                lines.append("            }")
            else:
                lines.append(f"            // Guard {guard} needs arguments the API does not have; wire it in custom.")
        lines.append(f"            item.{pascal(state_field)} = {enum}.{pascal(transition['to'])};")
        lines.append("            moved = true;")
        lines.append("        }")
    return lines


def endpoints_cs(app: dict) -> str:
    roles = sorted((app.get("roles") or {}).keys())
    allowed = sorted(_ops(app))
    out = [
        "// Generated by the scaffold stage from app.json. Do not edit: changes go to app.json or custom.",
        "using System.Security.Claims;",
        "using App.Domain;",
        "using App.Infrastructure;",
        "using Microsoft.EntityFrameworkCore;",
        "",
        "namespace App.Api.Features.Generated;",
        "",
        "public static class Access",
        "{",
        "    public static readonly IReadOnlySet<string> Roles = new HashSet<string>",
        "    {",
        *[f"        {_cs(role)}," for role in roles],
        "    };",
        "",
        "    private static readonly HashSet<string> Grants = new()",
        "    {",
        *[f"        {_cs(grant)}," for grant in allowed],
        "    };",
        "",
        "    /// <summary>Role x operation from app.json permissions; scopes own/team are not filtered yet.</summary>",
        "    public static bool Allowed(ClaimsPrincipal user, string operation) =>",
        "        Grants.Contains($\"{user.FindFirstValue(\"role\")}|{operation}\");",
        "}",
        "",
        "public static class GeneratedEndpoints",
        "{",
        "    public static void Map(RouteGroupBuilder api)",
        "    {",
    ]
    entities = _section(app, "entities")
    for entity in sorted(entities):
        cls, var = pascal(entity), camel(entity) + "Group"
        route = f"/{entity}"
        out += [
            f"        var {var} = api.MapGroup({_cs(route)}).RequireAuthorization();",
            f"        {var}.MapGet(\"/\", async (ClaimsPrincipal user, AppDbContext db) =>",
            f"            Access.Allowed(user, {_cs(entity + '.read')}) ? Results.Ok(await db.Set<{cls}>().AsNoTracking().ToListAsync()) : Results.Forbid());",
            f"        {var}.MapGet(\"/{{id:guid}}\", async (Guid id, ClaimsPrincipal user, AppDbContext db) =>",
            "        {",
            f"            if (!Access.Allowed(user, {_cs(entity + '.read')})) return Results.Forbid();",
            f"            var item = await db.Set<{cls}>().FindAsync(id);",
            "            return item is null ? Results.NotFound() : Results.Ok(item);",
            "        });",
            f"        {var}.MapPost(\"/\", async ({cls} item, ClaimsPrincipal user, AppDbContext db, TimeProvider time) =>",
            "        {",
            f"            if (!Access.Allowed(user, {_cs(entity + '.create')})) return Results.Forbid();",
            "            item.Id = Guid.NewGuid();",
            f"            Compute{cls}(item, time);",
            "            db.Add(item);",
            "            await db.SaveChangesAsync();",
            f"            return Results.Created($\"/api/{entity}/{{item.Id}}\", item);",
            "        });",
            f"        {var}.MapPut(\"/{{id:guid}}\", async (Guid id, {cls} item, ClaimsPrincipal user, AppDbContext db, TimeProvider time) =>",
            "        {",
            f"            if (!Access.Allowed(user, {_cs(entity + '.update')})) return Results.Forbid();",
            f"            if (!await db.Set<{cls}>().AnyAsync(x => x.Id == id)) return Results.NotFound();",
            "            item.Id = id;",
            f"            Compute{cls}(item, time);",
            "            db.Update(item);",
            "            await db.SaveChangesAsync();",
            "            return Results.Ok(item);",
            "        });",
            f"        {var}.MapDelete(\"/{{id:guid}}\", async (Guid id, ClaimsPrincipal user, AppDbContext db) =>",
            "        {",
            f"            if (!Access.Allowed(user, {_cs(entity + '.delete')})) return Results.Forbid();",
            f"            var item = await db.Set<{cls}>().FindAsync(id);",
            "            if (item is null) return Results.NotFound();",
            "            db.Remove(item);",
            "            await db.SaveChangesAsync();",
            "            return Results.NoContent();",
            "        });",
        ]
    commands = _section(app, "commands")
    for command in sorted(commands):
        spec = commands[command]
        entity = spec.get("entity")
        if entity not in entities:
            continue
        cls = pascal(entity)
        var = camel(entity) + "Group"
        out += [
            f"        {var}.MapPost({_cs('/commands/' + command)}, async ({pascal(command)} cmd, ClaimsPrincipal user, AppDbContext db, TimeProvider time) =>",
            "        {",
            f"            if (!Access.Allowed(user, {_cs(command)})) return Results.Forbid();",
            f"            var item = await db.Set<{cls}>().FindAsync(cmd.Id);",
            "            if (item is null) return Results.NotFound();",
            f"            var result = Apply{pascal(command)}(item, cmd, time);",
            "            if (result is not null) return result;",
            f"            Compute{cls}(item, time);",
            "            await db.SaveChangesAsync();",
            "            return Results.Ok(item);",
            "        });",
        ]
    out += ["    }", ""]
    for entity in sorted(entities):
        out += [f"    private static void Compute{pascal(entity)}({pascal(entity)} item, TimeProvider time)", "    {",
                *_computed(app, entity), "    }", ""]
    for command in sorted(commands):
        spec = commands[command]
        entity = spec.get("entity")
        if entity not in entities:
            continue
        body = _transitions(app, command, spec, entity)
        out += [f"    private static IResult? Apply{pascal(command)}({pascal(entity)} item, {pascal(command)} cmd, TimeProvider time)", "    {"]
        if body:
            out += ["        var moved = false;", *body,
                    "        return moved ? null : Results.Problem(title: \"transition\", statusCode: StatusCodes.Status409Conflict);"]
        else:
            out += ["        return null;"]
        out += ["    }", ""]
    out[-1:] = ["}", ""]
    return "\n".join(out)


def timers_cs(app: dict) -> str:
    """Transitions with a timer trigger: App.Worker moves records whose timer field has passed."""
    entities = _section(app, "entities")
    lines = []
    for machine_name, machine in sorted(_section(app, "state_machines").items()):
        entity = machine.get("entity")
        fields = (entities.get(entity) or {}).get("fields", {})
        state_field = next((name for name, f in fields.items() if f.get("type") == "state" and f.get("machine") == machine_name), None)
        for transition in machine.get("transitions") or []:
            timer = (transition.get("trigger") or {}).get("timer")
            if not timer:
                continue
            spec = fields.get(timer) or {}
            if state_field is None or spec.get("type") not in ("datetime", "date"):
                lines.append(f"        // {machine_name}.{transition['name']}: timer {timer} is not a date of {entity}; wire it in custom.")
                continue
            enum, cls = f"{pascal(machine_name)}State", pascal(entity)
            states = transition["from"] if isinstance(transition["from"], list) else [transition["from"]]
            due = f"x.{pascal(timer)}"
            limit = "now" if spec["type"] == "datetime" else "today"
            where = " || ".join(f"x.{pascal(state_field)} == {enum}.{pascal(s)}" for s in states)
            nullable = not spec.get("required") or spec.get("nullable")
            check = f"{due} != null && {due} <= {limit}" if nullable else f"{due} <= {limit}"
            lines += [f"        // {machine_name}.{transition['name']}: {', '.join(states)} -> {transition['to']} when {timer} has passed.",
                      f"        foreach (var item in await db.Set<{cls}>().Where(x => ({where}) && {check}).ToListAsync(ct))",
                      "        {"]
            guard = transition.get("guard")
            if guard:
                arguments = _bindings(guard, app, "item", entity, None)
                method = {"validator": "Validate", "policy": "Allow"}.get((_section(app, "hooks").get(guard) or {}).get("kind"))
                if arguments is not None and method:
                    lines.append(f"            if (!new App.Domain.Hooks.{pascal(guard)}Hook().{method}({', '.join(arguments)})) continue;")
                else:
                    lines.append(f"            // Guard {guard} needs arguments the worker does not have; wire it in custom.")
            lines += [f"            item.{pascal(state_field)} = {enum}.{pascal(transition['to'])};", "            moved++;", "        }"]
    return "\n".join([
        "// Generated by the scaffold stage from app.json: transitions triggered by a timer field.",
        "using App.Domain;",
        "using Microsoft.EntityFrameworkCore;",
        "",
        "namespace App.Infrastructure;",
        "",
        "public static class GeneratedTimers",
        "{",
        "    /// <summary>Moves records whose timer has passed; returns how many moved.</summary>",
        "    public static async Task<int> RunAsync(AppDbContext db, TimeProvider time, CancellationToken ct)",
        "    {",
        "        var now = time.GetUtcNow();",
        "        var today = DateOnly.FromDateTime(now.UtcDateTime);",
        "        var moved = 0;",
        *lines,
        "        if (moved > 0) await db.SaveChangesAsync(ct);",
        "        return moved;",
        "    }",
        "}",
        "",
    ])


def dbcontext_cs(app: dict) -> str:
    lines = ["// Generated by the scaffold stage from app.json.", "using App.Domain;",
             "using Microsoft.EntityFrameworkCore;", "", "namespace App.Infrastructure;", "",
             "public sealed partial class AppDbContext", "{",
             "    partial void ConfigureGenerated(ModelBuilder modelBuilder)", "    {"]
    for entity in sorted(_section(app, "entities")):
        lines.append(f"        modelBuilder.Entity<{pascal(entity)}>();")
    lines += ["    }", "}", ""]
    return "\n".join(lines)


SAMPLES = {
    "string": "sample", "text": "sample", "int": 1, "decimal": 1.5, "money": 10, "bool": True,
    "date": "2026-11-06", "datetime": "2026-11-06T09:00:00+00:00", "duration": "01:00:00",
    "interval": "sample", "geo_point": "POINT (30.3 59.9)", "geo_line": "LINESTRING (30.3 59.9, 30.31 59.91)",
    "geo_polygon": "POLYGON ((30.3 59.9, 30.31 59.9, 30.31 59.91, 30.3 59.9))", "file": "sample", "json": "{}",
}


def _sample(spec: dict, app: dict):
    kind = spec.get("type")
    if kind == "enum":
        values = (_section(app, "types").get(spec.get("ref")) or {}).get("values") or ["value"]
        return re.sub(r"(?<!^)(?=[A-Z])", "_", pascal(values[0])).lower()
    if kind == "ref":
        return "00000000-0000-0000-0000-000000000001"
    return SAMPLES.get(kind, "sample")


def _body(fields: dict, app: dict) -> dict:
    """Valid JSON body: every required field that the client sends (not computed, not state)."""
    return {name: _sample(spec, app) for name, spec in sorted(fields.items())
            if spec.get("required") and not spec.get("computed_by") and spec.get("type") != "state"}


def api_cases(app: dict) -> dict:
    """role x operation -> expected status, plus 400 on a body without required fields."""
    grants = _ops(app)
    roles = sorted((app.get("roles") or {}).keys())
    cases = []
    entities = _section(app, "entities")
    for entity in sorted(entities):
        fields = entities[entity].get("fields") or {}
        body = _body(fields, app)
        cases.append({"id": f"{entity}.read.anonymous", "role": None, "method": "GET", "path": f"/api/{entity}", "expected": 401})
        for role in roles:
            for op, method, path, payload, success in (
                    ("read", "GET", f"/api/{entity}", None, 200),
                    ("create", "POST", f"/api/{entity}", body, 201)):
                allowed = f"{role}|{entity}.{op}" in grants
                cases.append({"id": f"{entity}.{op}.{role}", "role": role, "method": method, "path": path,
                              "body": payload, "expected": success if allowed else 403})
            if f"{role}|{entity}.create" in grants and body:
                broken = dict(body)
                broken.pop(sorted(broken)[0])
                cases.append({"id": f"{entity}.create.{role}.invalid", "role": role, "method": "POST",
                              "path": f"/api/{entity}", "body": broken, "expected": 400})
    for command in sorted(_section(app, "commands")):
        spec = _section(app, "commands")[command]
        entity = spec.get("entity")
        if entity not in entities:
            continue
        body = {"id": "00000000-0000-0000-0000-0000000000ff", **_body(spec.get("input") or {}, app)}
        for role in roles:
            allowed = f"{role}|{command}" in grants
            # The record does not exist: an allowed role passes access and gets 404.
            cases.append({"id": f"{command}.{role}", "role": role, "method": "POST",
                          "path": f"/api/{entity}/commands/{command}", "body": body, "expected": 404 if allowed else 403})
    return {"schema_version": 1, "cases": cases}


def required_fields(spec: dict) -> bool:
    """Fields the API requires from the client (marked [JsonRequired] in the model)."""
    return bool(spec.get("required")) and not spec.get("computed_by") and spec.get("type") != "state"


__all__ = ["api_cases", "dbcontext_cs", "endpoints_cs", "required_fields", "SCALARS", "field_type", "hook_input"]
