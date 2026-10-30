"""Gate interfaces; concrete checks belong to the stage owners."""
from typing import Literal

from pydantic import BaseModel, Field

from contracts.stage import ElementFlag  # shared type, also available from this module


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
