import os
import re
import sys
from pathlib import Path

from celery import Celery

from app.config import settings

database_url = settings.database_url.render_as_string(hide_password=False)
celery_app = Celery("pipeline", broker=f"sqla+{database_url}", backend=f"db+{database_url}")
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    task_track_started=True,
)

_AGENT_ID = re.compile(r"^[a-z][a-z0-9_-]{0,40}$")
_PUBLIC = (
    "subtype", "result", "num_turns", "usage", "permission_denials",
    "assumptions", "events", "prompt_sha", "duration_ms",
)


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "harness" / "agent.py").is_file():
            return parent
    raise RuntimeError("harness not found")


def resolve_agent(agent: str) -> Path:
    if not _AGENT_ID.fullmatch(agent):
        raise LookupError(agent)
    path = repo_root() / "agents" / agent
    if not (path / "prompt.md").is_file() or not (path / "config.yaml").is_file():
        raise LookupError(agent)
    return path


def execute_agent(prompt: str, agent: str, project_id: str, *, client=None) -> dict:
    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from harness.agent import load_dotenv, run

    load_dotenv()
    folder = resolve_agent(agent)
    base = Path(os.environ.get("WORKSPACES_DIR") or (root / "workspaces")).resolve()
    workspace = (base / project_id).resolve()
    if base != workspace and base not in workspace.parents:
        raise LookupError(project_id)
    workspace.mkdir(parents=True, exist_ok=True)
    result = run(prompt, cwd=workspace, agent=folder, client=client, deadline_s=900)
    public = {key: result[key] for key in _PUBLIC}
    public["agent"] = agent
    return public


@celery_app.task(name="pipeline.run_agent", acks_late=True)
def run_agent(prompt: str, agent: str, project_id: str) -> dict:
    return execute_agent(prompt, agent, project_id)


@celery_app.task(name="pipeline.check_queue")
def check_queue():
    return {"status": "ok", "broker": "postgresql"}


if __name__ == "__main__":
    result = check_queue.delay()
    value = result.get(timeout=30)
    assert value == {"status": "ok", "broker": "postgresql"}, value
    print(f"Queue check passed: {result.id}: {value}")
    result.forget()
