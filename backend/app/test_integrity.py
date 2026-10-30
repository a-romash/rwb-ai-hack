"""Accept the QA-owned file manifest, never infer the protected set by extension."""
import json
from sqlalchemy import delete
from app.models import TestHash, Event
from contracts.stage import ContractError
from harness.fakes import workspace_path
from harness.workspace import describe


def accept_manifest(session, run_id, root, relative):
    data = json.loads(workspace_path(root, relative).read_text(encoding='utf-8'))
    hashes = data.get('hashes')
    if data.get('schema_version') != 1 or not isinstance(hashes, dict) or not hashes:
        raise ContractError('reports/tests.json должен содержать schema_version=1 и непустой hashes: путь → SHA256')
    checked = []
    for path, digest in hashes.items():
        if not isinstance(path, str) or not path.startswith('product/') or not isinstance(digest, str):
            raise ContractError('Некорректный манифест тестов')
        target = workspace_path(root, path)
        if not target.is_file() or describe(root, path)[0] != digest:
            raise ContractError(f'Хэш теста не совпадает: {path}')
        checked.append((path, digest))
    session.execute(delete(TestHash).where(TestHash.run_id == run_id))
    for path, digest in checked:
        session.add(TestHash(run_id=run_id, path=path, hash=digest, reason='redproof'))


def approve_test_change(session, run_id, root, path, dispute_id, g2_result):
    """Trusted QA integration hook; call only after resolve(fix) and a fresh G2."""
    row = session.get(TestHash, (run_id, path))
    if row is None or not dispute_id or g2_result.gate != 'G2' or not g2_result.passed:
        raise ContractError('Изменение теста требует принятого спора и зелёного G2')
    if session.query(Event).filter_by(run_id=run_id, type='test.dispute').filter(Event.payload['path'].astext == path).first():
        raise ContractError('Для теста уже использован спор')
    row.hash = describe(root, path)[0]
    row.reason = f'dispute:{dispute_id}'
    session.add(Event(run_id=run_id, type='test.dispute', payload={'path': path, 'dispute': dispute_id, 'hash': row.hash}))
