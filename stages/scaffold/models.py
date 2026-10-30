"""Local stand-ins used when contracts.hooks is not importable.

HookSpec mirrors contracts.hooks.HookSpec.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HookContract:
    summary: str
    pre: list[str] = field(default_factory=list)
    post: list[str] = field(default_factory=list)


@dataclass
class HookExample:
    input: dict[str, Any]
    expected: str
    ac: str


@dataclass
class HookSpec:
    # Mirrors contracts.hooks.HookSpec.
    id: str
    file: str
    language: str
    kind: str
    signature: str
    refs: list[str]
    contract: HookContract
    examples: list[HookExample] = field(default_factory=list)
    allowed_api: list[str] = field(default_factory=list)
    max_lines: int = 60
    stub: str = "neutral"


@dataclass
class StageResult:
    artifacts: dict[str, str]
    summary: str
