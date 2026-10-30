"""Ограниченный адресами находок RFC 6902; изменения применяются к копии."""
from __future__ import annotations

import copy
import re
from typing import Literal

from pydantic import Field, JsonValue

from contracts.analysis import ContractModel
from stages.analysis.compat import ContractError, Finding


class PatchRejected(ContractError):
    """Предложенный ремонт отклонён; исходный артефакт остаётся валидным."""


class PatchOperation(ContractModel):
    op: Literal["add", "remove", "replace", "test", "move", "copy"]
    path: str
    value: JsonValue = None
    from_: str | None = Field(default=None, alias="from")


class PatchResponse(ContractModel):
    operations: list[PatchOperation]


def tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise PatchRejected("JSON Patch должен использовать корректный JSON Pointer")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def pointer(document: dict, address: str) -> str:
    if address.startswith("/"):
        tokens(address)
        return address
    parts = re.findall(r"[^.\[\]]+", address)
    current = document
    result: list[str] = []
    for part in parts:
        if isinstance(current, list):
            if part.isdecimal():
                index = int(part)
            else:
                matches = [i for i, item in enumerate(current) if isinstance(item, dict) and (item.get("id") == part or item.get("name") == part)]
                if len(matches) != 1:
                    raise PatchRejected("Адрес находки не разрешается в уникальный элемент")
                index = matches[0]
            result.append(str(index))
            current = current[index] if index < len(current) else None
        else:
            result.append(part)
            current = current.get(part) if isinstance(current, dict) else None
    return "/" + "/".join(part.replace("~", "~0").replace("/", "~1") for part in result)


def _at(document: dict, parts: list[str]):
    current = document
    for part in parts:
        if isinstance(current, list):
            if not part.isdecimal() or (len(part) > 1 and part.startswith("0")):
                raise PatchRejected("Недопустимый индекс JSON Pointer")
            current = current[int(part)]
        else:
            current = current[part]
    return current


def apply_patch(document: dict, patch: PatchResponse, findings: list[Finding]) -> dict:
    allowed = [tokens(pointer(document, finding.path)) for finding in findings]
    if not allowed and patch.operations:
        raise PatchRejected("Ремонт без адресов находок запрещён")
    result = copy.deepcopy(document)

    def authorized(parts: list[str]) -> bool:
        return any(parts[:len(root)] == root for root in allowed)

    def remove(parts: list[str]):
        parent = _at(result, parts[:-1])
        if isinstance(parent, list):
            if not parts[-1].isdecimal() or (len(parts[-1]) > 1 and parts[-1].startswith("0")):
                raise PatchRejected("Недопустимый индекс удаления JSON Patch")
            value = parent.pop(int(parts[-1]))
        else:
            value = parent.pop(parts[-1])
        return value

    def put(parts: list[str], value, insert: bool) -> None:
        parent = _at(result, parts[:-1])
        key = parts[-1]
        if parts[0] != "seed":
            if key == "id":
                raise PatchRejected("Изменение стабильного идентификатора запрещено")
            old = None
            if isinstance(parent, dict):
                old = parent.get(key)
            elif not insert and key.isdecimal() and int(key) < len(parent):
                old = parent[int(key)]
            if isinstance(old, dict) and "id" in old and (not isinstance(value, dict) or value.get("id") != old["id"]):
                raise PatchRejected("Замена элемента не должна менять его стабильный идентификатор")
        if isinstance(parent, list):
            if key != "-" and (not key.isdecimal() or (len(key) > 1 and key.startswith("0"))):
                raise PatchRejected("Недопустимый индекс записи JSON Patch")
            index = len(parent) if key == "-" and insert else int(key)
            if index < 0 or index > len(parent) or (not insert and index == len(parent)):
                raise PatchRejected("Индекс JSON Patch вне списка")
            if insert:
                parent.insert(index, value)
            else:
                parent[index] = value
        else:
            if not insert and key not in parent:
                raise PatchRejected("JSON Patch заменяет отсутствующее свойство")
            parent[key] = value

    try:
        for operation in patch.operations:
            parts = tokens(operation.path)
            if not authorized(parts):
                raise PatchRejected("JSON Patch меняет элемент вне адресов находок")
            if len(parts) < 2 and operation.op != "test":
                raise PatchRejected("Замена корня или целого раздела запрещена")
            if parts[-1] == "id" and parts[0] != "seed" and operation.op != "test":
                raise PatchRejected("Изменение стабильного идентификатора запрещено")
            if parts[0] == "requirements" and len(parts) == 2 and operation.op in ("remove", "move"):
                raise PatchRejected("Нельзя скрывать находку удалением исходного требования")
            if operation.op == "test":
                if _at(result, parts) != operation.value:
                    raise PatchRejected("Проверка test в JSON Patch не прошла")
            elif operation.op == "remove":
                remove(parts)
            elif operation.op in ("add", "replace"):
                if "value" not in operation.model_fields_set:
                    raise PatchRejected("Операция JSON Patch не содержит value")
                put(parts, copy.deepcopy(operation.value), operation.op == "add")
            else:
                if operation.from_ is None:
                    raise PatchRejected("Операция JSON Patch не содержит from")
                source = tokens(operation.from_)
                if operation.op == "move" and source[0] == "requirements" and len(source) == 2:
                    raise PatchRejected("Нельзя перемещать исходное требование из анализа")
                if not authorized(source):
                    raise PatchRejected("Источник move/copy находится вне адресов находок")
                if parts[:len(source)] == source and len(parts) > len(source):
                    raise PatchRejected("Нельзя переместить элемент в собственного потомка")
                value = copy.deepcopy(_at(result, source))
                if operation.op == "move":
                    remove(source)
                put(parts, value, True)
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise PatchRejected("JSON Patch неприменим к документу") from exc
    return result
