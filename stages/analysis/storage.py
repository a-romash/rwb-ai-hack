"""Безопасное чтение и атомарная запись артефактов внутри workspace."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel

from stages.analysis.compat import ContractError


def inside(workspace: Path, relative: str | Path) -> Path:
    base = workspace.resolve()
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(base):
        raise ContractError("Путь выходит за рабочую папку")
    return candidate


def read_json(workspace: Path, relative: str) -> dict | list:
    try:
        return json.loads(inside(workspace, relative).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ContractError(f"Не удалось прочитать JSON-артефакт {relative}") from exc


def write_json(workspace: Path, relative: str, value: BaseModel | dict | list) -> str:
    path = inside(workspace, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value.model_dump(mode="json", by_alias=True) if isinstance(value, BaseModel) else value
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".analysis-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return str(path.relative_to(workspace.resolve()))


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_fingerprint(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
