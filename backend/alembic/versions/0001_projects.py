"""Projects and fixed pipeline stages."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "stages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.UniqueConstraint("project_id", "key"),
        sa.UniqueConstraint("project_id", "position"),
        sa.CheckConstraint("status = 'not_started'", name="stage_status"),
    )
    op.create_index("ix_stages_project_id", "stages", ["project_id"])


def downgrade():
    op.drop_table("stages")
    op.drop_table("projects")
