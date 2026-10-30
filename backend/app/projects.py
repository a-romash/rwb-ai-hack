from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Project, Stage
from app.schemas import ProjectCreate, ProjectRead, ProjectSummary, ProjectUpdate

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
