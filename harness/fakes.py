"""Deterministic test doubles; no database, network, Celery or Docker needed."""
from collections import deque
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from contracts.stage import (
    BudgetExceeded, ContractError, LLM, Sandbox, SandboxKind, SandboxResult,
    SandboxTarget, StageInput, StageOutput,
)


def workspace_path(workspace: Path, relative: str) -> Path:
    """Resolve a relative artifact path, rejecting escapes including symlinks."""
    root = workspace.resolve()
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts:
        raise ContractError(f"Недопустимый путь артефакта: {relative}")
    try:
        resolved = (root / path).resolve()
        resolved.relative_to(root)
    except (ValueError, OSError, RuntimeError) as exc:
        raise ContractError(f"Путь выходит за workspace: {relative}") from exc
    return resolved


def _existing(workspace: Path, relative: str) -> None:
    path = workspace_path(workspace, relative)
    if not path.exists():
        raise ContractError(f"Артефакт не существует: {relative}")
    # Directory artifacts must not hide symlinks pointing outside the workspace.
    if path.is_dir():
        # Only a symlink can point outside; resolving every file took minutes over node_modules on a bind mount.
        for child in path.rglob("*"):
            if child.is_symlink():
                workspace_path(workspace, str(child.relative_to(workspace.resolve())))


class FakeLLM:
    """Keys: task_class or (task_class, task_id); exact task keys take priority.

    budget_after=N allows N calls; later calls raise BudgetExceeded.
    Missing/exhausted scripts fail explicitly rather than inventing an answer.
    FakeLLM.recorded() replays answers recorded by task_id (or task_class) instead of queues.
    """
    def __init__(self, responses: dict[str | tuple[str, str], list], *, budget_after: int | None = None,
                 context_window: int = 32768):
        self.responses = {key: deque(values) for key, values in responses.items()}
        self.recordings: dict[str, object] = {}
        self.budget_after = budget_after
        self.context_window = context_window
        self.calls: list[dict] = []

    @classmethod
    def recorded(cls, answers: dict[str, object], *, context_window: int = 32768) -> "FakeLLM":
        """One reusable answer per task_id (falling back to task_class); a callable gets the call."""
        fake = cls({}, context_window=context_window)
        fake.recordings = dict(answers)
        return fake

    def __call__(self, *, task_class: str, system: str, user: str,
                 output: type[BaseModel] | Literal["code", "text"],
                 task_id: str | None = None) -> BaseModel | str:
        self.calls.append(dict(task_class=task_class, system=system, user=user, output=output, task_id=task_id))
        if self.budget_after is not None and len(self.calls) > self.budget_after:
            raise BudgetExceeded("Бюджет FakeLLM исчерпан")
        if self.recordings:
            value = self.recordings.get(task_id, self.recordings.get(task_class))
            if value is None:
                raise ContractError(f"В FakeLLM нет записанного ответа для {task_id}")
            if callable(value):
                value = value(self.calls[-1])
        else:
            key = (task_class, task_id) if (task_class, task_id) in self.responses else task_class
            if not self.responses.get(key):
                raise AssertionError(f"Нет ответа FakeLLM для {key!r}")
            value = self.responses[key].popleft()
        if isinstance(value, Exception):
            raise value
        if output in ("code", "text"):
            if self.recordings and not isinstance(value, str):
                value = str(value)
            if not isinstance(value, str):
                raise ContractError("FakeLLM ожидает строковый ответ")
            return value
        try:
            return output.model_validate_json(value) if isinstance(value, str) else output.model_validate(value)
        except ValidationError as exc:
            raise ContractError(str(exc)) from exc


class FakeSandbox:
    def __init__(self, script: dict[tuple[str, str], list[SandboxResult]]):
        self.script = {key: deque(values) for key, values in script.items()}
        self.calls: list[dict] = []

    def run(self, kind: SandboxKind, target: SandboxTarget, *,
            filter: str | None = None, timeout_s: int = 600) -> SandboxResult:
        self.calls.append(dict(kind=kind, target=target, filter=filter, timeout_s=timeout_s))
        key = (kind, target)
        if not self.script.get(key):
            raise AssertionError(f"Нет результата FakeSandbox для {key!r}")
        value = self.script[key].popleft()
        if isinstance(value, Exception):
            raise value
        return SandboxResult.model_validate(value).model_copy(deep=True)


def run_stage_locally(stage_module, inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    """Validate boundary and paths. This helper is not a process sandbox."""
    try:
        inp = StageInput.model_validate(inp)
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        for relative in [*inp.attachments, *inp.artifacts.values()]:
            _existing(workspace, relative)
        output = StageOutput.model_validate(stage_module.execute(inp, workspace, llm, sandbox))
        for relative in output.artifacts.values():
            _existing(workspace, relative)
        return output
    except ValidationError as exc:
        raise ContractError(str(exc)) from exc
