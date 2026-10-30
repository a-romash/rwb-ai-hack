"""Per-run workspace operations used by the runner and the API."""
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from contracts.stage import ContractError
from harness.fakes import workspace_path


def create_workspace(base: Path, project_id: UUID, run_id: UUID, requirements: str,
                     attachments: list[Path] = ()) -> Path:
    root = base.resolve()
    path = workspace_path(root, f"{project_id}/runs/{run_id}")
    path.mkdir(parents=True, exist_ok=False)
    (path / 'input').mkdir()
    (path / 'input' / 'requirements.md').write_text(requirements, encoding='utf-8')
    for file in attachments:
        (path / 'input' / file.name).write_bytes(file.read_bytes())
    (path / '.gitignore').write_text(IGNORED, encoding='utf-8')
    _git(path, 'init', '-q')
    _git(path, 'config', 'user.name', 'Pipeline')
    _git(path, 'config', 'user.email', 'pipeline@localhost')
    commit(path, 'input: требования')
    return path


def input_attachments(root: Path) -> list[str]:
    """Files the analyst attached to the run: everything in input/ besides the requirements text."""
    folder = Path(root) / 'input'
    return sorted(f'input/{p.name}' for p in folder.iterdir() if p.is_file() and p.name != 'requirements.md') if folder.is_dir() else []


# Build outputs and package caches of the generated product never belong to the run history.
IGNORED = """node_modules/
.nuget/
.npm/
bin/
obj/
dist/
.angular/
playwright-report/
test-results/
"""


def _git_config() -> str:
    """Isolated global config: API and build workers may run as different users on one workspace.

    safe.directory is honoured only in protected (system/global) config, so it cannot be passed
    through the repository; without it git refuses a repository owned by another user.
    """
    path = Path(tempfile.gettempdir()) / 'pipeline-gitconfig'
    if not path.is_file():
        path.write_text('[safe]\n\tdirectory = *\n', encoding='utf-8')
    return str(path)


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True, timeout=120,
                            env={**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': _git_config()})
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


def _tracked_files(folder: Path):
    """Files git would track: restored packages and build output (IGNORED) are not part of an artifact."""
    skip = {line.rstrip('/') for line in IGNORED.split()}
    for current, dirs, names in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip]
        yield from (Path(current) / name for name in names)


def describe(path: Path, relative: str) -> tuple[str, int, str]:
    target = workspace_path(path, relative)
    if not target.exists():
        raise ContractError(f'Артефакт не существует: {relative}')
    digest = hashlib.sha256()
    size = 0
    if target.is_dir():
        for child in sorted(_tracked_files(target)):
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
