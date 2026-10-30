"""Run management API; stage execution lives in app.runner."""
import asyncio
import json
import os
import select as socket_select

import psycopg2
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_session
from app.models import Artifact, Event, GateResult, LLMCall, Project, Question, Run, SpecFlag, StageRun, ToolRun
from contracts.api import (AnswersCreate, ArtifactRead, EventRead, GateDecisionCreate,
                           MetricsRead, RunCreate, RunRead, RunSummary)
from contracts.stage import ContractError
from harness.fakes import workspace_path
from harness.registry import STAGES, STAGES_BY_KEY
from app.projects import project_attachments
from harness.workspace import create_workspace

router = APIRouter(tags=["runs"])
Database = Annotated[Session, Depends(get_session)]


def get_run(session: Session, run_id: UUID) -> Run:
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Прогон не найден")
    return run


def summary(run):
    return {key: getattr(run, key) for key in ("id", "project_id", "status", "autonomy", "spec_version", "created_at", "finished_at")}


def event_dict(event):
    return {"id": event.id, "type": event.type, "ts": event.ts.isoformat(), "payload": event.payload}


def metrics(session, run_id):
    calls = session.scalars(select(LLMCall).where(LLMCall.run_id == run_id)).all()
    tools = session.scalars(select(ToolRun).where(ToolRun.run_id == run_id)).all()
    stages = {s.id: s.stage for s in session.scalars(select(StageRun).where(StageRun.run_id == run_id)).all()}
    manual = len(session.scalars(select(GateResult).join(StageRun, GateResult.stage_run_id == StageRun.id).where(StageRun.run_id == run_id, GateResult.decided_by == "human")).all())
    def aggregate(selected, selected_tools, interventions=0):
        data = {"calls": len(selected), "unknown_usage_calls": sum(not c.from_cache and (c.tokens_in is None or c.tokens_out is None) for c in selected),
                "latency_ms": sum(c.latency_ms or 0 for c in selected), "tool_duration_ms": sum(t.duration_ms for t in selected_tools),
                "manual_interventions": interventions}
        for attr in ("tokens_in", "tokens_out", "tokens_cached", "tokens_reasoning"):
            values = [getattr(c, attr) for c in selected if not c.from_cache and getattr(c, attr) is not None]
            data[attr] = sum(values) if values else None
        return data
    return {"totals": aggregate(calls, tools, manual),
            "by_stage": [{"stage": key, **aggregate([c for c in calls if stages.get(c.stage_run_id) == key], [t for t in tools if stages.get(t.stage_run_id) == key])} for key in dict.fromkeys(stages.values())],
            "by_task_class": [{"task_class": key, **aggregate([c for c in calls if c.task_class == key], [])} for key in dict.fromkeys(c.task_class for c in calls)]}


def run_read(session, run):
    stage_rows = session.scalars(select(StageRun).where(StageRun.run_id == run.id).order_by(StageRun.attempt.desc())).all()
    latest = {}
    for row in stage_rows:
        latest.setdefault(row.stage, row)
    items = []
    for spec in STAGES:
        row = latest.get(spec.key)
        if not row:
            continue
        gate = session.scalar(select(GateResult).where(GateResult.stage_run_id == row.id).order_by(GateResult.created_at.desc(), GateResult.id.desc()).limit(1))
        gate_data = {"gate": gate.gate, "passed": gate.passed, "decided_by": gate.decided_by, "findings": gate.findings} if gate else None
        items.append({"key": row.stage, "title": spec.title, "rwb_stage": spec.rwb_stage, "participants": list(spec.participants),
                      "status": row.status, "attempt": row.attempt, "started_at": row.started_at, "finished_at": row.finished_at,
                      "error": row.error, "summary": row.summary, "gate": gate_data})
    flags = session.scalars(select(SpecFlag).where(SpecFlag.run_id == run.id)).all()
    questions = session.scalars(select(Question).where(Question.run_id == run.id, Question.answer.is_(None))).all()
    used = metrics(session, run.id)["totals"]
    tokens = None if used["unknown_usage_calls"] else (used["tokens_in"] or 0) + (used["tokens_out"] or 0)
    start = run.started_at or run.created_at
    end = run.finished_at or datetime.now(timezone.utc)
    return {**summary(run), "budget": {"tokens_used": tokens, "tokens_limit": run.tokens_limit,
           "minutes_used": max(0, (end - start).total_seconds() / 60), "minutes_limit": run.minutes_limit},
           "stages": items, "flags": [{"path": f.path, "status": f.status, "reason": f.reason, "gate": f.gate} for f in flags],
           "questions": [q.payload for q in questions]}


@router.post("/projects/{project_id}/runs", status_code=201, response_model=RunRead)
def create_run(project_id: UUID, data: RunCreate, session: Database):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Проект не найден")
    run_id = uuid4()
    base = Path(os.environ.get("WORKSPACES_DIR", "workspaces")).resolve()
    workspace = None
    try:
        workspace = create_workspace(base, project_id, run_id, project.requirements, project_attachments(project_id))
        run = Run(id=run_id, project_id=project_id, requirements=project.requirements, workspace_path=str(workspace),
                  autonomy=data.autonomy, tokens_limit=data.budget.tokens, minutes_limit=data.budget.minutes,
                  config={"fake_stages": os.environ.get("PIPELINE_FAKE_STAGES", "").lower() in ("1", "true")})
        session.add(run)
        session.flush()
        session.add_all([StageRun(run_id=run_id, stage=stage.key, attempt=1) for stage in STAGES])
        session.add(Event(run_id=run_id, type="run.created", payload={}))
        session.commit()
    except Exception:
        session.rollback()
        import shutil
        if workspace is not None:
            shutil.rmtree(workspace)
        raise
    from app.runner import advance
    advance(run_id)
    session.expire_all()
    return run_read(session, get_run(session, run_id))


@router.get("/projects/{project_id}/runs", response_model=list[RunSummary])
def list_runs(project_id: UUID, session: Database):
    if not session.get(Project, project_id):
        raise HTTPException(404, "Проект не найден")
    return [summary(row) for row in session.scalars(select(Run).where(Run.project_id == project_id).order_by(Run.created_at.desc())).all()]


@router.get("/runs/{run_id}", response_model=RunRead)
def read_run(run_id: UUID, session: Database):
    return run_read(session, get_run(session, run_id))


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactRead])
def artifacts(run_id: UUID, session: Database):
    get_run(session, run_id)
    stage_rows = session.scalars(select(StageRun).where(StageRun.run_id == run_id).order_by(StageRun.attempt.desc())).all()
    latest = {}
    for stage in stage_rows:
        latest.setdefault(stage.stage, stage)
    accepted_ids = [stage.id for stage in latest.values() if stage.status == "succeeded"]
    rows = session.execute(select(Artifact, StageRun.stage).join(StageRun, Artifact.stage_run_id == StageRun.id).where(Artifact.run_id == run_id, Artifact.stage_run_id.in_(accepted_ids))).all()
    return [{"name": a.name, "path": a.path, "stage": stage, "hash": a.hash, "size": a.size, "kind": a.kind} for a, stage in rows]


@router.get("/runs/{run_id}/files")
def read_file(run_id: UUID, session: Database, path: str = Query(...)):
    run = get_run(session, run_id)
    try:
        target = workspace_path(Path(run.workspace_path), path)
    except ContractError:
        raise HTTPException(422, "Недопустимый путь") from None
    if not target.exists():
        raise HTTPException(404, "Файл не найден")
    if target.is_dir():
        result = []
        for child in sorted(target.iterdir()):
            try:
                workspace_path(Path(run.workspace_path), str(child.relative_to(Path(run.workspace_path))))
            except ContractError:
                continue
            result.append({"name": child.name, "type": "dir" if child.is_dir() else "file"})
        return {"type": "dir", "files": result}
    if not target.is_file() or target.stat().st_size > 2 * 1024 * 1024:
        raise HTTPException(422, "Файл недоступен или превышает 2 МБ")
    return FileResponse(target)


@router.get("/runs/{run_id}/events", response_model=list[EventRead])
def events(run_id: UUID, session: Database, after: int = Query(default=0, ge=0)):
    get_run(session, run_id)
    return [event_dict(row) for row in session.scalars(select(Event).where(Event.run_id == run_id, Event.id > after).order_by(Event.id)).all()]


@router.get("/runs/{run_id}/events/stream")
async def events_stream(run_id: UUID, request: Request, session: Database, last_event_id: str | None = Header(default=None)):
    get_run(session, run_id)
    if last_event_id is not None and (not last_event_id.isascii() or not last_event_id.isdecimal()):
        raise HTTPException(422, "Некорректный Last-Event-ID")
    async def stream():
        cursor = int(last_event_id or 0)
        # LISTEN before the first read closes the race between snapshot and subscribe.
        connection = psycopg2.connect(host=settings.postgres_host, port=settings.postgres_port,
                                      user=settings.postgres_user, password=settings.postgres_password,
                                      dbname=settings.postgres_db, connect_timeout=5)
        connection.autocommit = True
        try:
            with connection.cursor() as listener:
                listener.execute("LISTEN pipeline_events")
            while not await request.is_disconnected():
                with SessionLocal() as db:
                    rows = db.scalars(select(Event).where(Event.run_id == run_id, Event.id > cursor).order_by(Event.id)).all()
                    for row in rows:
                        cursor = row.id
                        yield f'id: {cursor}\nevent: {row.type}\ndata: {json.dumps(event_dict(row), ensure_ascii=False)}\n\n'
                # Notifications are hints; timeout ensures writes without NOTIFY and lost
                # notifications are still observed, and lets us check disconnects.
                readable = await asyncio.to_thread(socket_select.select, [connection], [], [], 2)
                if readable[0]:
                    connection.poll()
                    connection.notifies.clear()
                else:
                    yield ': keepalive\n\n'
        finally:
            connection.close()
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/runs/{run_id}/metrics", response_model=MetricsRead)
def get_metrics(run_id: UUID, session: Database):
    get_run(session, run_id)
    return metrics(session, run_id)


def invoke(action, *args):
    from app import runner
    try:
        getattr(runner, action)(*args)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(409, str(exc)) from None


@router.post("/runs/{run_id}/stages/{key}/retry", status_code=202)
def retry(run_id: UUID, key: str, session: Database):
    get_run(session, run_id)
    if key not in STAGES_BY_KEY:
        raise HTTPException(404, "Этап не найден")
    invoke("retry", run_id, key)
    return {"status": "accepted"}


@router.post("/runs/{run_id}/answers", status_code=202)
def answer(run_id: UUID, data: AnswersCreate, session: Database):
    get_run(session, run_id)
    invoke("answer", run_id, data.answers)
    return {"status": "accepted"}


@router.post("/runs/{run_id}/gates/{gate}/decision", status_code=202)
def decide(run_id: UUID, gate: str, data: GateDecisionCreate, session: Database):
    get_run(session, run_id)
    invoke("decide", run_id, gate, data.decision, data.comment)
    return {"status": "accepted"}


@router.post("/runs/{run_id}/cancel", status_code=202)
def cancel(run_id: UUID, session: Database):
    get_run(session, run_id)
    invoke("cancel", run_id)
    return {"status": "accepted"}
