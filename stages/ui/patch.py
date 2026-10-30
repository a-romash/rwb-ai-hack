"""Minimal JSON Patch (add, replace, remove) over plain JSON values; never mutates the input."""
import copy
from typing import Any

from stages.ui.llm_io import PatchOp


class PatchError(ValueError):
    pass


def _tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise PatchError(f"путь должен начинаться с /: {pointer}")
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer[1:].split("/")]


def _index(container: list, token: str, *, append: bool) -> int:
    if append and token == "-":
        return len(container)
    if not token.isdigit():
        raise PatchError(f"ожидался индекс массива, а не {token}")
    index = int(token)
    if index > len(container) or (not append and index == len(container)):
        raise PatchError(f"индекс {index} вне массива")
    return index


def apply_patch(doc: Any, ops: list[PatchOp]) -> Any:
    result = copy.deepcopy(doc)
    for op in ops:
        tokens = _tokens(op.path)
        parent = result
        for token in tokens[:-1]:
            try:
                parent = parent[_index(parent, token, append=False)] if isinstance(parent, list) else parent[token]
            except (KeyError, TypeError) as exc:
                raise PatchError(f"путь {op.path} не существует") from exc
        last = tokens[-1]
        if isinstance(parent, list):
            index = _index(parent, last, append=op.op == "add")
            if op.op == "add":
                parent.insert(index, copy.deepcopy(op.value))
            elif op.op == "replace":
                parent[index] = copy.deepcopy(op.value)
            else:
                del parent[index]
        elif isinstance(parent, dict):
            if op.op != "add" and last not in parent:
                raise PatchError(f"путь {op.path} не существует")
            if op.op == "remove":
                del parent[last]
            else:
                parent[last] = copy.deepcopy(op.value)
        else:
            raise PatchError(f"путь {op.path} не ведёт в объект или массив")
    return result
