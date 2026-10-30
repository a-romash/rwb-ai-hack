import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Project, Stage
from app.schemas import JobCreate, JobRead, ProjectCreate, ProjectRead, ProjectSummary, ProjectUpdate
from app.tasks import resolve_agent, run_agent

router = APIRouter(prefix="/projects", tags=["projects"])
Database = Annotated[Session, Depends(get_session)]

STAGES = (
    ("business_analysis", "Бизнес-анализ"),
    ("system_analysis", "Системный анализ"),
    ("interfaces", "Проектирование интерфейсов"),
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("database", "База данных"),
    ("testing", "Тестирование"),
    ("security", "Безопасность"),
    ("cicd", "CI/CD"),
    ("documentation", "Документация"),
)


def find_project(project_id: UUID, session: Session) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Проект не найден")
    return project


@router.get("", response_model=list[ProjectSummary])
def list_projects(session: Database):
    return session.scalars(select(Project).order_by(Project.created_at.desc(), Project.id.desc())).all()


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(data: ProjectCreate, session: Database):
    project = Project(**data.model_dump(), stages=[
        Stage(key=key, name=name, position=index)
        for index, (key, name) in enumerate(STAGES, start=1)
    ])
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, session: Database):
    return find_project(project_id, session)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: UUID, data: ProjectUpdate, session: Database):
    project = find_project(project_id, session)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    session.commit()
    session.refresh(project)
    return project


@router.post("/{project_id}/jobs", response_model=JobRead, status_code=202)
def create_job(project_id: UUID, data: JobCreate, session: Database):
    project = find_project(project_id, session)
    try:
        resolve_agent(data.agent)
    except LookupError:
        raise HTTPException(404, "Агент не найден") from None
    try:
        queued = run_agent.delay(data.prompt or project.requirements, data.agent, str(project.id))
    except Exception:
        raise HTTPException(503, "Очередь недоступна") from None
    return {"id": queued.id, "agent": data.agent, "status": "queued"}


@router.get("/{project_id}/jobs/{job_id}", response_model=JobRead)
def get_job(project_id: UUID, job_id: str, session: Database):
    find_project(project_id, session)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", job_id):
        raise HTTPException(404, "Задача не найдена")
    try:
        async_result = run_agent.AsyncResult(job_id)
        state = async_result.state
        payload = async_result.result if state == "SUCCESS" else None
    except Exception:
        raise HTTPException(503, "Очередь недоступна") from None
    if not isinstance(payload, dict):
        payload = {}
    return {
        "id": job_id,
        "status": state.lower(),
        "agent": payload.get("agent"),
        "subtype": payload.get("subtype"),
        "result": payload.get("result"),
        "num_turns": payload.get("num_turns"),
    }
