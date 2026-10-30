"""Одноходовые запросы, ограничение окна и разбиение узкого контекста."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from stages.analysis.compat import BudgetExceeded, ContractError, LLM, StageFailed

ModelT = TypeVar("ModelT", bound=BaseModel)
ROOT = Path(__file__).resolve().parents[2]


def window(llm: LLM) -> int:
    # Шлюз может объявить меньший профиль; этап не меняет параметры генерации.
    return max(1024, min(int(getattr(llm, "context_window", 32768)), 32768))


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def prompt(agent: str) -> str:
    return (ROOT / "agents" / agent / "prompt.md").read_text(encoding="utf-8")


def size(agent: str, payload: dict, output: type[BaseModel]) -> int:
    # UTF-8 byte count — консервативная верхняя оценка для byte-fallback BPE.
    return len(prompt(agent).encode()) + len(encoded(payload).encode()) + len(encoded(output.model_json_schema()).encode()) + 256


def batches(llm: LLM, agent: str, output: type[BaseModel], items: list[Any], key: str,
            base: dict | None = None, item_limit: int | None = None) -> list[dict]:
    base = base or {}
    groups: list[dict] = []
    current: list[Any] = []
    for item in items:
        candidate = base | {key: current + [item]}
        if current and (size(agent, candidate, output) > window(llm) or (item_limit and len(current) >= item_limit)):
            groups.append(base | {key: current})
            current = []
        if size(agent, base | {key: [item]}, output) > window(llm):
            raise BudgetExceeded("Один элемент контекста превышает профиль окна; требуется более мелкое разбиение")
        current.append(item)
    if current or not items:
        groups.append(base | {key: current})
    return groups


def ask(llm: LLM, *, task_class: str, agent: str, payload: dict,
        output: type[ModelT], task_id: str) -> ModelT:
    if size(agent, payload, output) > window(llm):
        raise BudgetExceeded("Контекст запроса превышает профиль окна")
    # Закрывающий разделитель в недоверенных данных не может закончить блок.
    body = encoded(payload).replace("<", "\\u003c").replace(">", "\\u003e")
    user = "<<<SOURCE\n" + body + "\nSOURCE>>>"
    try:
        value = llm(task_class=task_class, system=prompt(agent), user=user,
                    output=output, task_id=task_id)
        if isinstance(value, BaseModel):
            return output.model_validate(value.model_dump(mode="json", by_alias=True))
        if isinstance(value, str):
            return output.model_validate_json(value)
        return output.model_validate(value)
    except BudgetExceeded:
        raise
    except (ValueError, TypeError) as exc:
        raise ContractError(f"Ответ модели не соответствует схеме {output.__name__}") from exc
    except (TimeoutError, ConnectionError, OSError) as exc:
        raise StageFailed("Шлюз модели недоступен") from exc
