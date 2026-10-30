"""Studio wire models. HTTP endpoints are implemented in the next delivery."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from contracts.gates import GateResult
from contracts.stage import Autonomy, ElementFlag, Question

RunStatus = Literal["pending", "running", "waiting", "succeeded", "partial", "failed", "cancelled"]
StageStatus = Literal["pending", "queued", "running", "succeeded", "failed", "waiting_input", "waiting_human", "skipped", "stale"]


class RunBudget(BaseModel):
    tokens: int = Field(default=1_500_000, gt=0)
    minutes: int = Field(default=60, gt=0)


class RunCreate(BaseModel):
    autonomy: Autonomy = "A2"
    budget: RunBudget = Field(default_factory=RunBudget)


class BudgetRead(BaseModel):
    tokens_used: int | None = None
    tokens_limit: int
    minutes_used: float
    minutes_limit: int


class StageRunRead(BaseModel):
    key: str
    title: str
    rwb_stage: str
    participants: list[str]
    status: StageStatus
    attempt: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    summary: str | None = None
    gate: GateResult | None = None


class RunSummary(BaseModel):
    id: UUID
    project_id: UUID
    status: RunStatus
    autonomy: Autonomy
    spec_version: int
    created_at: datetime
    finished_at: datetime | None = None


class RunRead(RunSummary):
    prototype_url: str | None = None
    budget: BudgetRead
    stages: list[StageRunRead]
    flags: list[ElementFlag] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)


class EventRead(BaseModel):
    id: int
    type: str
    ts: datetime
    payload: dict


class ArtifactRead(BaseModel):
    name: str
    path: str
    stage: str
    hash: str
    size: int
    kind: Literal["json", "markdown", "dir", "text"]


class MetricTotals(BaseModel):
    calls: int = 0
    tokens_in: int | None = None
    tokens_cached: int | None = None
    tokens_out: int | None = None
    tokens_reasoning: int | None = None
    unknown_usage_calls: int = 0
    latency_ms: int = 0
    tool_duration_ms: int = 0
    manual_interventions: int = 0


class StageMetrics(MetricTotals):
    stage: str


class TaskClassMetrics(MetricTotals):
    task_class: str


class MetricsRead(BaseModel):
    totals: MetricTotals
    by_stage: list[StageMetrics] = Field(default_factory=list)
    by_task_class: list[TaskClassMetrics] = Field(default_factory=list)


class AnswersCreate(BaseModel):
    answers: dict[str, str]


class GateDecisionCreate(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = ""
