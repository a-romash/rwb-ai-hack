"""Локальные фейки по §3; не реализуют чужой harness и не вызывают сеть."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from stages.analysis.compat import ContractError, StageInput, StageOutput


class FakeLLM:
    def __init__(self, responses: dict, *, context_window: int = 32768) -> None:
        self.responses = copy.deepcopy(responses)
        self.context_window = context_window
        self.calls: list[dict] = []

    @classmethod
    def from_file(cls, path: Path) -> "FakeLLM":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def __call__(self, *, task_class: str, system: str, user: str,
                 output: type[BaseModel] | str, task_id: str | None = None):
        self.calls.append({"task_class": task_class, "system": system, "user": user, "output": output.__name__ if isinstance(output, type) else output, "task_id": task_id})
        response = self.responses.get(task_id, self.responses.get(task_class))
        if response is None:
            raise ContractError(f"В FakeLLM нет записанного ответа для {task_id}")
        if isinstance(response, Exception):
            raise response
        if callable(response):
            response = response(self.calls[-1])
        return output.model_validate(response) if isinstance(output, type) else str(response)


class FakeSandbox:
    def run(self, *args, **kwargs):
        raise AssertionError("Этапы analysis/spec не должны запускать песочницу")


def run_stage_locally(execute: Callable, *, stage: str, requirements: str,
                      workspace: Path, llm: FakeLLM, artifacts: dict[str, str] | None = None,
                      autonomy: str = "A2", answers: dict[str, str] | None = None) -> StageOutput:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "input/requirements.md").write_text(requirements, encoding="utf-8")
    inp = StageInput(run_id="local", stage=stage, attempt=0, requirements=requirements, artifacts=artifacts or {}, autonomy=autonomy, answers=answers or {})
    return execute(inp, workspace, llm, FakeSandbox())
