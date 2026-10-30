"""Полная выдача S1–S7: python -m stages.spec.delivery; только документация."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Task:
    title: str
    files: tuple[str, ...]
    tests: tuple[str, ...]
    test_directory: str
    outcome: str
    limits: str


def fixture_paths(stage: str) -> tuple[str, ...]:
    return tuple(str(path.relative_to(ROOT)) for path in sorted((ROOT / f"stages/{stage}/tests/fixtures").glob("*.json")))


def tasks() -> dict[str, Task]:
    prompts = tuple(str(path.relative_to(ROOT)) for pattern in ("analyst-*/*", "system-analyst-*/*") for path in sorted((ROOT / "agents").glob(pattern)) if path.is_file())
    eval_files = tuple(str(path.relative_to(ROOT)) for pattern in ("EVAL*.md", "EVAL*.json", "eval/case1/*", "eval-history/DEV-EVAL.*", "TESTS.*") for path in sorted((ROOT / "stages/spec").glob(pattern)) if path.is_file())
    return {
        "S1": Task("Приём входов", ("stages/analysis/compat.py", "stages/analysis/storage.py", "stages/analysis/profiling.py", "stages/analysis/inputs.py", "stages/analysis/requirements.txt"), ("stages/analysis/tests/test_inputs.py",), "stages/analysis/tests", "Разобраны TXT/Markdown/PDF/DOCX; изображения и ошибки сохраняются явно. JSON/CSV/GeoJSON профилируются без LLM; источники имеют стабильные ID, данные — компактные карточки.", "Карточка ограничена 7000 UTF-8 байтами. Слишком широкая схема остаётся честно неразобранной. Паспорт входов хранится отдельно от общего analysis.json."),
        "S2": Task("Этап analysis", ("stages/analysis/__init__.py", "stages/analysis/runtime.py", "stages/analysis/models.py", "stages/analysis/symbols.py", "stages/analysis/patching.py", "stages/analysis/testing.py") + fixture_paths("analysis"), ("stages/analysis/tests/test_analysis_stage.py",), "stages/analysis/tests", "Реализованы извлечение, дедупликация, каркас домена, lint, A0/A1/A2, синтез и две ревизии. A0/A1 продолжает контрольную точку без повторного извлечения; A2 переводит defaults в ASM. Неизвестные роли ограничены внутренней схемой; однозначные подписи нормализуются в объявленные ID. Бюджет возвращает частичный результат.", "Стабильные ID нельзя менять при ремонте. Патч вне находки отклоняется без изменения артефакта. Нормализация Gherkin исправляет только двоеточия после ключевых слов шагов. Общие модули платформы не создаются; до их появления применяются локальные дублёры."),
        "S3": Task("Гейт G0", ("gates/g0_inputs.py",), ("gates/tests/test_gates.py",), "gates/tests", "Покрыты IN_UNPARSED, REQ_NO_QUOTE, SRC_UNCOVERED, CONTRACT_ANALYSIS. Проверяются точность цитаты, происхождение самого фрагмента, покрытие и неполностью разобранные файлы.", "Нет модели, сети или записи в workspace. Паспорт шума и статусов — отдельный вспомогательный артефакт. Общий файл тестов также содержит проверки G1."),
        "S4": Task("Этап spec", ("stages/spec/__init__.py", "stages/spec/context.py") + fixture_paths("spec"), ("stages/spec/tests/test_spec_stage.py",), "stages/spec/tests", "Семь шагов валидируют семнадцать разделов независимо. Параметры переносятся из BR/ASM кодом; модель пишет семантику. Контекст разбивается по требованиям и содержит компактные готовые разделы. Сохраняются partial, конфликты, поздние допущения и адресный ремонт.", "CRUD и события переходов не материализуются. Открытые разделы JSON не объявлены согласованными строгими моделями. Допущения spec сохраняются в spec-notes.json; механизм заморозки относится к платформе."),
        "S5": Task("Гейт G1", ("gates/g1_spec.py", "stages/spec/semantics.py", "stages/spec/requirements.txt"), ("gates/tests/test_gates.py",), "gates/tests", "Реализованы 18 чистых семантических валидаторов и отдельный CONTRACT_APP. Каждый код покрыт нарушающим примером. Gherkin разбирается официальным парсером; границы проверяются по таблицам Examples с приведением длительностей к секундам.", "Пересечения произвольных guard-функций проверяются консервативно с предупреждением. Соглашение об именах неявных событий требует окончательного контракта генератора. Проверка file/field/unit действует на явно заданные отображения данных."),
        "S6": Task("Промпты", prompts, ("stages/spec/tests/test_eval.py",), "stages/spec/tests", "Созданы 16 английских ролевых карточек с конфигурациями. Указаны версии, запрет доверять источникам, JSON-выход, русский язык человеческих текстов. Вызовы одноходовые; SHA-256 текста фиксируется в eval и проверяется регрессионным тестом.", "Карточки имеют свои версии в заголовках и config.yaml. Изменение текста требует нового recorded-eval. Настоящие результаты отделены от воспроизведения записанных ответов."),
        "S7": Task("Оценка качества", ("stages/spec/eval.py", "stages/spec/delivery.py", "stages/spec/README.md", "contracts/fixtures/equipment/requirements.md", "contracts/fixtures/equipment/analysis.json", "contracts/fixtures/equipment/app.json") + eval_files, ("stages/spec/tests/test_eval.py",), "stages/spec/tests", "Реализованы live/recorded eval, версии промптов, реальные токены и время, метрики цитат, ISS/Q, BR/AC, G0/G1 до/после ремонта и честные флаги зависимостей. Эталон equipment валиден. Текст кейса №1 извлечён из пяти проверенных слайдов; происхождение сохранено.", "Фактические статусы трёх настоящих прогонов приведены в EVAL.md/EVAL.json. partial означает нерешённые проблемы; failed/contract_error никогда не называются успехом. Ключи не сохраняются в артефактах. Общие контрактные пробелы и подключение платформы остаются запросами владельцам."),
    }


def tree(paths: tuple[str, ...]) -> str:
    nodes: dict = {}
    for path in paths:
        current = nodes
        for part in Path(path).parts:
            current = current.setdefault(part, {})
    lines: list[str] = []

    def walk(node: dict, prefix: str = "") -> None:
        entries = sorted(node.items())
        for index, (name, children) in enumerate(entries):
            last = index == len(entries) - 1
            lines.append(prefix + ("└── " if last else "├── ") + name + ("/" if children else ""))
            if children:
                walk(children, prefix + ("    " if last else "│   "))
    walk(nodes)
    return "\n".join(lines)


def block(relative: str) -> str:
    path = ROOT / relative
    language = {".py": "python", ".json": "json", ".yaml": "yaml", ".md": "markdown", ".txt": "text"}.get(path.suffix, "text")
    return f"### {path}\n\n````{language}\n{path.read_text(encoding='utf-8').rstrip()}\n````\n\n"


def main() -> None:
    destination = ROOT / "stages/spec/delivery"
    destination.mkdir(exist_ok=True)
    for key, task in tasks().items():
        contents = [f"# {key} — {task.title}\n\n## Дерево файлов\n\n```text\n{tree(task.files + task.tests)}\n```\n\n## Полные файлы\n\n"]
        contents += [block(path) for path in task.files]
        contents += ["## Тесты\n\n"] + [block(path) for path in task.tests]
        contents += [f"## Команды запуска\n\n```sh\ncd {ROOT}\n.venv/bin/python -m pip install -r stages/analysis/requirements.txt\n.venv/bin/python -m unittest discover -s {task.test_directory} -v\n```\n\n"]
        if key == "S7":
            contents += ["```sh\n.venv/bin/python -m stages.spec.eval --mode live\n.venv/bin/python -m stages.spec.eval --mode recorded --output stages/spec/EVAL-recorded.md\n```\n\n"]
        contents += [f"## Короткий отчёт\n\nСделано: {task.outcome}\n\nКак проверить: команды выше; результаты общих тестов — в TESTS.md, оценка настоящей модели — в EVAL.md.\n\nДопущения и ограничения: {task.limits}\n\nЗапрос владельцу: межкомандные вопросы перечислены в `stages/spec/README.md`. Чужие исходные файлы не изменены.\n"]
        (destination / f"{key}.md").write_text("".join(contents), encoding="utf-8")
    lines = ["# Полная выдача S1–S7", "", "Для каждой задачи: дерево, полные тексты файлов, полные тесты, команды и короткий отчёт.", ""]
    lines += [f"- [{key} — {task.title}]({key}.md)" for key, task in tasks().items()]
    lines += ["", "Установка, интеграция, зависимости и запросы владельцам: [README](../README.md).", "", "Фактические проверки: [TESTS](../TESTS.md), [настоящая модель](../EVAL.md), [записанные ответы](../EVAL-recorded.md).", "", "Отчёты не включают собственную копию; содержимое всех перечисленных исходных файлов приводится без сокращений."]
    (destination / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
