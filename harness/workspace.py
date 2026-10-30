"""Per-run workspace operations used by the runner and the API."""
import hashlib
import os
import subprocess
from pathlib import Path
from uuid import UUID

from contracts.stage import ContractError
from harness.fakes import workspace_path


def create_workspace(base: Path, project_id: UUID, run_id: UUID, requirements: str) -> Path:
    root = base.resolve()
    path = workspace_path(root, f"{project_id}/runs/{run_id}")
    path.mkdir(parents=True, exist_ok=False)
    (path / 'input').mkdir()
    (path / 'input' / 'requirements.md').write_text(requirements, encoding='utf-8')
    _git(path, 'init', '-q')
    _git(path, 'config', 'user.name', 'Pipeline')
    _git(path, 'config', 'user.email', 'pipeline@localhost')
    commit(path, 'input: требования')
    return path


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True, timeout=60,
                            env={**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull})
    return result.stdout.strip()


def commit(path: Path, message: str) -> str:
    _git(path, 'add', '-A')
    _git(path, '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-qm', message[:300])
    return _git(path, 'rev-parse', 'HEAD')


def restore(path: Path, revision: str) -> None:
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ContractError('Некорректный идентификатор коммита')
    _git(path, 'reset', '--hard', revision)
    # git clean removes generated files after the restore; path is the isolated run workspace.
    _git(path, 'clean', '-fd')


def describe(path: Path, relative: str) -> tuple[str, int, str]:
    target = workspace_path(path, relative)
    if not target.exists():
        raise ContractError(f'Артефакт не существует: {relative}')
    digest = hashlib.sha256()
    size = 0
    if target.is_dir():
        for child in sorted(target.rglob('*')):
            workspace_path(path, str(child.relative_to(path.resolve())))
            if child.is_file():
                data = child.read_bytes()
                digest.update(str(child.relative_to(target)).encode() + b'\0' + hashlib.sha256(data).digest())
                size += len(data)
        kind = 'dir'
    else:
        data = target.read_bytes()
        size = len(data)
        digest.update(data)
        kind = {'.json': 'json', '.md': 'markdown'}.get(target.suffix, 'text')
    return digest.hexdigest(), size, kind
