from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    requirements: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    stages: Mapped[list["Stage"]] = relationship(
        cascade="all, delete-orphan", order_by="Stage.position", lazy="selectin",
    )


class Stage(Base):
    __tablename__ = "stages"
    __table_args__ = (
        UniqueConstraint("project_id", "key"),
        UniqueConstraint("project_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="not_started")


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    autonomy: Mapped[str] = mapped_column(String(2), default="A2")
    spec_version: Mapped[int] = mapped_column(default=1)
    requirements: Mapped[str] = mapped_column(Text)
    workspace_path: Mapped[str] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    tokens_limit: Mapped[int]
    minutes_limit: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StageRun(Base):
    __tablename__ = "stage_runs"
    __table_args__ = (UniqueConstraint("run_id", "stage", "attempt", name="uq_stage_run_attempt"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(50))
    attempt: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    input_hash: Mapped[str | None] = mapped_column(String(64))
    output_commit: Mapped[str | None] = mapped_column(String(64))
    summary: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (UniqueConstraint("stage_run_id", "name", name="uq_artifact_stage_name"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    stage_run_id: Mapped[UUID] = mapped_column(ForeignKey("stage_runs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    path: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(30))
    hash: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GateResult(Base):
    __tablename__ = "gate_results"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stage_run_id: Mapped[UUID] = mapped_column(ForeignKey("stage_runs.id", ondelete="CASCADE"), index=True)
    gate: Mapped[str] = mapped_column(String(20))
    round: Mapped[int]
    passed: Mapped[bool] = mapped_column(Boolean)
    decided_by: Mapped[str] = mapped_column(String(20))
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SpecFlag(Base):
    __tablename__ = "spec_flags"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    spec_version: Mapped[int]
    path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    gate: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("stage_run_id", "qid", name="uq_question_stage_qid"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    stage_run_id: Mapped[UUID] = mapped_column(ForeignKey("stage_runs.id", ondelete="CASCADE"), index=True)
    qid: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[str | None] = mapped_column(String(20))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class TestHash(Base):
    __tablename__ = "test_hashes"
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True)
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LLMCall(Base):
    __tablename__ = "llm_calls"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    stage_run_id: Mapped[UUID] = mapped_column(ForeignKey("stage_runs.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[str | None] = mapped_column(String(100))
    task_class: Mapped[str] = mapped_column(String(50))
    provider: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(200))
    prompt_sha: Mapped[str | None] = mapped_column(String(64))
    context_profile: Mapped[str] = mapped_column(String(10))
    tokens_in: Mapped[int | None]
    tokens_cached: Mapped[int | None]
    tokens_out: Mapped[int | None]
    tokens_reasoning: Mapped[int | None]
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(30), default="started")
    repair_rounds: Mapped[int] = mapped_column(default=0)
    ts_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ts_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ToolRun(Base):
    __tablename__ = "tool_runs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    stage_run_id: Mapped[UUID] = mapped_column(ForeignKey("stage_runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    target: Mapped[str] = mapped_column(String(30))
    exit_code: Mapped[int]
    ok: Mapped[bool] = mapped_column(Boolean)
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
