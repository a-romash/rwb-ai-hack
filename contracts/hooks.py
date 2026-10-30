import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, RootModel


class HookContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    pre: list[str]
    post: list[str]


class HookExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input: dict[str, Any]
    expected: str
    ac: str


class HookSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    file: str
    language: str
    kind: Literal["validator", "calculator", "decider", "policy", "reaction"]
    signature: str
    refs: list[str]
    contract: HookContract
    examples: list[HookExample]
    allowed_api: list[str]
    max_lines: int
    stub: str


class HooksFile(RootModel[list[HookSpec]]):
    pass


def load_hooks(path: str | Path) -> list[HookSpec]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return HooksFile.model_validate(data).root
