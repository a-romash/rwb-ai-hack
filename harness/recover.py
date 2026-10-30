"""Manual recovery after all workers are stopped."""
import argparse
import sys
from pathlib import Path
from uuid import UUID


def recover(run_id: UUID) -> int:
    root = Path(__file__).resolve().parent.parent
    if (root / 'backend' / 'app').is_dir():
        sys.path.insert(0, str(root / 'backend'))
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Run, StageRun, utc_now
    from app.runner import _event, _lock, advance

    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        if run is None:
            raise LookupError('Прогон не найден')
        rows = session.scalars(select(StageRun).where(StageRun.run_id == run_id, StageRun.status == 'running')).all()
        for row in rows:
            row.status = 'failed'
            row.error = 'Прервано: воркер остановлен'
            row.finished_at = utc_now()
            _event(session, run_id, 'stage.finished', {'stage': row.stage, 'attempt': row.attempt, 'status': 'failed', 'reason': 'worker_stopped'})
    if rows:
        advance(run_id)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Восстановить прерванный прогон после остановки всех воркеров')
    parser.add_argument('run_id', type=UUID)
    parser.add_argument('--worker-stopped', action='store_true', help='подтверждаю, что все воркеры остановлены')
    args = parser.parse_args(argv)
    if not args.worker_stopped:
        parser.error('остановите все воркеры и передайте --worker-stopped')
    try:
        count = recover(args.run_id)
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f'Прерванных этапов отмечено как failed: {count}')
    return 0
