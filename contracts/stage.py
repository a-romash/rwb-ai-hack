"""Stable boundary between stages and the execution platform."""
from typing import Literal, Protocol

from pydantic import BaseModel, Field

Autonomy = Literal["A0", "A1", "A2"]
SandboxKind = Literal["build", "publish", "test", "lint", "scan", "up", "smoke", "e2e", "down"]
SandboxTarget = Literal["backend", "admin", "pwa", "stack"]


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
    attempt: int = Field(ge=1)
    autonomy: Autonomy = "A2"
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


class ContractError(Exception):
    """Input or output violates a stage contract."""


class StageFailed(Exception):
    """Execution failed; the platform may offer a manual retry."""


class BudgetExceeded(Exception):
    """Model budget exhausted; a stage may return a partial result."""


class LLM(Protocol):
    def __call__(self, *, task_class: str, system: str, user: str,
                 output: type[BaseModel] | Literal["code", "text"],
                 task_id: str | None = None) -> BaseModel | str: ...


class SandboxResult(BaseModel):
    ok: bool
    exit_code: int
    duration_ms: int
    failed: list[str]
    output_tail: str
    reports: dict[str, str] = Field(default_factory=dict)


class Sandbox(Protocol):
    def run(self, kind: SandboxKind, target: SandboxTarget, *,
            filter: str | None = None, timeout_s: int = 600) -> SandboxResult: ...
