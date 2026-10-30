"""Serialize access to the single prepared prototype across projects and retries."""
from sqlalchemy import select, text

from app.models import Run, StageRun
from harness import prototype


def reserve(session, run_id=None):
    if not prototype.enabled():
        return
    # ponytail: one VPS slot; introduce per-slot locks only for concurrent prototypes.
    session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': int.from_bytes(b'rwb-demo', 'big')})
    active = select(Run.id).where(Run.status.in_(('pending', 'running', 'waiting')))
    executing = select(StageRun.id).where(StageRun.status == 'running')
    if run_id is not None:
        active = active.where(Run.id != run_id)
        executing = executing.where(StageRun.run_id != run_id)
    if session.scalar(active.limit(1)) or session.scalar(executing.limit(1)):
        raise ValueError('Другой прогон ещё работает. Дождитесь его завершения или остановите его.')
