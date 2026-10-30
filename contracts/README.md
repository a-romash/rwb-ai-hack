# Контракты M0: можно начинать этапы независимо

Это настоящие общие Pydantic-контракты и тестовые двойники платформы.
Дирижёр, HTTP API, настоящий LLM-шлюз и Docker-песочница придут следующими поставками.
Фейковые JSON-файлы проверяют связность и **не заменяют** модели артефактов Сани, Артёма, Ивана и Тимофея.

Из корня репозитория, Python 3.12 с зависимостями `backend/requirements.txt`:

```bash
python -m unittest discover -s tests -v
python -m harness.fake_stages
# Сохранить артефакты в новом/пустом каталоге:
python -m harness.fake_stages --workspace /tmp/rwb-fake-run
```

## Один этап

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from contracts.stage import StageInput
from harness.fakes import FakeLLM, FakeSandbox, run_stage_locally
from harness.fake_stages import analysis  # заменить своим stages.analysis

with TemporaryDirectory() as folder:
    result = run_stage_locally(
        analysis,
        StageInput(run_id="local-1", stage="analysis", attempt=1,
                   requirements="Текст требований", artifacts={}),
        Path(folder), FakeLLM({}), FakeSandbox({}),
    )
    print(result.model_dump_json(indent=2))
```

Каждый этап экспортирует:

```python
def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput:
    ...
```

Этап не импортирует FastAPI, Celery или модели БД. Собственные входные и выходные
JSON-файлы проверяет своей Pydantic-моделью. Все пути относительны workspace.
`run_stage_locally` проверяет существование входов и выходов, включая внешние
симлинки внутри папок. Это проверка контракта, а не изоляция недоверенного Python-кода.

## Ответ модели и результат инструмента

```python
from pydantic import BaseModel
from contracts.stage import SandboxResult
from harness.fakes import FakeLLM, FakeSandbox

class Extracted(BaseModel):
    summary: str

llm = FakeLLM({"req_extract": [{"summary": "Пример"}]}, budget_after=1)
answer = llm(task_class="req_extract", system="Извлеки требования",
             user="Текст", output=Extracted)
assert answer.summary == "Пример"
assert len(llm.calls) == 1

sandbox = FakeSandbox({("test", "backend"): [SandboxResult(
    ok=False, exit_code=1, duration_ms=10,
    failed=["AC-01"], output_tail="Ожидалось другое значение",
)]})
assert not sandbox.run("test", "backend", filter="AC-01").ok
```

- `FakeLLM` принимает ключ класса задачи или `(task_class, task_id)`; точный ключ приоритетнее.
- Ответы расходуются по порядку; отсутствующий ответ — явная ошибка теста.
- Для `output="code"` задаётся уже извлечённый код без маркеров; для `"text"` — строка.
- Объект исключения в сценарии будет выброшен. `budget_after=N` разрешает N вызовов.
- Списки ответов копируются, вызовы доступны в `.calls`.

## Реестр и API

`harness.registry.STAGES` содержит фиксированную цепочку и метаданные для Студии.
`tests/develop/scaffold/verify` используют очередь `build`, включая свои вызовы LLM;
`analysis/spec/ui/report` — `llm`. Реестр сам не запускает задачи.

Модели для Студии — `contracts.api`; валидные примеры — `contracts/examples/`.
Это контракт будущих маршрутов из задания, а не уже работающий HTTP API.
В метриках неизвестные токены — `null`; числовой ноль не означает неизвестный расход.
`MetricTotals` применяется в totals, by_stage (добавлено stage) и by_task_class (добавлено task_class).

### Продолжение после вопросов и целостность тестов

После `waiting_input` платформа повторно входит в `execute` с заполненным `inp.answers`
и артефактами той же попытки в `inp.artifacts`. Этап должен читать этот checkpoint,
а не заново извлекать требования. Повтор идентичного LLM-запроса обслуживается кэшем.
Гейты выполняются после получения ответов, а не над незавершённым анализом.

Контракт `reports/tests.json`: `{"schema_version":1,"hashes":{"product/path/to/test":"sha256"}}`.
Включать все защищаемые файлы, в том числе helpers и fixtures; платформа проверяет
каждый хэш до принятия. Интеграция QA после `resolve(fix)` и повторного G2 вызывает
`app.test_integrity.approve_test_change(session, run_id, workspace, path, dispute_id, g2_result)`
в доверенном коде; функция обновляет хэш и пишет событие спора. Это не инструмент модели.
