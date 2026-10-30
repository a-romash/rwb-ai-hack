"""Recorded-answer doubles for analysis/spec: thin wrappers over harness.fakes."""
from __future__ import annotations

from pathlib import Path
from typing import Callable
import json

from harness.fakes import FakeLLM as _PlatformFakeLLM
from harness.fakes import FakeSandbox as _PlatformFakeSandbox
from stages.analysis.compat import StageInput, StageOutput


def FakeLLM(responses: dict, *, context_window: int = 32768) -> _PlatformFakeLLM:
    """Answers recorded by task_id (stages/*/tests/fixtures/*-responses.json)."""
    return _PlatformFakeLLM.recorded(responses, context_window=context_window)


def FakeSandbox() -> _PlatformFakeSandbox:
    """analysis/spec never run the sandbox: any call fails the test."""
    return _PlatformFakeSandbox({})


def load_responses(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_stage_locally(execute: Callable, *, stage: str, requirements: str,
                      workspace: Path, llm, artifacts: dict[str, str] | None = None,
                      autonomy: str = "A2", answers: dict[str, str] | None = None) -> StageOutput:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "input").mkdir(exist_ok=True)
    (workspace / "input/requirements.md").write_text(requirements, encoding="utf-8")
    inp = StageInput(run_id="local", stage=stage, attempt=1, requirements=requirements, artifacts=artifacts or {}, autonomy=autonomy, answers=answers or {})
    return execute(inp, workspace, llm, FakeSandbox())
