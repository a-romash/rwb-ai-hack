# Задачи: Тимофей — тесты, проверка и отчёт (tests, verify, report, гейты G2–G5)

> **Коротко.** Ты делаешь так, чтобы «зелёное» значило «требование выполнено»: тесты из критериев приёмки до кода и без доступа к реализации, red-proof, мутации, сканеры, подъём стенда и E2E; затем честный отчёт, паспорт и документацию продукта. Первая задача (T0) — модели `verification.json` и `report.json`.
>
> Основа — `docs/architecture-v2.md`. Остальные четыре файла в `docs/tasks/` содержат тот же общий блок (разделы 1–4), поэтому контракты у всех одинаковые.

## Как пользоваться этим файлом

Файл самодостаточный. Его можно целиком вставить в чат с нейросетью (Claude, GPT и т. п.) вместе с репозиторием или нужными файлами из него. Блок «Промпт для нейросети» в конце — готовая инструкция.

Файл состоит из двух частей:
- **Общая часть** (разделы 1–4) одинакова во всех пяти файлах задач. В ней контекст кейса, архитектура и **общие контракты** — то, о чём команда договорилась, чтобы работать параллельно.
- **Твоя часть** (раздел 5 и дальше) — только твои задачи.

Источники, если нужно больше подробностей: `docs/architecture-v2.md` (архитектура, на которую опираются задачи), `docs/trassa/p1.md`–`p11.md` (подробный проект «Трасса»: исследования, обоснования, примеры), `docs/architecture-overview.md` (упрощённый MVP-план; расхождения с ним — в `architecture-v2.md`, §16).

---

## 1. Контекст: что мы строим

**Хакатон Russtech / RWB, кейс «Агентский ИИ-пайплайн полного цикла разработки корпоративных приложений».** Нужен не одно приложение, а **универсальный конвейер**: на входе только бизнес-требования (текст, PDF, приложенные данные), на выходе — системный анализ, дизайн интерфейса, код, тесты, инфраструктура, документация, развёрнутый прототип и отчёт о расходе токенов, времени и попыток.

- **Кейс №1** «Парковочный помощник для технических служб» выдан заранее — для подготовки.
- **Кейс №2 скрыт.** Жюри запустит конвейер на нём в момент оценки. Поэтому главное свойство решения — надёжный автономный прогон на незнакомом требовании. **В коде конвейера нельзя зашивать ни парковки, ни любой другой домен.**
- **Модель:** Qwen3.8-27B (через OpenRouter или локальный vLLM). Сильна в задачах уровня одной функции, слаба в длинных агентных сессиях, по умолчанию долго «думает», окно контекста у организаторов считаем малым (8–32 тыс. токенов). Отсюда принцип: **нет длинной агентной сессии — есть детерминированный конвейер из множества коротких проверяемых задач.**
- **Стек генерируемого приложения задан ТЗ и не меняется:** Angular 20.1.6 (UI Kit — Angular Material), C# 14 / ASP.NET Core 10, PostgreSQL 17.9 + PostGIS, Kotlin 2.2.21 (Android, Compose M3), Kafka + REST, Docker / Docker Compose, GitLab CI/CD.
- **Стек самой платформы** (уже в `main`): Angular 20.1.6 + Taiga UI 5 (Студия), FastAPI, SQLAlchemy + Alembic, Celery, PostgreSQL 17.9 — он же брокер Celery через Kombu SQLAlchemy transport. Redis, RabbitMQ и Langfuse не используем.
- **Семь этапов по постановке RWB:** 1) приём и анализ требований; 2) системный анализ; 3) проектирование интерфейса; 4) разработка; 5) тестирование и безопасность; 6) сборка и развёртывание; 7) документация.
- **Критерии (100 баллов):** анализ — 20, продукт и интерфейс — 15, архитектура и разработка — 20, тестирование и безопасность — 15, инфраструктура — 10, документация — 10, эффективность пайплайна (токены, время, попытки, автономность) — 10.
- **Что сдаём:** работающий пайплайн; репозиторий в GitLab; документы; исходный код; тесты и проверки; Docker-окружение; CI/CD; работающий прототип; пользовательская документация; отчёт о токенах, времени и попытках; видео.

## 2. Архитектура в одном экране

**Главные принципы:**
1. **Модель пишет минимум, остальное выводит код.** CRUD, миграции, эндпоинты, права, клиенты API, CI, Compose, большая часть документации генерируются детерминированно из спецификации. Модель пишет смысл: требования, правила, тексты, тела бизнес-хуков, тесты.
2. **Спецификация — единственный источник истины.** `analysis.json` → `app.json` → `ui.json`. Всё дальше выводится из них. После гейта G1 спецификация замораживается.
3. **Данные от модели — JSON по схеме (Pydantic), код от модели — текстом** между строками `<<<CODE` и `CODE>>>`.
4. **Каждый вызов модели одноходовый**, со свежим узким контекстом не больше профиля окна. Истории диалога нет.
5. **Независимая проверка.** Тесты пишутся из критериев приёмки (AC) другим агентом, без доступа к реализации. Разработчик тесты не меняет.
6. **Гейты — код, а не агент.** После этапа дирижёр прогоняет гейт; находки с адресом в спецификации превращаются в задачи на точечное исправление (JSON Patch).
7. **Понижение вместо остановки.** Если элемент не удалось исправить за два круга, он и всё, что от него зависит, помечаются «под вопросом», остальное идёт дальше. Прогон останавливает только сломанный контракт (артефакт не создан или не проходит схему).
8. **Честный результат.** Нет реализации — «не реализовано». Нет проверки — «не проверено». Пропущенный тест — не успех.

**Цепочка этапов** (ключ → владелец → гейт после этапа):

```text
analysis (Саня, G0) → spec (Саня, G1 + заморозка) → ui (Артём, G1.5) → scaffold (Иван)
  → tests (Тимофей, G2 red-proof) → develop (Иван) → verify (Тимофей, G3 + G4) → report (Тимофей, G5)
```

`report` выполняется всегда, даже если прогон упал раньше. Платформу — дирижёр, очередь, шлюз модели, песочницу, API, гейты как механизм — делает Максим. Студию делает Артём.

**Режимы автономности:** A0 — человек утверждает каждый гейт; A1 — человек отвечает на вопросы анализа и подтверждает заморозку спецификации; **A2 — полный автомат, режим жюри** (вопросы закрываются ответами по умолчанию → допущения ASM).

**Гейты:**

| Гейт | Когда | Что проверяет | Чья логика |
|---|---|---|---|
| G0 | после `analysis` | входы разобраны; у каждого REQ точная цитата из источника | Саня |
| G1 | после `spec` | схема + 18 семантических валидаторов спецификации | Саня |
| G1.5 | после `ui` | проходы US по экранам, testid, обязательные состояния | Артём |
| G2 | после `tests` | тесты AC падают на заглушках (red-proof) | Тимофей |
| G3 | в `verify` | сборка, тесты, хэши тестов, мутации, сканеры | Тимофей |
| G4 | в `verify` | стенд поднят, health, smoke, E2E | Тимофей |
| G5 | после `report` | документация покрывает AC и роли; приёмка | Тимофей |

Механизм гейтов (реестр, запуск, хранение, круги исправлений, флаги «под вопросом») — у Максима.

## 3. Общие контракты

**Правило:** контракт меняется только через PR, который одобрили владелец и все потребители. Пока владелец не выложил свою модель и фикстуру, потребитель работает по описанию из этого раздела.

### 3.1 Раскладка репозитория и владельцы

```text
contracts/                     Python-пакет: Pydantic-модели всех артефактов и интерфейсов
  stage.py                     Максим   — StageInput, StageOutput, LLM, Sandbox, исключения
  gates.py                     Максим   — Finding, GateResult, ElementFlag
  api.py                       Максим   — модели API Студии
  analysis.py, app.py          Саня     — analysis.json, app.json (+ dependents())
  ui.py                        Артём    — ui.json, каталог паттернов и виджетов
  hooks.py, pack.py            Иван     — спецификация хука (hooks.json), манифест шаблона (pack.yaml)
  verification.py, report.py   Тимофей  — verification.json, report.json, споры по тестам
  fixtures/tickets/            эталонный домен «заявки на ремонт с SLA»: по одному валидному файлу на артефакт
  fixtures/equipment/          второй домен «выдача оборудования» (фаза 3)
stages/<key>/__init__.py       def execute(...); опционально def repair(...)
  analysis/, spec/             Саня
  ui/                          Артём
  scaffold/, develop/          Иван
  tests/, verify/, report/     Тимофей
gates/
  core.py                      Максим   — реестр и запуск
  g0_inputs.py, g1_spec.py     Саня
  g15_ui.py                    Артём
  g2_redproof.py, g3_checks.py, g4_stand.py, g5_docs.py   Тимофей
harness/                       Максим (runner.py, llm.py, sandbox.py, fakes.py, registry.py, doctor.py)
  agent.py                     Иван     — цикл с инструментами, только для мест custom
agents/<id>/                   промпты агентов: prompt.md (англ.), config.yaml; владелец — владелец этапа
templates/product/             Иван     — золотой шаблон генерируемого приложения + pack.yaml
backend/app/                   Максим   — API платформы, модели БД, миграции, Celery-задачи
frontend/                      Артём    — Студия
```

Каждый работает в своей ветке `feat/<имя>-<тема>` от `main` и вливает через PR. В чужие папки не пишем; правка чужого — через issue или PR с одобрением владельца.

### 3.2 Граница этапа

```python
# contracts/stage.py
from pathlib import Path
from typing import Literal, Protocol
from pydantic import BaseModel

Autonomy = Literal["A0", "A1", "A2"]

class Question(BaseModel):
    id: str                     # "Q-01"
    text: str
    options: list[str]
    default: str
    why: str
    blocking: bool = False

class ElementFlag(BaseModel):   # элемент спецификации «под вопросом»
    path: str                   # "hooks.SlaDeadline"
    status: Literal["questioned", "blocked_by"]
    reason: str
    gate: str | None = None

class StageInput(BaseModel):
    run_id: str
    stage: str                  # ключ этапа
    attempt: int
    autonomy: Autonomy = "A2"
    requirements: str           # исходный текст требований
    attachments: list[str] = [] # пути приложенных файлов внутри workspace/input/
    artifacts: dict[str, str]   # логическое имя → путь (относительно workspace) принятых артефактов
    answers: dict[str, str] = {}   # ответы человека на вопросы (A0/A1), id → ответ
    snapshot: dict | None = None   # только для report: статусы, гейты, метрики прогона

class StageOutput(BaseModel):
    artifacts: dict[str, str]   # имя → путь созданного файла или папки
    summary: str                # 1–3 предложения для Студии
    flags: list[ElementFlag] = []
    questions: list[Question] = []   # только analysis в A0/A1; непустой список → waiting_input

class ContractError(Exception): ...    # вход или выход не по контракту → прогон останавливается
class StageFailed(Exception): ...      # инфраструктура не дала выполнить этап → этап failed, можно повторить
class BudgetExceeded(Exception): ...   # бросает llm; этап ловит и возвращает частичный результат

class LLM(Protocol):
    def __call__(self, *, task_class: str, system: str, user: str,
                 output: type[BaseModel] | Literal["code", "text"],
                 task_id: str | None = None) -> BaseModel | str: ...

class SandboxResult(BaseModel):
    ok: bool
    exit_code: int
    duration_ms: int
    failed: list[str]           # "file:line: сообщение" или имена упавших тестов
    output_tail: str            # последние 4000 символов вывода
    reports: dict[str, str] = {}   # "junit" | "sarif" | "coverage" → путь в workspace

class Sandbox(Protocol):
    def run(self, kind: Literal["build", "test", "lint", "scan", "up", "smoke", "e2e", "down"],
            target: Literal["backend", "admin", "mobile", "stack"], *,
            filter: str | None = None, timeout_s: int = 600) -> SandboxResult: ...
```

```python
# stages/<key>/__init__.py
def execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput: ...
def repair(inp: StageInput, workspace: Path, llm: LLM, findings: list[Finding]) -> StageOutput: ...  # опционально
```

Правила:
- Этап не знает про HTTP, Celery и таблицы платформы. Всё, что ему нужно, приходит аргументами.
- Этап пишет только внутри `workspace` и не перезаписывает чужие файлы. В `product/` после `scaffold` добавлять и менять файлы можно только в местах своего этапа: `tests` — тестовые проекты AC (`backend/tests/App.Acceptance.Tests`, `admin-web/e2e/*.spec.ts`); `develop` — `write_roots` из `pack.yaml`; `verify` — временно для мутаций, с обязательным восстановлением.
- Этап проверяет вход и выход своими Pydantic-моделями. Нарушение — `ContractError`.
- Частичный бизнес-результат (хук не написан, AC красный) — это **успешное** завершение этапа со статусами внутри артефакта, а не исключение.
- `repair` вызывает дирижёр, если гейт после этапа нашёл ошибки: не больше двух раз. Этап исправляет только элементы по путям из `findings` (JSON Patch), остальное не трогает.
- Каждый этап обязан проверяться без платформы: с `FakeLLM` (заранее записанные ответы) и `FakeSandbox` из `harness/fakes.py`.

**Классы задач для `llm`** (`task_class`) и их режимы (размышления, лимиты, температуру ставит шлюз — этап их не выбирает):

| `task_class` | Для чего | Форма ответа |
|---|---|---|
| `req_extract` | Извлечение требований из куска источника | JSON |
| `req_lint` | Поиск неоднозначностей и вопросов | JSON |
| `spec_step` | Шаги системного анализа | JSON |
| `ui` | Доработка интерфейса и тексты | JSON |
| `patch` | Починка по находкам гейта (JSON Patch) | JSON |
| `hook_1`, `hook_2`, `hook_3`, `hook_4` | Попытки написать тело хука | код |
| `qa` | Тесты по AC, решение споров | код / JSON |
| `ci_classify` | Классификация ошибок сборки | JSON |
| `writer` | Связный текст документации | text (Markdown) |

### 3.3 Гейты

```python
# contracts/gates.py
class Finding(BaseModel):
    path: str          # адрес в артефакте: "state_machines.TicketFlow.transitions[2]"
    code: str          # "SM_UNREACHABLE"
    severity: Literal["error", "warning"]
    message: str       # по-русски, одно предложение

class GateResult(BaseModel):
    gate: str          # "G0" | "G1" | "G1.5" | "G2" | "G3" | "G4" | "G5"
    passed: bool       # True, если нет находок с severity == "error"
    decided_by: Literal["code", "human"] = "code"
    findings: list[Finding] = []

# gates/<file>.py
def check(workspace: Path, artifacts: dict[str, str]) -> GateResult: ...
```

Гейт — чистая проверка артефактов: без модели, без сети, без побочных эффектов. Ошибки блокируют гейт и идут в `repair`; предупреждения уходят в паспорт.

### 3.4 Артефакты прогона

Рабочая папка прогона: `WORKSPACES_DIR/<project_id>/runs/<run_id>/` — git-репозиторий; коммит после каждого принятого этапа.

| Имя | Путь | Кто пишет | Кто читает |
|---|---|---|---|
| — | `input/requirements.md`, `input/<файлы>` | платформа | analysis |
| `analysis` | `spec/analysis.json` | analysis | spec, ui, tests, report |
| `app` | `spec/app.json` | spec | ui, scaffold, tests, develop, report |
| `ui` | `spec/ui.json` | ui | scaffold, tests (E2E), report |
| `product` | `product/` (папка) | scaffold, develop | tests, verify |
| `hooks` | `product/hooks.json` | scaffold | tests, develop |
| `openapi` | `product/openapi.json` | scaffold | tests, report |
| `tests` | тестовые проекты внутри `product/` + `reports/tests.json` | tests | develop, verify |
| `develop` | `reports/develop.json` | develop | verify, report |
| `verification` | `reports/verification.json` | verify | report |
| `report` | `reports/report.json`, `reports/report.md`, `product/docs/` | report | Студия |

Все JSON-артефакты содержат `"schema_version": 1`. Идентификаторы стабильные: `S-001`, `REQ-01`, `ISS-01`, `Q-01`, `ASM-01`, `US-01`, `BR-01`, `AC-01`, `NFR-01`.

### 3.5 `analysis.json` (владелец — Саня)

```json
{
  "schema_version": 1,
  "sources":      [{"id": "S-001", "file": "requirements.md", "text": "…"}],
  "requirements": [{"id": "REQ-01", "text": "Система должна …", "type": "function",
                    "source": ["S-001"], "quote": "точная подстрока источника"}],
  "roles":        [{"id": "dispatcher", "name": "Диспетчер", "description": "…"}],
  "glossary":     [{"term": "SLA", "definition": "…"}],
  "issues":       [{"id": "ISS-01", "req": "REQ-03", "characteristic": "однозначность",
                    "problem": "…", "action": "Q-01"}],
  "questions":    [{"id": "Q-01", "text": "…", "options": ["…", "…"], "default": "…",
                    "why": "…", "blocking": false, "answer": "…", "answered_by": "default"}],
  "assumptions":  [{"id": "ASM-01", "text": "…", "source": "Q-01", "params": {"SLA_HIGH": "PT4H"}}],
  "user_stories": [{"id": "US-01", "role": "engineer", "want": "…", "so_that": "…", "req": ["REQ-01"]}],
  "rules":        [{"id": "BR-01", "text": "…", "req": ["REQ-02"],
                    "params": {"SLA_HIGH": {"type": "duration", "value": "PT4H"}}}],
  "acceptance":   [{"id": "AC-01", "rules": ["BR-01"], "stories": ["US-01"], "ui": true,
                    "gherkin": "# language: ru\nФункция: …\n  Сценарий: …\n    Дано …\n    Когда …\n    Тогда …"}],
  "nfr":          [{"id": "NFR-01", "text": "…", "metric": "p95 ≤ 2 с", "verify": "…"}],
  "out_of_scope": [{"req": "REQ-09", "reason": "…"}],
  "data_cards":   [{"file": "zones.json", "records": 6867, "schema": {}, "anomalies": [], "samples": []}],
  "profile":      {"modules": ["core", "workflow", "scheduler", "notify"], "platforms": ["web", "mobile"]}
}
```

Типы требований: `function`, `rule`, `data`, `interface`, `integration`, `constraint`, `nfr`, `goal`. Характеристики ISS: `единичность`, `непротиворечивость`, `актуальность`, `выполнимость`, `проверяемость`, `однозначность`, `полнота`, `данные`.

### 3.6 `app.json` (владелец — Саня)

```json
{
  "schema_version": 1,
  "meta":   {"name": "tickets", "title": "Заявки на ремонт", "lang": "ru-RU",
             "timezone": "Europe/Moscow", "modules": ["core", "workflow", "scheduler", "notify"]},
  "params": {"SLA_HIGH": {"type": "duration", "value": "PT4H", "traces": ["BR-02"]}},
  "types":  {"Priority": {"kind": "enum", "values": ["low", "normal", "high"],
                          "labels": {"low": "Низкий", "normal": "Обычный", "high": "Высокий"}}},
  "entities": {
    "Ticket": {
      "label": "Заявка",
      "fields": {
        "title":    {"type": "string", "required": true, "label": "Тема", "max": 200},
        "priority": {"type": "enum", "ref": "Priority", "required": true, "label": "Приоритет"},
        "assignee": {"type": "ref", "ref": "Employee", "nullable": true, "label": "Исполнитель"},
        "due_at":   {"type": "datetime", "computed_by": "SlaDeadline", "label": "Срок"},
        "status":   {"type": "state", "machine": "TicketFlow", "label": "Статус"}
      },
      "owner": "author", "traces": ["US-01"]
    }
  },
  "roles": {"engineer": {"name": "Инженер", "demo_users": ["eng1"]},
            "dispatcher": {"name": "Диспетчер", "demo_users": ["disp1"]}},
  "permissions": [{"role": "engineer", "op": "Ticket.read", "scope": "own"},
                  {"role": "dispatcher", "op": "Ticket.read", "scope": "all"},
                  {"role": "engineer", "op": "TakeTicket", "scope": "all"}],
  "state_machines": {
    "TicketFlow": {"entity": "Ticket", "initial": "new", "final": ["resolved"],
      "states": ["new", "in_progress", "overdue", "resolved"],
      "transitions": [
        {"name": "take",    "from": ["new"], "to": "in_progress",
         "trigger": {"command": "TakeTicket"}, "roles": ["engineer"], "traces": ["US-02"]},
        {"name": "expire",  "from": ["in_progress"], "to": "overdue",
         "trigger": {"timer": "due_at"}, "traces": ["BR-02"]},
        {"name": "resolve", "from": ["in_progress", "overdue"], "to": "resolved",
         "trigger": {"command": "ResolveTicket"}, "guard": "ResolutionRequired",
         "roles": ["engineer"], "traces": ["BR-03"]}]}
  },
  "hooks": {
    "SlaDeadline":        {"kind": "calculator", "in": ["Ticket"], "out": "datetime",
                           "params": ["SLA_HIGH"], "rule": "BR-02", "traces": ["AC-04", "AC-05"]},
    "ResolutionRequired": {"kind": "validator", "in": ["ResolveTicket"], "rule": "BR-03", "traces": ["AC-07"]}
  },
  "commands": {"TakeTicket":    {"entity": "Ticket", "roles": ["engineer"], "input": {},
                                 "effects": ["transition:TicketFlow.take"], "traces": ["US-02"]},
               "ResolveTicket": {"entity": "Ticket", "roles": ["engineer"],
                                 "input": {"resolution": {"type": "text", "required": true}},
                                 "effects": ["transition:TicketFlow.resolve"], "traces": ["US-03"]}},
  "queries":  {"OpenTickets": {"entity": "Ticket", "filter": "status in [new, in_progress, overdue]",
                               "roles": ["engineer", "dispatcher"], "order": "-due_at"}},
  "events":        {},
  "integrations":  {},
  "schedules":     {},
  "notifications": {"TicketOverdue": {"on": "TicketExpired", "to": "dispatcher",
                                      "channels": ["web"], "text": "Заявка «{title}» просрочена"}},
  "seed":      {"Ticket": [{"title": "Не работает кондиционер", "priority": "high"}]},
  "scenarios": [],
  "custom":    []
}
```

Закрытые словари (всё прочее отвергает схема):
- **типы полей:** `string`, `text`, `int`, `decimal`, `money`, `bool`, `date`, `datetime`, `duration`, `interval`, `enum`, `ref`, `state`, `geo_point`, `geo_line`, `geo_polygon`, `file`, `json`;
- **триггеры переходов:** `command`, `event`, `schedule`, `timer` (истекло время по полю), `geo` (вход/выход из области);
- **виды хуков:** `validator` (можно ли так?), `calculator` (сколько?), `decider` (что произошло / куда?), `policy` (положено ли?), `reaction` (что сделать в ответ на событие?). Хук — чистая функция без БД, сети и времени; если нужны другие записи, в хуке указывается `"select": "<имя query>"`, генератор выполняет запрос и передаёт результат хуку как вход;
- **области прав:** `own`, `team`, `all`;
- **каналы уведомлений:** `web`, `mobile`, `email`, `sms` (`email`/`sms` — через порт интеграции с mock);
- **операции:** `<Entity>.create|read|update|delete` или имя команды.

Неявное генератор выводит сам, в `app.json` это не пишется: CRUD, события на переходах (`TicketTaken`, `TicketExpired`, …), топики Kafka, тесты прав и переходов.

`contracts/app.py` дополнительно экспортирует `dependents(app, path) -> list[str]` — все пути, которые ссылаются на элемент (для пометки «под вопросом» зависимых).

### 3.7 `ui.json` (владелец — Артём)

```json
{
  "schema_version": 1,
  "screens": {
    "TicketList": {
      "platform": "web", "roles": ["engineer", "dispatcher"], "pattern": "list", "title": "Заявки",
      "source": {"query": "OpenTickets"},
      "widgets": [{"kind": "field",  "field": "Ticket.title",    "testid": "ticket-list.title"},
                  {"kind": "status", "field": "Ticket.status",   "testid": "ticket-list.status"},
                  {"kind": "countdown", "field": "Ticket.due_at", "testid": "ticket-list.due"}],
      "actions": [{"command": "TakeTicket", "testid": "ticket-list.take", "confirm": true}],
      "live": ["TicketTaken", "TicketExpired"],
      "states": {"empty": "Нет открытых заявок"},
      "nav": ["TicketDetail"]
    }
  },
  "menus": {"engineer": {"web": ["TicketList"]}, "dispatcher": {"web": ["TicketList", "Dashboard"]}},
  "home":  {"engineer": {"web": "TicketList"}, "dispatcher": {"web": "Dashboard"}},
  "walks": {
    "US-02": {"role": "engineer", "platform": "web",
              "steps": [{"open": "TicketList"},
                        {"tap": "TakeTicket", "row": {"seed": "Ticket[0]"}},
                        {"expect": {"screen": "TicketDetail", "status": "in_progress"}}],
              "covers": ["AC-02"]}
  },
  "copy":   {"ticket.take.confirm": "Взять заявку в работу?"},
  "device": {"mobile": []}
}
```

Закрытые словари:
- **паттерны экранов:** `list`, `detail`, `form`, `wizard`, `dashboard`, `map`, `feed`, `action`, `settings`, `calendar`, `kanban`;
- **виджеты:** `field`, `status`, `countdown`, `kpi`, `timeline`, `map_layer`, `action_button`, `scan`, `file`;
- **шаги проходов:** `open`, `fill`, `tap`, `scan`, `expect`;
- **возможности устройства:** `location`, `local_notification`, `external_link`, `scan_code`, `file_pick`;
- **состояния экрана:** `loading`, `empty`, `error`, `forbidden` (+ `offline` для mobile) — обязательны; модель задаёт только тексты.

`data-testid` имеет вид `<screen-kebab>.<element>` и уникален в пределах приложения.

### 3.8 Спецификация хука `hooks.json` (владелец — Иван)

```json
[{
  "id": "SlaDeadline",
  "file": "backend/src/App.Domain/Hooks/SlaDeadlineHook.cs",
  "language": "csharp",
  "kind": "calculator",
  "signature": "public DateTimeOffset Evaluate(Ticket ticket, SlaParams p, IWorkCalendar calendar)",
  "refs": ["BR-02", "AC-04", "AC-05"],
  "contract": {"summary": "Срок решения заявки по приоритету и рабочему календарю",
               "pre": ["ticket.CreatedAt задан"], "post": ["срок не раньше CreatedAt"]},
  "examples": [{"input": {"priority": "high", "created_at": "2026-11-06T17:00:00+03:00"},
                "expected": "2026-11-09T12:00:00+03:00", "ac": "AC-05"}],
  "allowed_api": ["Ticket", "Priority", "SlaParams", "IWorkCalendar.IsWorkingTime"],
  "max_lines": 60,
  "stub": "neutral"
}]
```

Заглушки хуков **нейтральные**: возвращают «пусто», «ноль», «разрешено», не бросают исключений.

### 3.9 Манифест шаблона `templates/product/pack.yaml` (владелец — Иван, потребитель — Максим)

```yaml
targets:
  backend:
    image: rwb/tool-dotnet:10
    build: ["dotnet", "build", "backend/App.sln", "--nologo"]
    test:  ["dotnet", "test", "backend/App.sln", "--nologo", "--logger", "junit;LogFilePath=/work/reports/junit/backend/{assembly}.xml"]
    filter: ["--filter", "AC={filter}"]
    reports: {junit: "reports/junit/backend/*.xml"}
  admin:
    image: rwb/tool-node:22-ng20.1.6
    workdir: admin-web
    build: ["npm", "run", "build"]
    test:  ["npx", "jest", "--ci"]
    e2e:   ["npx", "playwright", "test"]
    filter: ["--grep", "@{filter}"]
  mobile:
    image: rwb/tool-android:kt2.2.21
    build: ["./gradlew", "--offline", "-p", "mobile", "assembleDebug"]
    test:  ["./gradlew", "--offline", "-p", "mobile", "testDebugUnitTest"]
  stack:
    up:    ["docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d", "--wait"]
    smoke: ["python3", "infra/smoke.py"]
    down:  ["docker", "compose", "-f", "infra/docker-compose.yml", "down", "-v"]
scan:
  image: rwb/tool-security:1
  commands: [["gitleaks", "detect", "--source", "."], ["trivy", "fs", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "."]]
write_roots: [backend/src/App.Domain/Hooks, backend/src/App.Api/Custom, admin-web/src/app/custom,
              mobile/app/src/main/java/app/hooks, db/seed]
readonly: [backend/tests, admin-web/e2e, spec]
```

### 3.10 Тестовый набор шаблона (владелец — Иван, потребитель — Тимофей)

Генерируется в каждом продукте, для тестировщика — только чтение:

```csharp
// backend/tests/App.TestKit/
public sealed class AppFactory : WebApplicationFactory<Program>  // БД с миграциями и сидом, тестовые часы, перехват событий
public sealed class TestClock : TimeProvider { void Set(DateTimeOffset t); void Advance(TimeSpan d); }
public sealed class Api { Api As(string role); /* типизированный клиент из OpenAPI: TakeTicketAsync(id), GetOpenTicketsAsync() … */ }
public sealed class PublishedEvents { IReadOnlyList<CloudEvent> All { get; } Task<CloudEvent> WaitFor(string type, TimeSpan timeout); }
public static class Seed { Task Load(AppFactory app, string name = "default"); }
// App.Domain.Params — сгенерированные значения из app.json params (SlaParams.SlaHigh …)
// App.Domain.Hooks — интерфейсы I<Name>Hook и классы <Name>Hook (файл модели)
```

- Тесты AC — проект `backend/tests/App.Acceptance.Tests`, каждый тест помечен `[Trait("AC", "AC-07")]`.
- Сгенерированные тесты прав и переходов — `backend/tests/App.Generated.Tests` (пишет генератор).
- E2E — `admin-web/e2e/*.spec.ts`, заголовок теста начинается с `@AC-07`; page objects `admin-web/e2e/pages/*` генерируются из `data-testid` в `ui.json`.

### 3.11 API Студии (владелец — Максим, потребитель — Артём)

Все пути с префиксом `/api`. Существующие эндпоинты проектов (`/api/projects…`) остаются.

| Метод и путь | Тело / ответ |
|---|---|
| `POST /projects/{project_id}/runs` | `{autonomy: "A2", budget: {tokens: 1500000, minutes: 60}}` → `201 RunRead` |
| `GET /projects/{project_id}/runs` | → `RunSummary[]` |
| `GET /runs/{run_id}` | → `RunRead` |
| `GET /runs/{run_id}/artifacts` | → `[{name, path, stage, hash, size, kind: "json"\|"markdown"\|"dir"\|"text"}]` |
| `GET /runs/{run_id}/files?path=spec/app.json` | содержимое файла из workspace; для папки — список файлов |
| `POST /runs/{run_id}/stages/{key}/retry` | → `202` (только для `failed`, прогон не активен) |
| `POST /runs/{run_id}/answers` | `{answers: {"Q-01": "…"}}` → `202` |
| `POST /runs/{run_id}/gates/{gate}/decision` | `{decision: "approve"\|"reject", comment}` → `202` (A0/A1) |
| `POST /runs/{run_id}/cancel` | → `202` |
| `GET /runs/{run_id}/events?after={id}` | → `EventRead[]` (опрос) |
| `GET /runs/{run_id}/events/stream` | SSE с `Last-Event-ID` |
| `GET /runs/{run_id}/metrics` | → `{totals, by_stage[], by_task_class[]}` |

```text
RunRead = {id, project_id, status, autonomy, spec_version, created_at, finished_at,
           budget: {tokens_used, tokens_limit, minutes_used, minutes_limit},
           stages: StageRunRead[], flags: ElementFlag[], questions: Question[]}
StageRunRead = {key, title, rwb_stage: "Э1"…"Э7", participants: string[], status, attempt,
                started_at, finished_at, error, summary, gate: GateResult | null}
EventRead = {id, type, ts, payload}
```

- Статусы прогона: `pending`, `running`, `waiting`, `succeeded`, `partial`, `failed`, `cancelled`.
- Статусы этапа: `pending`, `queued`, `running`, `succeeded`, `failed`, `waiting_input`, `waiting_human`, `skipped`, `stale`.
- Типы событий: `run.created`, `stage.queued`, `stage.started`, `stage.finished`, `gate.result`, `llm.call`, `question.asked`, `flag.added`, `run.finished`.
- `participants` — участки Студии из `main` (`backend/app/projects.py`): `analysis` → `business_analysis`; `spec` → `system_analysis`, `database`; `ui` → `interfaces`; `scaffold` → `frontend`, `backend`, `database`, `cicd`; `tests` → `testing`; `develop` → `backend`, `frontend`; `verify` → `testing`, `security`, `cicd`; `report` → `documentation`.

### 3.12 Эталонный домен для фикстур и примеров

Все пишут примеры, фикстуры и тесты на этом домене. Кейс №1 (парковки) — только для финальной проверки, не для разработки: так мы не зашьём его в код.

```text
Заявки на ремонт оборудования офиса

Сотрудники офиса создают заявки на ремонт: тема, описание, приоритет (низкий, обычный, высокий).
Инженер берёт заявку в работу и закрывает её, указав решение. Закрыть заявку без решения нельзя.
Срок решения зависит от приоритета: высокий — 4 рабочих часа, обычный — 1 рабочий день, низкий — 3 рабочих дня.
Рабочее время — будни с 9:00 до 18:00. Если срок прошёл, заявка становится просроченной,
а диспетчер получает уведомление. Диспетчер видит все заявки и дашборд: открытые, просроченные,
среднее время решения. Инженер видит свои заявки и общую очередь.
```

Второй домен (фаза 3) — «выдача оборудования сотрудникам»: инвентарные номера, выдача по QR-коду, возврат, история, нельзя выдать больше двух ноутбуков одному сотруднику.

## 4. Порядок работы команды

1. **День 0, первые часы — контракты.** Каждый выкладывает свои модели в `contracts/` и фикстуры в `contracts/fixtures/tickets/`; Максим — `harness/fakes.py`. После этого контракты v1 заморожены.
2. **Фаза 1 — ходячий скелет.** Каждый делает свой этап на фикстурах и фейках, без чужого кода. Максим собирает цепочку на фейковых этапах (они просто копируют фикстуры), чтобы Студия и отчёт работали сразу.
3. **Фаза 2 — глубина.** Реальные вызовы модели, гейты, ремонт, лестница попыток, сканеры, документация.
4. **Фаза 3 — интеграция.** Сквозной прогон на домене `tickets` с настоящей моделью, затем на втором домене, затем на кейсе №1. Успех на одном домене не заменяет проверку на другом.

---

## 5. Твоя зона: тесты, проверка и отчёт

Ты отвечаешь за то, чтобы «зелёное» значило «требование выполнено», а не «модель подогнала тест». И за то, чтобы результат был честно показан. Три этапа и четыре гейта:

1. **`tests`** — тесты из критериев приёмки (AC) **до кода**, агентом, который не видит реализацию; гейт **G2** (red-proof).
2. **`verify`** — сборка, все тесты, мутации, сканеры, подъём стенда, smoke, E2E; гейты **G3** и **G4**.
3. **`report`** — отчёт, паспорт, документация продукта; гейт **G5**.

Это критерии «тестирование и безопасность» (15), «документация» (10), «эффективность» (10) и половина «продукта» — демо должно быть проверено тестом.

**Входит:** `contracts/verification.py`, `contracts/report.py`, фикстуры `contracts/fixtures/tickets/verification.json`, `report.json`; `stages/tests/` (включая `dispute.py`), `stages/verify/`, `stages/report/`; `gates/g2_redproof.py`, `g3_checks.py`, `g4_stand.py`, `g5_docs.py`; промпты `agents/qa-*`, `agents/writer-*`.

**Не входит:** тестовый набор шаблона `App.TestKit` и сгенерированные тесты прав и переходов (Иван); тела хуков (Иван); песочница как механизм (Максим).

## 6. Задачи

### T0. Контракты — первым делом

`contracts/verification.py`:

```python
class TestCase(BaseModel):
    id: str                      # "AcceptanceTests.SlaDeadline_AC05_FridayEvening"
    ac: str | None               # "AC-05"
    level: Literal["unit", "api", "rbac", "transition", "contract", "e2e"]
    file: str
    status: Literal["passed", "failed", "skipped", "not_run"]
    message: str | None = None

class AcStatus(BaseModel):
    specified: bool              # AC есть и проходит G1
    tested: bool                 # есть хотя бы один тест
    red_proof: bool | None       # прошёл G2 (None — тест с нейтральным ожиданием, проверен мутацией)
    implemented: bool            # связанные хуки не заглушки
    passes: bool                 # все тесты AC зелёные
    e2e: bool | None             # покрыт проходом и E2E зелёный (None — AC без UI)
    reason: str | None           # почему красный, по-русски

class Verification(BaseModel):
    schema_version: Literal[1] = 1
    build: dict[str, bool]                   # backend/admin/mobile → собралось
    tests: list[TestCase]
    mutations: list[dict]                    # хук, мутация, убита ли
    scans: list[dict]                        # инструмент, находки, high/critical
    stand: dict                              # up, health, smoke по ролям
    ac_status: dict[str, AcStatus]

class Dispute(BaseModel):
    test: str; ac: str; reason: str; hook: str
class DisputeDecision(BaseModel):
    decision: Literal["fix", "reject"]; reason: str
```

`contracts/report.py` — модель `report.json` (см. T6). Фикстуры — руками на домене `tickets`.

### T1. Этап `tests`

Агент-тестировщик видит **только**: AC с примерами, BR и `params`, `hooks.json` (сигнатуры и примеры), `openapi.json`, тестовый набор `App.TestKit` (§3.10), page objects. **Реализацию хуков не видит никогда.**

| Уровень | Откуда | Как | Куда |
|---|---|---|---|
| Unit хуков | Примеры из AC и `hooks.json` | Модель `qa`, один параметризованный тест на AC; строка на каждый пример; границы N−1 / N / N+1 обязательны | `backend/tests/App.Acceptance.Tests/Hooks/` |
| API по AC | Gherkin: Дано → сид и часы, Когда → команда, Тогда → query и события | Модель `qa`, через `AppFactory`, `Api.As(role)`, `TestClock`, `PublishedEvents` | `…/App.Acceptance.Tests/Api/` |
| E2E | Проходы из `ui.json` | **Код, без модели**: шаг `open` → переход, `fill` → ввод по testid, `tap` → клик, `expect` → проверка; данные из `seed` | `admin-web/e2e/<US>.spec.ts`, заголовок `@AC-xx` |
| Права и переходы | `app.json` | Генерирует Иван | `App.Generated.Tests` |

Правила для тестов (проверяет линтер тестов в G2):
- каждый тест помечен `[Trait("AC", "AC-xx")]` или `@AC-xx` в заголовке;
- пороги — из `App.Domain.Params`, а не литералами (линтер ищет числа, совпадающие со значениями `params`);
- время — только через `TestClock`; запрещены `DateTime.Now`, `Thread.Sleep`, `Task.Delay`;
- запрещены `Skip`, `[Fact(Skip=…)]`, пустые тела, тесты без проверок, `try/catch` вокруг проверок;
- ожидаемое значение не вычисляется тем же алгоритмом, что и реализация, — оно берётся из примера AC.

Сборка тестов — `sandbox.run("build", "backend")`; ошибка компиляции теста → повтор `qa` с ошибкой в контексте, не больше двух раз.

После G2 хэши всех файлов тестов → `reports/tests.json` и таблица `test_hashes` (через `StageOutput`; запись в таблицу делает платформа).

Образец промпта — «Трасса», `docs/trassa/p11.md`, приложение B.7. Главная фраза: «Тест, который проходит на пустой реализации, — дефект».

### T2. Гейт G2 — `gates/g2_redproof.py`

1. Тесты AC запускаются на каркасе с нейтральными заглушками хуков (`sandbox.run("test", "backend")` и разбор JUnit).
2. Тест, ожидающий **не нейтральное** значение (не «пусто», не «ноль», не «разрешено»), обязан упасть **на проверке** (`Assert`), а не на компиляции, настройке или исключении.
3. Тест с нейтральным ожиданием может законно пройти; для него `red_proof = None`, проверка переносится на мутации в `verify`.
4. Нарушение → находка с путём `tests/<id>`; `repair` этапа `tests` переписывает только этот тест; после двух кругов тест помечается «слабый» в паспорте.

| Код | Проверка | Важность |
|---|---|---|
| `TEST_GREEN_ON_STUB` | Тест с не нейтральным ожиданием прошёл на заглушке | error |
| `TEST_FAILS_WRONG` | Тест упал не на проверке (компиляция, исключение настройки) | error |
| `TEST_NO_AC` | Тест без метки AC | error |
| `AC_NO_TEST` | AC без единого теста | error |
| `TEST_FORBIDDEN` | Skip, пустое тело, `DateTime.Now`, `sleep`, литерал порога | error |

### T3. Споры — `stages/tests/dispute.py`

```python
def resolve(dispute: Dispute, workspace: Path, llm: LLM, sandbox: Sandbox) -> DisputeDecision: ...
```

Вызывает Иван из `develop`, когда разработчик считает тест противоречащим AC. Тестировщик (`qa`) получает тест, AC, BR и аргумент; решает `fix` (исправляет тест, тест снова проходит проверку G2, хэш обновляется со ссылкой на спор) или `reject` (тест остаётся, причина — в ответ). Один спор на тест; все споры — в отчёт.

### T4. Этап `verify`

1. Сборка всех целей: `sandbox.run("build", t)` для `backend`, `admin` (и `mobile`, если есть).
2. Сверка хэшей тестов с `reports/tests.json`: расхождение — ошибка G3, а не предупреждение.
3. Все тесты: `test` по целям, разбор JUnit → `TestCase[]`.
4. **Green-proof (мутации):** для каждого реализованного хука 3–5 мутаций тела (перевернуть сравнение, сдвинуть числовую константу на единицу, `&&` ↔ `||`, вернуть другой вариант перечисления) → тесты хука по фильтру AC → хотя бы один тест должен покраснеть на каждой мутации. Выжившая мутация — находка (тестировщику дописать пример). После мутаций файл хука восстанавливается.
5. Сканеры: `sandbox.run("scan", "stack")` по `pack.yaml` (gitleaks, trivy fs; semgrep — если есть в образе) → разбор SARIF/JSON.
6. Стенд: `up` → health всех сервисов → `smoke` (вход каждой ролью) → `e2e` (Playwright по проходам) → `down`.
7. Проекция `ac_status` по каждому AC (см. T0) → `reports/verification.json`.

Частичный результат — успех этапа: красные тесты и находки сканеров — это данные, а не исключение. Исключение — только если песочница недоступна (`StageFailed`).

### T5. Гейты G3 и G4

| Гейт | Код | Проверка | Важность |
|---|---|---|---|
| G3 | `BUILD_FAILED` | Цель не собралась | error |
| G3 | `TEST_HASH_MISMATCH` | Тест изменён после G2 без решения по спору | error |
| G3 | `AC_RED` | Есть красные тесты AC | warning (статус AC красный, прогон идёт дальше) |
| G3 | `MUTANT_SURVIVED` | Мутация хука выжила | warning |
| G3 | `SCAN_HIGH` | Находка high/critical | error |
| G3 | `SKIPPED_AS_PASS` | Пропущенный тест засчитан как пройденный | error |
| G4 | `STAND_DOWN` | Стенд не поднялся или health не 200 | error |
| G4 | `SMOKE_FAILED` | Роль не смогла войти или выполнить запрос | error |
| G4 | `E2E_FAILED` | Упал E2E прохода | warning (AC красный) |

### T6. Этап `report`

Выполняется **всегда**, даже если прогон упал раньше. Получает `inp.snapshot` от платформы (статусы этапов, гейты, флаги, агрегаты `llm_calls` и `tool_runs`).

**`reports/report.json`:**

```json
{"schema_version": 1,
 "run": {"id": "…", "status": "partial", "autonomy": "A2", "started_at": "…", "finished_at": "…"},
 "verdict": {"ac_total": 12, "ac_green": 9, "ac_red": 2, "ac_not_implemented": 1},
 "ac": [{"id": "AC-05", "status": "green", "tests": 3, "hooks": ["SlaDeadline"], "reason": null}],
 "assumptions": [{"id": "ASM-01", "text": "…", "answered_by": "default"}],
 "flags": [{"path": "hooks.X", "status": "questioned", "reason": "…"}],
 "checks": {"build": {}, "tests": {}, "mutations": {}, "scans": {}, "stand": {}},
 "metrics": {"wall_time_s": 0, "llm_calls": 0, "tokens": {"in": 0, "cached": 0, "out": 0, "reasoning": 0},
             "attempts_per_hook": 0.0, "first_pass_rate": 0.0, "interventions": 0,
             "by_stage": [], "by_task_class": []},
 "not_done": [{"what": "…", "why": "…"}],
 "links": {"stand": "…", "docs": "…", "openapi": "…"}}
```

**Формулы:** попыток на хук = Σ попыток / число хуков; first-pass rate = хуки, закрытые с первой попытки / все хуки; доля детерминированного кода = строки вне файлов хуков и `custom` / все строки сгенерированного кода; токенов на AC = Σ токенов / число AC; вмешательства = решения людей в `gate_results` + ответы на вопросы. Неизвестный расход — «неизвестно», а не ноль.

**`reports/report.md`** — таблицы и числа подставляет код; модель (`writer`) пишет только связный текст через плейсхолдеры `{{metric:tokens.out}}`, `{{ac:AC-05}}`, `{{param:SLA_HIGH}}` — код подставляет значения. Плейсхолдер на несуществующий объект — ошибка G5.

**Документация продукта `product/docs/`** (MkDocs Material, собирается в CI):
- **пользовательская** — по каждой роли «Как сделать …» для каждой её US по шагам прохода; скриншоты из прогонов E2E;
- **системная** — сущности (ER-диаграмма mermaid), машины состояний (mermaid), матрица прав, API (из `openapi.json`), события, интеграции, параметры правил с BR;
- **эксплуатационная** — запуск, переменные окружения, сервисы Compose, health, типовые неполадки;
- **трассировка** — REQ → US → BR → AC → хук → тест → статус.

Около 70% документации — таблицы и диаграммы из артефактов, без модели.

### T7. Гейт G5 — `gates/g5_docs.py`

| Код | Проверка | Важность |
|---|---|---|
| `DOC_AC_MISSING` | AC не упомянут в трассировке | error |
| `DOC_ROLE_MISSING` | У роли нет пользовательского руководства | error |
| `DOC_PLACEHOLDER` | Неразрешённый плейсхолдер | error |
| `DOC_NUMBER_LITERAL` | В тексте модели число, совпадающее с метрикой или параметром, вместо плейсхолдера | warning |
| `DOC_BROKEN_LINK` | Битая внутренняя ссылка | warning |

## 7. Как проверять независимо

- `tests`: `FakeLLM` с записанными тестами; фикстуры `app.json`, `hooks.json`, `ui.json`; проверка линтера тестов на заведомо плохих тестах (Skip, литерал порога, `DateTime.Now`).
- G2/G3: «правильная» и «заведомо неверная» реализации хука на фикстуре — правильная зеленит тесты, неверная краснит хотя бы один; мутации убиваются.
- `verify`: `FakeSandbox` со сценариями (всё зелёное; упал build; красный AC; high-находка; стенд не поднялся) → проверка `verification.json` и находок гейтов.
- `report`: два записанных `snapshot` — успешный и упавший прогон → отчёт честно показывает разницу; G5 на обоих.

## 8. Что ты отдаёшь другим и когда

| Что | Кому | Когда |
|---|---|---|
| `contracts/verification.py`, `report.py`, фикстуры | Максиму, Артёму | день 0 |
| `stages/tests/dispute.py` | Ивану | фаза 2 (до этого — заглушка, всегда `reject`) |
| Отчёт на фейковом `snapshot` | Артёму (Студия), Максиму | фаза 1 |

## 9. Чего не делать

- Не показывать тестировщику код хуков.
- Не засчитывать пропущенный тест как пройденный и не удалять тесты ради зелёного.
- Не давать модели писать числа в отчёт — только код.
- Не требовать падения на заглушке от теста с нейтральным ожиданием.
- Не прятать красное: «не реализовано», «не проверено», «не развёрнуто» — явные статусы.

## 10. Definition of Done

- На домене `tickets` с настоящей моделью: тесты по всем AC, G2 пройден, мутации убиты, стенд поднят, E2E по проходам зелёные или красные с причиной.
- Отчёт и документация собираются и для успешного, и для упавшего прогона; числа сходятся с `llm_calls`.
- Все коды G2–G5 покрыты тестами.
- Демо-сценарий кейса №1 — автоматический E2E-тест.

## 11. Промпт для нейросети

Скопируй блок ниже в чат вместе с этим файлом целиком (и, если есть доступ, с репозиторием `a-romash/rwb-ai-hack`, ветка `main`).

```text
Ты — сильный инженер (Python 3.12, C# xUnit, Playwright, тестирование и безопасность, MkDocs). Работаешь в команде из пяти человек над хакатонным проектом «универсальный ИИ-конвейер: бизнес-требования → работающее приложение». Выше — полный документ моей задачи: контекст кейса, архитектура, общие контракты команды (раздел 3) и мои задачи (раздел 5 и дальше).

Моя роль: Тимофей, тесты, проверка и отчёт (tests, verify, report, гейты G2–G5).
Мои папки: `contracts/verification.py`, `contracts/report.py`, фикстуры `verification.json`/`report.json`, `stages/tests/`, `stages/verify/`, `stages/report/`, `gates/g2_redproof.py`, `gates/g3_checks.py`, `gates/g4_stand.py`, `gates/g5_docs.py`, `agents/qa-*`, `agents/writer-*`. В чужие папки не пиши. Если там нужно изменение — оформи его отдельным пунктом «Запрос владельцу» с описанием и причиной.

Как работаем:
1. Сначала прочитай документ целиком. Затем в 10–15 строках перескажи: что я строю, что получаю на входе, что отдаю и кому. Перечисли неясности и противоречия, если видишь. Недостающие контракты не придумывай — спроси.
2. Делай задачи по порядку: T0 → T1 → T2 → T3 → T4 → T5 → T6 → T7. Начни с T0: от неё зависят коллеги.
3. Каждую задачу выдавай целиком: дерево файлов, затем каждый файл полностью с путём в заголовке, затем тесты, затем команды запуска. Без «…» и «остальное аналогично».
4. Контракты из раздела 3 — закон. Если для работы их нужно изменить, остановись и опиши изменение: что, зачем, кого затрагивает. В коде контракт сам не меняй.
5. Всё, что зависит от чужих частей, делай через фейки и фикстуры (FakeLLM, FakeSandbox, contracts/fixtures/tickets). Не жди коллег и не пиши их код.
6. Никакого домена в коде конвейера: ни парковок, ни заявок. Домен живёт только в фикстурах, тестах и eval.
7. Python 3.12 с аннотациями типов; C# / TypeScript — по правилам стека из документа. Тексты для людей — по-русски, идентификаторы — по-английски. Внешние зависимости — только необходимые, с закреплёнными версиями; перечисли их отдельно.
8. Каждый вызов модели — одноходовый, со свежим контекстом не больше профиля окна; данные от модели — JSON по Pydantic-схеме, код — текстом между <<<CODE и CODE>>>.
9. После каждой задачи — короткий отчёт: что сделано, как проверить, что осталось, какие допущения принял. Проверку «Готово, когда» из задачи выполняй буквально.

Начни с шага 1.
```
