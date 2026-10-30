from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: str | None = None
    build: list[str] | None = None
    test: list[str] | None = None
    filter: list[str] | None = None
    reports: dict[str, str] | None = None
    workdir: str | None = None
    e2e: list[str] | None = None
    up: list[str] | None = None
    smoke: list[str] | None = None
    down: list[str] | None = None


class Targets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    backend: Target
    admin: Target
    mobile: Target
    stack: Target


class Scan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: str
    commands: list[list[str]]


class Pack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targets: Targets
    scan: Scan
    write_roots: list[str]
    readonly: list[str]


def load_pack(path: str | Path) -> Pack:
    return Pack.model_validate(_parse_yaml(Path(path).read_text(encoding="utf-8")))


# ponytail: indent maps plus one-line [...] and {...} only. Use a real YAML
# parser if the manifest gains anchors, block lists, or multiline strings.


def _parse_yaml(text: str):
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), stripped))
    if not lines:
        return {}
    node, index = _mapping(lines, 0, lines[0][0])
    if index != len(lines):
        raise ValueError("unparsed manifest lines")
    return node


def _mapping(lines, index, indent):
    node = {}
    while index < len(lines):
        current, text = lines[index]
        if current < indent:
            break
        if current != indent:
            raise ValueError(f"unexpected indent before {text}")
        key, value = _split_key(text)
        index += 1
        if value == "":
            if index < len(lines) and lines[index][0] > indent:
                node[key], index = _mapping(lines, index, lines[index][0])
            else:
                node[key] = None
        elif value[0] in "[{":
            parsed, end = _flow(value, 0)
            if end != len(value):
                raise ValueError(f"trailing characters in {value}")
            node[key] = parsed
        else:
            node[key] = _plain(value)
    return node, index


def _split_key(text: str):
    if ": " in text:
        key, value = text.split(": ", 1)
        return key.strip(), value.strip()
    if text.endswith(":"):
        return text[:-1].strip(), ""
    raise ValueError(f"expected key: {text}")


def _plain(value: str):
    if value[:1] in "\"'":
        parsed, end = _quoted(value, 0)
        if end != len(value):
            raise ValueError(f"trailing characters in {value}")
        return parsed
    return value


def _skip(text, index):
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _flow(text, index):
    closing = {"[": "]", "{": "}"}[text[index]]
    as_map = text[index] == "{"
    index += 1
    items = []
    pairs = {}
    while True:
        index = _skip(text, index)
        if index < len(text) and text[index] == closing:
            return (pairs if as_map else items), index + 1
        if as_map:
            key, index = _token(text, index, ":")
            index = _skip(text, index)
            if index >= len(text) or text[index] != ":":
                raise ValueError("expected ':' in flow mapping")
            index += 1
            value, index = _flow_value(text, index)
            pairs[key] = value
        else:
            value, index = _flow_value(text, index)
            items.append(value)
        index = _skip(text, index)
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        if index < len(text) and text[index] == closing:
            continue
        got = text[index : index + 20] if index < len(text) else "eof"
        raise ValueError(f"expected ',' or '{closing}', got {got!r}")


def _flow_value(text, index):
    index = _skip(text, index)
    if text[index] in "[{":
        return _flow(text, index)
    if text[index] in "\"'":
        return _quoted(text, index)
    return _token(text, index, ",]}")


def _token(text, index, stops):
    index = _skip(text, index)
    if index < len(text) and text[index] in "\"'":
        return _quoted(text, index)
    end = index
    while end < len(text) and text[end] not in stops:
        end += 1
    return text[index:end].strip(), end


def _quoted(text, index):
    quote = text[index]
    index += 1
    chars = []
    while index < len(text):
        char = text[index]
        if char == "\\":
            chars.append(text[index + 1])
            index += 2
            continue
        if char == quote:
            return "".join(chars), index + 1
        chars.append(char)
        index += 1
    raise ValueError("unterminated string")
