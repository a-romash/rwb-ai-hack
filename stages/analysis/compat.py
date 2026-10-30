"""Граница §3.2–3.3; локальные дублёры, пока владелец не создал contracts.

При наличии contracts.stage/contracts.gates используются только их определения.
Файлы владельца платформы этот модуль не создаёт и не подменяет.
"""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

try:
    from contracts.stage import (  # type: ignore[import-not-found]
        BudgetExceeded, ContractError, ElementFlag, LLM, Question, Sandbox,
        StageFailed, StageInput, StageOutput,
    )
except ModuleNotFoundError as exc:
    if exc.name != "contracts.stage":
        raise

    class ContractError(Exception):
        pass

    class StageFailed(Exception):
        pass

    class BudgetExceeded(Exception):
        pass

    class Question(BaseModel):
        id: str
        text: str
        options: list[str]
        default: str
        why: str
        blocking: bool = False

    class ElementFlag(BaseModel):
        path: str
        status: Literal["questioned", "blocked_by"]
        reason: str
        gate: str | None = None

    class StageInput(BaseModel):
        run_id: str
        stage: str
        attempt: int
        autonomy: Literal["A0", "A1", "A2"] = "A2"
        requirements: str
        attachments: list[str] = Field(default_factory=list)
        artifacts: dict[str, str]
        answers: dict[str, str] = Field(default_factory=dict)
        snapshot: dict | None = None

    class StageOutput(BaseModel):
        artifacts: dict[str, str]
        summary: str
        flags: list[ElementFlag] = Field(default_factory=list)
        questions: list[Question] = Field(default_factory=list)

    class LLM(Protocol):
        def __call__(self, *, task_class: str, system: str, user: str,
                     output: type[BaseModel] | Literal["code", "text"],
                     task_id: str | None = None) -> BaseModel | str: ...

    class Sandbox(Protocol):
        def run(self, kind: Literal["build", "test", "lint", "scan", "up", "smoke", "e2e", "down"],
                target: Literal["backend", "admin", "pwa", "stack"], *, filter: str | None = None,
                timeout_s: int = 600) -> BaseModel: ...

try:
    from contracts.gates import Finding, GateResult  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:
    if exc.name != "contracts.gates":
        raise

    class Finding(BaseModel):
        path: str
        code: str
        severity: Literal["error", "warning"]
        message: str

    class GateResult(BaseModel):
        gate: str
        passed: bool
        decided_by: Literal["code", "human"] = "code"
        findings: list[Finding] = Field(default_factory=list)


def validate_input(inp: StageInput, expected: str) -> StageInput:
    try:
        result = StageInput.model_validate(inp)
    except (ValueError, TypeError) as exc:
        raise ContractError("Вход этапа не соответствует StageInput") from exc
    if result.stage != expected or result.attempt < 0:
        raise ContractError(f"Ожидался этап {expected} и неотрицательная попытка")
    return result
