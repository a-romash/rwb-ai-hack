"""Pipeline runs and audit records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("stage_status", "stages", type_="check")
    op.create_table("runs",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete="CASCADE"), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('autonomy', sa.String(length=2), nullable=False),
        sa.Column('spec_version', sa.Integer(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=False),
        sa.Column('workspace_path', sa.Text(), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('tokens_limit', sa.Integer(), nullable=False),
        sa.Column('minutes_limit', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_runs_project_id', 'runs', ['project_id'])
    op.create_table("stage_runs",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('attempt', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('input_hash', sa.String(length=64)),
        sa.Column('output_commit', sa.String(length=64)),
        sa.Column('summary', sa.Text()),
        sa.Column('error', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('queued_at', sa.DateTime(timezone=True)),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('finished_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('run_id', 'stage', 'attempt', name='uq_stage_run_attempt'),
    )
    op.create_index('ix_stage_runs_run_id', 'stage_runs', ['run_id'])
    op.create_table("artifacts",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('stage_run_id', sa.Uuid(), sa.ForeignKey('stage_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('stage_run_id', 'name', name='uq_artifact_stage_name'),
    )
    op.create_index('ix_artifacts_run_id', 'artifacts', ['run_id'])
    op.create_index('ix_artifacts_stage_run_id', 'artifacts', ['stage_run_id'])
    op.create_table("gate_results",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('stage_run_id', sa.Uuid(), sa.ForeignKey('stage_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('gate', sa.String(length=20), nullable=False),
        sa.Column('round', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('decided_by', sa.String(length=20), nullable=False),
        sa.Column('findings', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_gate_results_stage_run_id', 'gate_results', ['stage_run_id'])
    op.create_table("spec_flags",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('spec_version', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('gate', sa.String(length=20)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_spec_flags_run_id', 'spec_flags', ['run_id'])
    op.create_table("questions",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('stage_run_id', sa.Uuid(), sa.ForeignKey('stage_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('qid', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('answer', sa.Text()),
        sa.Column('answered_by', sa.String(length=20)),
        sa.Column('deadline', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('stage_run_id', 'qid', name='uq_question_stage_qid'),
    )
    op.create_index('ix_questions_stage_run_id', 'questions', ['stage_run_id'])
    op.create_index('ix_questions_run_id', 'questions', ['run_id'])
    op.create_table("test_hashes",
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), primary_key=True),
        sa.Column('path', sa.Text(), primary_key=True),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table("events",
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_events_run_id', 'events', ['run_id'])
    op.execute('''CREATE FUNCTION notify_pipeline_event() RETURNS trigger AS $$
        BEGIN
            PERFORM pg_notify('pipeline_events', NEW.run_id::text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql''')
    op.execute('CREATE TRIGGER events_notify AFTER INSERT ON events FOR EACH ROW EXECUTE FUNCTION notify_pipeline_event()')
    op.create_table("llm_calls",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('stage_run_id', sa.Uuid(), sa.ForeignKey('stage_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('task_id', sa.String(length=100)),
        sa.Column('task_class', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=200), nullable=False),
        sa.Column('prompt_sha', sa.String(length=64)),
        sa.Column('context_profile', sa.String(length=10), nullable=False),
        sa.Column('tokens_in', sa.Integer()),
        sa.Column('tokens_cached', sa.Integer()),
        sa.Column('tokens_out', sa.Integer()),
        sa.Column('tokens_reasoning', sa.Integer()),
        sa.Column('from_cache', sa.Boolean(), nullable=False),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('repair_rounds', sa.Integer(), nullable=False),
        sa.Column('ts_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ts_end', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_llm_calls_run_id', 'llm_calls', ['run_id'])
    op.create_index('ix_llm_calls_stage_run_id', 'llm_calls', ['stage_run_id'])
    op.create_table("tool_runs",
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('run_id', sa.Uuid(), sa.ForeignKey('runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('stage_run_id', sa.Uuid(), sa.ForeignKey('stage_runs.id', ondelete="CASCADE"), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=False),
        sa.Column('target', sa.String(length=30), nullable=False),
        sa.Column('exit_code', sa.Integer(), nullable=False),
        sa.Column('ok', sa.Boolean(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_tool_runs_run_id', 'tool_runs', ['run_id'])
    op.create_index('ix_tool_runs_stage_run_id', 'tool_runs', ['stage_run_id'])


def downgrade():
    op.drop_table("tool_runs")
    op.drop_table("llm_calls")
    op.drop_table("events")
    op.execute("DROP FUNCTION notify_pipeline_event()")
    op.drop_table("test_hashes")
    op.drop_table("questions")
    op.drop_table("spec_flags")
    op.drop_table("gate_results")
    op.drop_table("artifacts")
    op.drop_table("stage_runs")
    op.drop_table("runs")
    op.create_check_constraint("stage_status", "stages", "status = 'not_started'")
