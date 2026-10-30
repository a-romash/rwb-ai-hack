"""Publish one prototype into a prepared runtime, without building Docker images."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from contracts.stage import ContractError
from harness.sandbox import host_workspaces_dir


def enabled() -> bool:
    return os.environ.get('PROTOTYPE_ENABLED', '').lower() in ('1', 'true')


def directory() -> Path:
    return Path(os.environ.get('WORKSPACES_DIR', 'workspaces')).resolve() / '.prototype'


def public_path() -> str:
    path = os.environ.get('PROTOTYPE_PUBLIC_PATH', '/agent-prototype/')
    if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)+', path):
        raise ContractError('PROTOTYPE_PUBLIC_PATH должен быть локальным путём с завершающим /')
    return path


def _state() -> dict:
    try:
        state = json.loads((directory() / 'state.json').read_text())
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(run_id: str, status: str) -> None:
    root = directory()
    root.mkdir(parents=True, exist_ok=True)
    temporary = root / 'state.json.tmp'
    temporary.write_text(json.dumps({'run_id': run_id, 'status': status}))
    temporary.replace(root / 'state.json')


def claim(run_id: str) -> None:
    public_path()
    _save(run_id, 'pending')


def _assert_owner(run_id: str) -> None:
    if _state().get('run_id') != run_id:
        raise ContractError('Прототип принадлежит другому прогону')


def mark_ready(run_id: str) -> None:
    _assert_owner(run_id)
    _save(run_id, 'ready')


def url(run_id: str) -> str | None:
    if not enabled():
        return None
    state = _state()
    return public_path() if state.get('run_id') == run_id and state.get('status') == 'ready' else None


def _compose(*arguments: str) -> None:
    root = directory()
    compose = root / 'compose.yaml'
    if not compose.is_file():
        raise ContractError('Runtime прототипа не подготовлен: нет workspaces/.prototype/compose.yaml')
    if arguments[0] == 'up':
        templates = Path(__file__).resolve().parents[1] / 'infra' / 'prototype'
        for filename in ('nginx.conf', 'mobile.conf'):
            (root / filename).write_text((templates / filename).read_text().replace('/agent-prototype/', public_path()))
    environment = {key: os.environ[key] for key in ('PATH', 'HOME', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG') if key in os.environ}
    environment['PROTOTYPE_DIR'] = str(host_workspaces_dir(root.parent) / '.prototype')
    result = subprocess.run(['docker', 'compose', '-p', 'rwb-prototype', '-f', str(compose), *arguments],
                            cwd=root, env=environment, capture_output=True, text=True, timeout=180, check=False)
    if result.returncode:
        raise ContractError(f'Runtime прототипа: {(result.stderr or result.stdout)[-2000:]}')


def reset(run_id: str) -> None:
    _assert_owner(run_id)
    _save(run_id, 'pending')
    _compose('down', '-v', '--remove-orphans')
    shutil.rmtree(directory() / 'current', ignore_errors=True)


def stop(run_id: str) -> None:
    _assert_owner(run_id)
    _save(run_id, 'failed')
    _compose('down', '-v', '--remove-orphans')


def reset_data(run_id: str) -> None:
    """Discard E2E data and start the same published binaries with a fresh database."""
    _assert_owner(run_id)
    _save(run_id, 'starting')
    _compose('down', '-v', '--remove-orphans')
    _compose('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '120')


def deploy(product: Path, run_id: str) -> None:
    _assert_owner(run_id)
    # ponytail: one global prototype; use per-run runtimes if simultaneous demos are required.
    outputs = {'backend': ('.publish/backend', 'App.Api.dll'), 'worker': ('.publish/worker', 'App.Worker.dll'),
               'admin': ('admin-web/dist/admin-web/browser', 'index.html'),
               'mobile': ('mobile-web/dist/mobile-web/browser', 'index.html')}
    for folder, filename in outputs.values():
        if not (product / folder / filename).is_file():
            raise ContractError(f'Не собран артефакт прототипа: {folder}/{filename}')
    _save(run_id, 'starting')
    _compose('down', '-v', '--remove-orphans')
    current = directory() / 'current'
    shutil.rmtree(current, ignore_errors=True)
    for target, (folder, _) in outputs.items():
        shutil.copytree(product / folder, current / target)
    try:
        _compose('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '120')
    except Exception:
        _save(run_id, 'failed')
        raise
