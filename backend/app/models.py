from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
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
        CheckConstraint("status = 'not_started'", name="stage_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="not_started")
