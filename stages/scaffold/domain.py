"""C# domain model from app.json: enums, machine states, entities, commands and Params.

Hook stubs, hook bodies written by the model and acceptance tests compile against these types.
Everything lives in namespace App.Domain, so App.Domain.Hooks and App.Domain.Generated see it
without extra usings. Same bytes in, same bytes out.
"""

import json
import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char", "checked", "class",
    "const", "continue", "decimal", "default", "delegate", "do", "double", "else", "enum", "event",
    "explicit", "extern", "false", "finally", "fixed", "float", "for", "foreach", "goto", "if",
    "implicit", "in", "int", "interface", "internal", "is", "lock", "long", "namespace", "new",
    "null", "object", "operator", "out", "override", "params", "private", "protected", "public",
    "readonly", "ref", "return", "sbyte", "sealed", "short", "sizeof", "stackalloc", "static",
    "string", "struct", "switch", "this", "throw", "true", "try", "typeof", "uint", "ulong",
    "unchecked", "unsafe", "ushort", "using", "virtual", "void", "volatile", "while",
}
# Scalar field types of app.json mapped to C#; ref/enum/state are resolved separately.
SCALARS = {
    "string": "string", "text": "string", "int": "int", "decimal": "decimal", "money": "decimal",
    "bool": "bool", "date": "DateOnly", "datetime": "DateTimeOffset", "duration": "TimeSpan",
    "interval": "string", "geo_point": "string", "geo_line": "string", "geo_polygon": "string",
    "file": "string", "json": "string",
}
_REFERENCE = {"string"}


def pascal(text: str) -> str:
    parts = [part for part in re.split(r"[^0-9A-Za-z]+", str(text)) if part]
    name = "".join(part[:1].upper() + part[1:] for part in parts)
    if not name:
        name = "Value"
    if name[0].isdigit():
        name = "V" + name
    return name


def camel(text: str) -> str:
    name = pascal(text)
    name = name[:1].lower() + name[1:]
    return name + "Arg" if name in _KEYWORDS else name


def _section(app: dict, key: str) -> dict:
    value = app.get(key)
    return value if isinstance(value, dict) else {}


def state_enum(machine: str) -> str:
    return f"{pascal(machine)}State"


def enum_name(name: str, app: dict) -> str:
    """C# name of an app.json type; a spec may give a type the name of an entity or command."""
    taken = {pascal(n) for section in ("entities", "commands") for n in _section(app, section)}
    return pascal(name) + ("Type" if pascal(name) in taken else "")


def field_type(spec: dict, app: dict) -> str:
    """C# type of an app.json field, without nullability."""
    kind = spec.get("type")
    if kind == "enum" and isinstance(spec.get("ref"), str) and spec["ref"] in _section(app, "types"):
        return enum_name(spec["ref"], app)
    if kind == "ref":
        return "Guid"
    if kind == "state" and isinstance(spec.get("machine"), str):
        return state_enum(spec["machine"])
    return SCALARS.get(kind, "string")


def _nullable(cs_type: str, spec: dict) -> bool:
    return not spec.get("required") or bool(spec.get("nullable"))


def _property(name: str, spec: dict, app: dict) -> str:
    cs_type = field_type(spec, app)
    machine = _section(app, "state_machines").get(spec.get("machine")) if spec.get("type") == "state" else None
    if isinstance(machine, dict) and machine.get("initial") in (machine.get("states") or []):
        # A record always has a state; it starts in the machine's initial state.
        initial = _members(machine["states"])[machine["states"].index(machine["initial"])]
        return f"    public {cs_type} {pascal(name)} {{ get; set; }} = {cs_type}.{initial};"
    if _nullable(cs_type, spec):
        return f"    public {cs_type}? {pascal(name)} {{ get; set; }}"
    default = ' = "";' if cs_type in _REFERENCE else ""
    # The API rejects a body without fields the client must send (computed and state are server-side).
    required = "    [System.Text.Json.Serialization.JsonRequired]\n" if not spec.get("computed_by") else ""
    return f"{required}    public {cs_type} {pascal(name)} {{ get; set; }}{default}"


def param_type(declared: dict) -> str:
    kind = declared.get("type") if isinstance(declared, dict) else None
    value = declared.get("value") if isinstance(declared, dict) else None
    if kind == "json" and isinstance(value, list):
        if all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            return "int[]"
        if all(isinstance(item, str) for item in value):
            return "string[]"
    return SCALARS.get(kind, "string")


def _literal(cs_type: str, value) -> str:
    if cs_type == "TimeSpan":
        return f"System.Xml.XmlConvert.ToTimeSpan({json.dumps(str(value))})"
    if cs_type == "DateTimeOffset":
        return f"DateTimeOffset.Parse({json.dumps(str(value))}, System.Globalization.CultureInfo.InvariantCulture)"
    if cs_type == "DateOnly":
        return f"DateOnly.Parse({json.dumps(str(value))}, System.Globalization.CultureInfo.InvariantCulture)"
    if cs_type == "bool":
        return "true" if value is True else "false"
    if cs_type == "int" and isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if cs_type == "decimal" and isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value}m"
    if cs_type in ("int[]", "string[]"):
        return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return json.dumps(text, ensure_ascii=False)


def params_cs(app: dict) -> str:
    """Rule thresholds; tests read them from here instead of repeating numbers."""
    lines = ["namespace App.Domain;", "", "/// <summary>Rule parameters from app.json params.</summary>",
             "public static class Params", "{"]
    for name in sorted(_section(app, "params")):
        if not _IDENT.fullmatch(name):
            continue
        declared = _section(app, "params")[name]
        cs_type = param_type(declared)
        value = declared.get("value") if isinstance(declared, dict) else None
        literal = _literal(cs_type, value)
        if cs_type in ("int", "decimal", "bool", "string") and not literal.startswith(("System.", "DateTimeOffset", "DateOnly")):
            lines.append(f"    public const {cs_type} {name} = {literal};")
        else:
            lines.append(f"    public static readonly {cs_type} {name} = {literal};")
    lines.extend(["}", ""])
    return "\n".join(lines)


def _members(values: list) -> list[str]:
    seen, members = set(), []
    for value in values:
        name = pascal(value)
        while name in seen:
            name += "_"
        seen.add(name)
        members.append(name)
    return members


def model_cs(app: dict) -> str:
    """Enums, machine states, entities and commands of the domain."""
    lines = ["namespace App.Domain;", ""]
    for name in sorted(_section(app, "types")):
        values = _section(app, "types")[name].get("values") or []
        lines += [f"public enum {enum_name(name, app)}", "{", *[f"    {member}," for member in _members(values)], "}", ""]
    for name in sorted(_section(app, "state_machines")):
        states = _section(app, "state_machines")[name].get("states") or []
        lines += [f"public enum {state_enum(name)}", "{", *[f"    {member}," for member in _members(states)], "}", ""]
    for name in sorted(_section(app, "entities")):
        fields = _section(app, "entities")[name].get("fields") or {}
        lines += [f"public sealed class {pascal(name)}", "{", "    public Guid Id { get; set; }"]
        lines += [_property(field, fields[field], app) for field in sorted(fields) if pascal(field) != "Id"]
        lines += ["}", ""]
    for name in sorted(_section(app, "commands")):
        command = _section(app, "commands")[name]
        parameters = ["Guid Id"] if isinstance(command.get("entity"), str) else []
        inputs = command.get("input") if isinstance(command.get("input"), dict) else {}
        for field in sorted(inputs):
            # Entity commands already carry the target entity Id as their first
            # argument. Some specs repeat that same identifier in input.
            if parameters and pascal(field) == "Id":
                continue
            spec = inputs[field] if isinstance(inputs[field], dict) else {}
            cs_type = field_type(spec, app)
            optional = "?" if _nullable(cs_type, spec) else ""
            parameters.append(f"{cs_type}{optional} {pascal(field)}")
        lines += [f"public sealed record {pascal(name)}({', '.join(parameters)});", ""]
    return "\n".join(lines)


def hook_input(token: str, app: dict) -> tuple[str, str]:
    """Type and parameter name for an item of hooks[].in.

    The contract allows entity and command names, `Entity.field` and scalar type names.
    """
    entities, commands, types = _section(app, "entities"), _section(app, "commands"), _section(app, "types")
    if token in entities or token in commands:
        return pascal(token), camel(token)
    if token in types:
        return enum_name(token, app), camel(token)
    if "." in token:
        entity, field = token.split(".", 1)
        spec = (entities.get(entity) or {}).get("fields", {}).get(field)
        if isinstance(spec, dict):
            cs_type = field_type(spec, app)
            return (cs_type + "?" if _nullable(cs_type, spec) else cs_type), camel(f"{entity}_{field}")
    if token in SCALARS:
        return SCALARS[token], camel(token + "_value")
    params = _section(app, "params")
    if token in params:
        return param_type(params[token]), camel(token)
    # An unresolved name (G1 reports REF_UNRESOLVED) must not become a C# type that does not exist.
    return "string", camel(token)
