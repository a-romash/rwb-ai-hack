"""Sequential run scheduling; PostgreSQL remains the source of truth."""
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select, text, update

from app.database import SessionLocal
from app.models import Artifact, Event, GateResult, LLMCall, Question, Run, SpecFlag, StageRun, TestHash, ToolRun, utc_now
from harness.fakes import run_stage_locally
from harness.registry import STAGES, STAGES_BY_KEY
from harness.workspace import commit, describe, restore
from gates.core import run_gate
from contracts.stage import ContractError, StageInput


def _event(session, run_id, kind, payload):
    session.add(Event(run_id=run_id, type=kind, payload=payload))


def _lock(session, run_id):
    key = int.from_bytes(hashlib.sha256(str(run_id).encode()).digest()[:8], 'big', signed=True)
    session.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': key})


def _latest(session, run_id):
    rows = session.scalars(select(StageRun).where(StageRun.run_id == run_id).order_by(StageRun.attempt)).all()
    return {row.stage: row for row in rows}


APP_SECTIONS = frozenset({
    'meta', 'params', 'types', 'entities', 'roles', 'permissions', 'state_machines', 'hooks', 'commands',
    'queries', 'events', 'integrations', 'schedules', 'notifications', 'seed', 'scenarios', 'custom',
})


def _is_app_path(path):
    """Gate findings also address tests, builds and ui.json; only app.json paths have dependents."""
    head = path.removeprefix('app.').lstrip('/').replace('[', '.').split('.')[0].split('/')[0]
    return head in APP_SECTIONS


def _dependent_paths(root, artifacts, path):
    """Ask the specification owner for transitive dependents of an app.json element.

    A broken or missing specification must not turn a degraded result into a failed stage,
    so errors here only mean "no dependents known".
    """
    app_path = artifacts.get('app')
    if not app_path or not _is_app_path(path):
        return []
    from harness.fakes import workspace_path
    try:
        app_module = importlib.import_module('contracts.app')
        data = json.loads(workspace_path(root, app_path).read_text(encoding='utf-8'))
        paths = app_module.dependents(data, path)
    except Exception:
        logging.exception('Не удалось вычислить зависимости спецификации для %s', path)
        return []
    if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
        return []
    return sorted(set(paths) - {path})


def stage_flag_gate(stage):
    """Flags a stage reports itself carry no gate; tag them so a retry can drop them."""
    return f'stage:{stage}'


def advance(run_id):
    from app.tasks import run_stage
    pending = None
    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        if not run or run.status == 'cancelled':
            return
        stages = _latest(session, run_id)
        if any(x.status in ('running', 'queued', 'waiting_input', 'waiting_human') for x in stages.values()):
            return
        failed = any(x.status == 'failed' for k, x in stages.items() if k != 'report')
        report = stages['report']
        if failed:
            candidate = report if report.status == 'pending' else None
        else:
            candidate = next((stages[x.key] for x in STAGES if stages[x.key].status == 'pending'), None)
        if candidate:
            candidate.input_hash = input_hash(session, run, stages, candidate.stage)
            candidate.status = 'queued'
            candidate.queued_at = utc_now()
            run.status = 'running'
            run.started_at = run.started_at or utc_now()
            _event(session, run.id, 'stage.queued', {'stage': candidate.stage, 'attempt': candidate.attempt})
            pending = (str(candidate.id), STAGES_BY_KEY[candidate.stage].queue)
        else:
            run.status = 'failed' if failed or report.status == 'failed' else result_status(session, run_id, stages)
            run.finished_at = utc_now()
            _event(session, run.id, 'run.finished', {'status': run.status})
    if pending:
        try:
            run_stage.apply_async(args=[pending[0]], queue=pending[1])
        except Exception:
            # Reconciler republishes the durable queued record.
            pass


def _execute(stage_id):
    from harness.fakes import FakeLLM, FakeSandbox
    from app.llm_binding import make_llm
    with SessionLocal.begin() as session:
        row = session.execute(update(StageRun).where(StageRun.id == UUID(str(stage_id)), StageRun.status == 'queued').values(status='running', started_at=utc_now()).returning(StageRun)).scalar_one_or_none()
        if row is None:
            return
        run = session.get(Run, row.run_id)
        if run.status == 'cancelled':
            row.status = 'failed'; row.error = 'Прогон отменён'; return
        run_id, stage, attempt = run.id, row.stage, row.attempt
        root = Path(run.workspace_path)
        latest = _latest(session, run.id)
        accepted_ids = [item.id for item in latest.values() if item.status == 'succeeded' or (item.id == row.id and answers_present(session, row.id))]
        accepted_artifacts = session.scalars(select(Artifact).where(Artifact.run_id == run.id, Artifact.stage_run_id.in_(accepted_ids)).order_by(Artifact.created_at)).all()
        artifacts = {a.name: a.path for a in accepted_artifacts}
        frozen = [(a.path, a.hash) for a in accepted_artifacts if a.name in ('app', 'ui')]
        snapshot = None
        if stage == 'report':
            calls = session.scalars(select(LLMCall).where(LLMCall.run_id == run.id)).all()
            tools = session.scalars(select(ToolRun).where(ToolRun.run_id == run.id)).all()
            from app.runs import metrics
            snapshot = {'metrics': metrics(session, run.id), 'status': result_status(session, run.id, latest), 'stages': [{'stage': x.stage, 'status': x.status, 'attempt': x.attempt, 'error': x.error} for x in latest.values()],
                'flags': [{'path': x.path, 'status': x.status, 'reason': x.reason, 'gate': x.gate} for x in session.scalars(select(SpecFlag).where(SpecFlag.run_id == run.id))],
                'gates': [{'gate': x.gate, 'passed': x.passed, 'findings': x.findings} for x in session.scalars(select(GateResult).join(StageRun).where(StageRun.run_id == run.id))],
                'llm_calls': [{'task_class': x.task_class, 'status': x.status, 'tokens_in': x.tokens_in, 'tokens_out': x.tokens_out, 'from_cache': x.from_cache} for x in calls],
                'tool_runs': [{'kind': x.kind, 'target': x.target, 'ok': x.ok, 'duration_ms': x.duration_ms} for x in tools]}
        answers = {q.qid: q.answer for q in session.scalars(select(Question).where(Question.stage_run_id == row.id, Question.answer.is_not(None))).all()}
        inp = StageInput(run_id=str(run.id), stage=stage, attempt=attempt, autonomy=run.autonomy, requirements=run.requirements, artifacts=artifacts, answers=answers, snapshot=snapshot)
        test_hashes = [(item.path, item.hash) for item in session.scalars(select(TestHash).where(TestHash.run_id == run.id)).all()]
        fake = bool(run.config.get('fake_stages'))
        _event(session, run.id, 'stage.started', {'stage': stage, 'attempt': attempt})
    try:
        for path, digest in frozen:
            if describe(root, path)[0] != digest:
                raise ContractError(f'Замороженный артефакт изменён: {path}')
        if stage in ('develop', 'verify'):
            for path, digest in test_hashes:
                if describe(root, path)[0] != digest:
                    raise ContractError(f'Тест изменён без одобренного спора: {path}')
        module = importlib.import_module(f'harness.fake_stages.{stage}' if fake else STAGES_BY_KEY[stage].module)
        llm = FakeLLM({}) if fake else make_llm(run_id, UUID(str(stage_id)))
        if fake:
            sandbox = FakeSandbox({})
        else:
            class LazySandbox:
                _instance = None
                def approve_test_change(self, path, dispute_id, gate):
                    from app.test_integrity import approve_test_change
                    with SessionLocal.begin() as session:
                        approve_test_change(session, run_id, root, path, dispute_id, gate)
                def run(self, *args, **kwargs):
                    if self._instance is None:
                        from harness.sandbox import DockerSandbox
                        manifest_path = Path(__file__).resolve().parents[2] / 'templates/product/pack.json'
                        if not manifest_path.is_file():
                            raise ContractError('Не найден доверенный templates/product/pack.json')
                        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                        if not isinstance(manifest, dict):
                            raise ContractError('Некорректный pack.json')
                        from harness.sandbox import host_workspaces_dir
                        base = Path(os.environ.get('WORKSPACES_DIR', '/app/workspaces')).resolve()
                        host_root = host_workspaces_dir(base) / root.resolve().relative_to(base)
                        def record(kind, target, result):
                            with SessionLocal.begin() as session:
                                session.add(ToolRun(run_id=run_id, stage_run_id=UUID(str(stage_id)), kind=kind, target=target,
                                    exit_code=result.exit_code, ok=result.ok, duration_ms=result.duration_ms))
                        self._instance = DockerSandbox(root / "product", str(run_id), manifest, host_workspace=host_root / "product", report_prefix="product", record=record)
                    return self._instance.run(*args, **kwargs)
            sandbox = LazySandbox()
        output = run_stage_locally(module, inp, root, llm, sandbox)
        gates = []
        for name in (() if output.questions and inp.autonomy in ('A0', 'A1') else STAGES_BY_KEY[stage].gates):
            if fake:
                from contracts.gates import GateResult as GateModel, Finding
                results = [GateModel(gate=name, passed=True, findings=[Finding(path='', code='GATE_MISSING', severity='warning', message='Фейковый этап не проверен')])]
            else:
                output, results = run_gate(name, module, inp, root, llm, output, allow_missing=False, sandbox=sandbox)
            gates.extend((name, n, value) for n, value in enumerate(results))
        with SessionLocal() as session:
            test_hashes = [(item.path, item.hash) for item in session.scalars(select(TestHash).where(TestHash.run_id == run_id)).all()]
        for path, digest in frozen:
            if describe(root, path)[0] != digest:
                raise ContractError(f'Замороженный артефакт изменён: {path}')
        if stage in ('develop', 'verify'):
            for path, digest in test_hashes:
                if describe(root, path)[0] != digest:
                    raise ContractError(f'Тест изменён без одобренного спора: {path}')
        with SessionLocal.begin() as session:
            _lock(session, run_id)
            row = session.get(StageRun, UUID(str(stage_id)))
            if row.status != 'running' or _latest(session, run_id)[stage].id != row.id:
                return
            run = session.get(Run, run_id)
            if run.status == 'cancelled':
                row.status, row.finished_at = 'skipped', utc_now()
                return
            metadata = [(name, path, *describe(root, path)) for name, path in output.artifacts.items()]
            # Re-entry after a question replaces this attempt's accepted output atomically.
            session.execute(delete(Artifact).where(Artifact.stage_run_id == row.id))
            session.execute(delete(GateResult).where(GateResult.stage_run_id == row.id))
            if stage == 'tests' and not fake:
                from app.test_integrity import accept_manifest
                accept_manifest(session, run_id, root, output.artifacts.get('tests', 'reports/tests.json'))
            for name, path, digest, size, kind in metadata:
                if name in ('app', 'ui'):
                    from harness.fakes import workspace_path
                    workspace_path(root, path).chmod(0o444)
            revision = commit(root, f'stage({stage}): {output.summary}')
            for name, path, digest, size, kind in metadata:
                session.add(Artifact(run_id=run_id, stage_run_id=row.id, name=name, path=path, hash=digest, size=size, kind=kind))
            for name, n, result in gates:
                session.add(GateResult(stage_run_id=row.id, gate=name, round=n, passed=result.passed, decided_by=result.decided_by, findings=[f.model_dump() for f in result.findings]))
                _event(session, run_id, 'gate.result', {'stage': stage, 'gate': name, 'round': n, 'passed': result.passed})
                for finding in result.findings:
                    if n == max(r for g, r, _ in gates if g == name) and finding.severity == 'error':
                        session.add(SpecFlag(run_id=run_id, spec_version=1, path=finding.path, status='questioned', reason=finding.message, gate=name))
                        for dependent in _dependent_paths(root, {**inp.artifacts, **output.artifacts}, finding.path):
                            session.add(SpecFlag(run_id=run_id, spec_version=1, path=dependent, status='blocked_by', reason=finding.message, gate=name))
            session.execute(delete(SpecFlag).where(SpecFlag.run_id == run_id, SpecFlag.gate == stage_flag_gate(stage)))
            for flag in output.flags:
                session.add(SpecFlag(run_id=run_id, spec_version=1, path=flag.path, status=flag.status, reason=flag.reason,
                                     gate=flag.gate or stage_flag_gate(stage)))
            row.output_commit, row.summary = revision, output.summary
            run = session.get(Run, run_id)
            if run.status == 'cancelled':
                row.status, row.finished_at = 'skipped', utc_now()
            elif output.questions and run.autonomy in ('A0', 'A1'):
                for question in output.questions:
                    if not session.scalar(select(Question.id).where(Question.stage_run_id == row.id, Question.qid == question.id)):
                        session.add(Question(run_id=run_id, stage_run_id=row.id, qid=question.id, payload=question.model_dump()))
                row.status, run.status = 'waiting_input', 'waiting'
                _event(session, run_id, 'question.asked', {'stage': stage, 'questions': [q.model_dump() for q in output.questions]})
            elif STAGES_BY_KEY[stage].gates and (run.autonomy == 'A0' or (run.autonomy == 'A1' and stage == 'spec')):
                row.status, run.status = 'waiting_human', 'waiting'
            else:
                row.status, row.finished_at = 'succeeded', utc_now()
            _event(session, run_id, 'stage.finished', {'stage': stage, 'status': row.status})
    except Exception as exc:
        with SessionLocal.begin() as session:
            row = session.get(StageRun, UUID(str(stage_id)))
            if row and row.status == 'running':
                row.status, row.error, row.finished_at = 'failed', _safe_error(exc), utc_now()
                _event(session, run_id, 'stage.finished', {'stage': stage, 'status': 'failed'})
    advance(run_id)



def _safe_error(exc):
    message = f'{type(exc).__name__}: {str(exc)[:1000]}'
    for name, value in os.environ.items():
        if value and len(value) >= 4 and any(part in name.upper() for part in ('KEY', 'TOKEN', 'PASSWORD', 'SECRET')):
            message = message.replace(value, '[скрыто]')
    return message


def execute(stage_id):
    try:
        return _execute(stage_id)
    except Exception as exc:
        # Fail durable queued/running state even if input assembly or module setup fails.
        run_id = None
        with SessionLocal.begin() as session:
            row = session.get(StageRun, UUID(str(stage_id)))
            if row and row.status in ('queued', 'running'):
                row.status, row.error, row.finished_at = 'failed', _safe_error(exc), utc_now()
                run_id = row.run_id
                _event(session, run_id, 'stage.finished', {'stage': row.stage, 'status': 'failed'})
        if run_id:
            advance(run_id)

def reconcile():
    from datetime import timedelta
    from app.tasks import run_stage
    with SessionLocal() as session:
        rows = session.scalars(select(StageRun).where(StageRun.status == 'queued', StageRun.queued_at < utc_now() - timedelta(seconds=30))).all()
        for row in rows:
            run_stage.apply_async(args=[str(row.id)], queue=STAGES_BY_KEY[row.stage].queue)


def retry(run_id, key):
    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        if not run or run.status in ('running', 'waiting', 'cancelled'):
            raise ValueError('Повтор доступен только для неактивного прогона')
        latest = _latest(session, run_id)
        if key not in latest or latest[key].status != 'failed':
            raise ValueError('Повтор доступен только для упавшего этапа')
        index = next(i for i, stage in enumerate(STAGES) if stage.key == key)
        predecessor = latest[STAGES[index - 1].key] if index else None
        root = Path(run.workspace_path)
        if predecessor and predecessor.output_commit:
            revision = predecessor.output_commit
        else:
            import subprocess
            revision = subprocess.check_output(['git', '-C', str(root), 'rev-list', '--max-parents=0', 'HEAD'], text=True).strip()
        restore(root, revision)
        # Earlier stages remain accepted, so only invalidate downstream gate flags.
        invalid_gates = [gate for item in STAGES[index:] for gate in (*item.gates, stage_flag_gate(item.key))]
        session.execute(delete(SpecFlag).where(SpecFlag.run_id == run_id, SpecFlag.gate.in_(invalid_gates)))
        if index <= next(i for i, item in enumerate(STAGES) if item.key == 'tests'):
            session.execute(delete(TestHash).where(TestHash.run_id == run_id))
        for stage in STAGES[index:]:
            old = latest[stage.key]
            old.status = 'stale' if old.status not in ('failed', 'pending') else old.status
            session.add(StageRun(run_id=run_id, stage=stage.key, attempt=old.attempt + 1, status='pending'))
        run.status, run.finished_at = 'pending', None
        _event(session, run_id, 'run.retry', {'stage': key})
    advance(run_id)


def cancel(run_id):
    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        if not run or run.status in ('succeeded', 'failed', 'partial', 'cancelled'):
            raise ValueError('Прогон уже завершён')
        run.status, run.finished_at = 'cancelled', utc_now()
        for stage in _latest(session, run_id).values():
            if stage.status in ('queued', 'pending', 'waiting_input', 'waiting_human'):
                stage.status = 'skipped'
        _event(session, run_id, 'run.finished', {'status': 'cancelled'})


def answer(run_id, answers):
    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        stages = _latest(session, run_id)
        stage = next((row for row in stages.values() if row.status == 'waiting_input'), None)
        if not run or not stage:
            raise ValueError('Прогон не ожидает ответов')
        questions = session.scalars(select(Question).where(Question.stage_run_id == stage.id, Question.answer.is_(None))).all()
        if set(answers) != {q.qid for q in questions} or any(not v.strip() for v in answers.values()):
            raise ValueError('Необходимо ответить на все вопросы')
        for question in questions:
            question.answer, question.answered_by = answers[question.qid], 'user'
        # Re-enter execute with saved answers; stages must preserve their own checkpoint
        # to avoid repeating model work. The interface has no generic continuation state.
        # Preserve this attempt's artifacts as the stage's resume checkpoint.
        stage.status, stage.finished_at = 'queued', None
        stage.queued_at = utc_now()
        run.status = 'running'
        stage_id, queue = str(stage.id), STAGES_BY_KEY[stage.stage].queue
        _event(session, run_id, 'stage.queued', {'stage': stage.stage, 'attempt': stage.attempt})
    from app.tasks import run_stage
    run_stage.apply_async(args=[stage_id], queue=queue)


def decide(run_id, gate, decision, comment):
    with SessionLocal.begin() as session:
        _lock(session, run_id)
        run = session.get(Run, run_id)
        stage = next((row for row in _latest(session, run_id).values() if row.status == 'waiting_human' and gate in STAGES_BY_KEY[row.stage].gates), None)
        if not run or not stage or decision not in ('approve', 'reject'):
            raise ValueError('Гейт не ожидает решения')
        session.add(GateResult(stage_run_id=stage.id, gate=gate, round=0, passed=decision == 'approve', decided_by='human', findings=[]))
        prior = session.scalars(select(GateResult.gate).where(GateResult.stage_run_id == stage.id, GateResult.decided_by == 'human', GateResult.passed.is_(True))).all()
        outstanding = set(STAGES_BY_KEY[stage.stage].gates) - set(prior) - {gate}
        stage.status = ('waiting_human' if outstanding and decision == 'approve' else ('succeeded' if decision == 'approve' else 'failed'))
        stage.error = None if decision == 'approve' else (comment or 'Отклонено пользователем')
        stage.finished_at = None if stage.status == 'waiting_human' else utc_now()
        run.status = 'waiting' if stage.status == 'waiting_human' else 'running'
        _event(session, run_id, 'gate.result', {'stage': stage.stage, 'gate': gate, 'decision': decision})
    advance(run_id)


def answers_present(session, stage_id):
    return session.scalar(select(Question.id).where(Question.stage_run_id == stage_id, Question.answer.is_not(None)).limit(1)) is not None


def result_status(session, run_id, latest):
    if any(row.status == 'failed' for key, row in latest.items() if key != 'report'):
        return 'failed'
    ids = [row.id for row in latest.values()]
    checks = session.scalars(select(GateResult).where(GateResult.stage_run_id.in_(ids))).all()
    flags = session.scalar(select(SpecFlag.id).where(SpecFlag.run_id == run_id).limit(1))
    verification = session.scalar(select(Artifact).where(Artifact.stage_run_id.in_(ids), Artifact.name == 'verification').order_by(Artifact.created_at.desc()).limit(1))
    quality_partial = False
    if verification:
        from harness.fakes import workspace_path
        run = session.get(Run, run_id)
        data = json.loads(workspace_path(Path(run.workspace_path), verification.path).read_text())
        quality_partial = any(not value.get('passes') or not value.get('implemented') for value in data.get('ac_status', {}).values())
        quality_partial = quality_partial or any(m.get('status') != 'killed' for m in data.get('mutations', []))
    return 'partial' if flags or quality_partial or any(f.get('code') == 'GATE_MISSING' for g in checks for f in g.findings) else 'succeeded'


def input_hash(session, run, latest, key):
    ids = [row.id for row in latest.values() if row.status == 'succeeded']
    artifacts = session.scalars(select(Artifact).where(Artifact.stage_run_id.in_(ids))).all()
    files = []
    repo = Path(__file__).resolve().parents[2]
    for directory in ('agents', 'templates', 'contracts'):
        for path in sorted((repo / directory).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                files.append((str(path.relative_to(repo)), hashlib.sha256(path.read_bytes()).hexdigest()))
    payload = [run.requirements, key, sorted((a.name, a.hash) for a in artifacts), files]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
