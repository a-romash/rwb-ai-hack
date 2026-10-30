"""Preflight checks for the platform; nothing is modified except the queue probe."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from harness import llm_config


def _backend_imports():
    root = Path(__file__).resolve().parent.parent
    if (root / "backend" / "app").is_dir():
        sys.path.insert(0, str(root / "backend"))
    from app.database import engine
    from app.tasks import check_queue
    return engine, check_queue


def _database():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import text
    engine, _ = _backend_imports()
    root = Path(__file__).resolve().parent.parent
    ini = root / "backend" / "alembic.ini"
    if not ini.exists():
        ini = root / "alembic.ini"
    head = ScriptDirectory.from_config(Config(str(ini))).get_current_head()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        database_time = conn.execute(text("SELECT extract(epoch from now())")).scalar_one()
    if version != head:
        raise RuntimeError(f"Миграции: БД {version}, требуется {head}")
    if abs(float(database_time) - time.time()) > 60:
        raise RuntimeError("Время БД и приложения отличается более чем на 60 секунд")
    return f"БД доступна; миграции {version}; время синхронизировано"


def _broker():
    _, check_queue = _backend_imports()
    task = check_queue.delay()
    try:
        result = task.get(timeout=20)
        if result != {"status": "ok", "broker": "postgresql"}:
            raise RuntimeError("Воркер вернул неожиданный результат проверки очереди")
    finally:
        task.forget()
    return "Сообщение доставлено через PostgreSQL и обработано воркером"


def _model():
    from harness.agent import OpenRouter, load_dotenv
    load_dotenv()
    if not llm_config.api_key() and llm_config.key_required():
        raise RuntimeError("LLM_API_KEY не задан")
    client = OpenRouter(thinking=False, max_output_tokens=64, retries=1)
    result = client.complete([{"role": "user", "content": 'Return JSON: {"ok": true}'}], tools=None,
                             response_format={"type": "json_object"})
    if result.get("finish_reason") != "stop":
        raise RuntimeError("Модель вернула незавершённый ответ")
    response = json.loads(result["message"]["content"])
    if response.get("ok") is not True:
        raise RuntimeError("Модель вернула некорректный JSON")
    return "Модель ответила в JSON-режиме с отключёнными размышлениями"


def _docker(manifest: Path):
    if not manifest.is_file():
        raise RuntimeError(f"Манифест инструментов отсутствует: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Некорректный pack.json")
    images = {target.get("image") for target in data.get("targets", {}).values() if isinstance(target, dict) and target.get("image")}
    if isinstance(data.get("scan"), dict) and data["scan"].get("image"):
        images.add(data["scan"]["image"])
    if not images:
        raise RuntimeError("В pack.json нет образов инструментов")
    subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=15)
    for image in sorted(images):
        if subprocess.run(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15).returncode:
            raise RuntimeError(f"Нет образа {image}: соберите docker compose --profile tools build")
    return f"Docker доступен; найдены образы: {', '.join(sorted(images))}"


def _disk(workspaces: Path):
    path = workspaces.resolve()
    while not path.exists():
        path = path.parent
    free = shutil.disk_usage(path).free
    if free < 2 * 1024**3:
        raise RuntimeError(f"Меньше 2 ГБ свободного места: {free // 1024**2} МБ")
    return f"Свободно {free // 1024**2} МБ на {path}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка готовности платформы")
    parser.add_argument("--manifest", type=Path, default=Path("templates/product/pack.json"))
    parser.add_argument("--workspace", type=Path, default=Path(os.environ.get("WORKSPACES_DIR", "workspaces")))
    args = parser.parse_args(argv)
    checks = [("БД и миграции", _database), ("Очередь", _broker), ("Модель", _model),
              ("Docker и образы", lambda: _docker(args.manifest)), ("Диск", lambda: _disk(args.workspace))]
    success = True
    for name, check in checks:
        try:
            detail = check()
            print(f"[OK] {name}: {detail}")
        except Exception as exc:
            from harness.agent import _redact
            print(f"[ERROR] {name}: {_redact(str(exc), llm_config.api_key())}")
            success = False
    return 0 if success else 1
