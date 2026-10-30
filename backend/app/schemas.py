from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Requirements = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name
    requirements: Requirements


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Name | None = None
    requirements: Requirements | None = None

    @model_validator(mode="after")
    def reject_null_values(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


class StageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    name: str
    position: int
    status: Literal["not_started"]


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class ProjectRead(ProjectSummary):
    requirements: str
    stages: list[StageRead]


AgentId = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z][a-z0-9_-]{0,40}$")]


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent: AgentId
    prompt: Requirements | None = None


class JobRead(BaseModel):
    id: str
    status: str
    agent: str | None = None
    subtype: str | None = None
    result: str | None = None
    num_turns: int | None = None
