from typing import Literal
from pydantic import BaseModel, Field
from contracts.stage import ElementFlag

class ReportRun(BaseModel):
    id: str
    status: str
    autonomy: str
    started_at: str | None = None
    finished_at: str | None = None

class AcReport(BaseModel):
    id: str
    status: Literal['green','red','not_implemented','not_checked']
    tests: int
    hooks: list[str] = Field(default_factory=list)
    reason: str | None = None

class Report(BaseModel):
    schema_version: Literal[1] = 1
    run: ReportRun
    verdict: dict[str,int]
    ac: list[AcReport]
    assumptions: list[dict]
    flags: list[ElementFlag]
    checks: dict
    metrics: dict
    not_done: list[dict[str,str]]
    links: dict[str,str | None]
