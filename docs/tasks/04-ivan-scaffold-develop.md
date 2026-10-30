# Задачи: Иван — генератор, шаблон продукта и агент-разработчик (scaffold, develop)

> **Разблокировано Максимом (M0):** контракты этапов, гейтов и API, `FakeLLM`, `FakeSandbox` и локальный запуск уже в `main` ([86c50261](https://github.com/a-romash/rwb-ai-hack/commit/86c50261)). Можно писать и тестировать свою часть независимо; примеры — [contracts/README.md](https://github.com/a-romash/rwb-ai-hack/blob/main/contracts/README.md). Настоящие шлюз, песочница и API прогонов — следующая поставка.

> **Коротко.** Ты превращаешь спецификацию в приложение: золотой шаблон на стеке ТЗ и детерминированный генератор (`scaffold`), который строит собираемый проект с нейтральными заглушками хуков, OpenAPI, тестовым набором, Compose и CI; затем агент-разработчик (`develop`) вписывает тела хуков лестницей попыток. Первая задача (I0) — контракты хуков и манифеста плюс пустой собираемый шаблон.
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
- **Стек генерируемого приложения:** Angular 20.1.6 (UI Kit — Angular Material), C# 14 / ASP.NET Core 10, PostgreSQL 17.9 + PostGIS, REST + SSE, Docker / Docker Compose, GitLab CI/CD.
- **Решение команды по стеку (ресурсов стенда мало):** вместо Kafka — события через PostgreSQL (outbox-таблица, обработчики через `FOR UPDATE SKIP LOCKED`, `LISTEN/NOTIFY` для живых обновлений); вместо нативного Android на Kotlin — **PWA** на Angular (`mobile-web/`): устанавливается на телефон, работает с геолокацией, уведомлениями и камерой через браузерные API. Это осознанное отступление от стека ТЗ: оно записывается в README продукта и в отчёт.
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
            target: Literal["backend", "admin", "pwa", "stack"], *,
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

Неявное генератор выводит сам, в `app.json` это не пишется: CRUD, события на переходах (`TicketTaken`, `TicketExpired`, …), записи в таблице событий, тесты прав и переходов.

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

`platform: mobile` — мобильный интерфейс (например, полевого сотрудника). Он поставляется как **PWA** (`mobile-web/`), а не нативное приложение. Возможности устройства — через браузерные API: `location` → Geolocation API (пока приложение открыто; фонового трекинга у PWA нет), `local_notification` → Notification API через service worker, `external_link` → переход по ссылке, `scan_code` → BarcodeDetector или `@zxing/browser`, `file_pick` → `<input type="file" capture>`. В E2E — эмуляция мобильного устройства, геолокации и разрешений Playwright.

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
  pwa:
    image: rwb/tool-node:22-ng20.1.6
    workdir: mobile-web
    build: ["npm", "run", "build"]
    test:  ["npx", "jest", "--ci"]
    e2e:   ["npx", "playwright", "test"]
    filter: ["--grep", "@{filter}"]
  stack:
    up:    ["docker", "compose", "-f", "infra/docker-compose.yml", "up", "-d", "--wait"]
    smoke: ["python3", "infra/smoke.py"]
    down:  ["docker", "compose", "-f", "infra/docker-compose.yml", "down", "-v"]
scan:
  image: rwb/tool-security:1
  commands: [["gitleaks", "detect", "--source", "."], ["trivy", "fs", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "."]]
write_roots: [backend/src/App.Domain/Hooks, backend/src/App.Api/Custom, admin-web/src/app/custom,
              mobile-web/src/app/custom, db/seed]
readonly: [backend/tests, admin-web/e2e, mobile-web/e2e, spec]
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
- E2E — `admin-web/e2e/*.spec.ts` и `mobile-web/e2e/*.spec.ts` (мобильная эмуляция Playwright), заголовок теста начинается с `@AC-07`; page objects `*/e2e/pages/*` генерируются из `data-testid` в `ui.json`.
- `PublishedEvents` читает таблицу событий продукта (`domain_events`), а не брокер.

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

## 5. Твоя зона: генератор, шаблон продукта и разработчик

Ты превращаешь спецификацию в работающее приложение. Две части:
1. **`scaffold`** — детерминированный генератор (код, без модели): из `app.json` и `ui.json` строит собираемый проект на стеке ТЗ с нейтральными заглушками хуков, OpenAPI, тестовым набором, Compose и `.gitlab-ci.yml`. Плюс золотой шаблон `templates/product/` и манифест `pack.yaml`.
2. **`develop`** — агент-разработчик: вписывает тела хуков по лестнице попыток и места `custom`.

Объём кода, который пишет модель, — сотни строк. Всё остальное — шаблон и генератор. Это и качество, и скорость, и экономия токенов.

**Входит:** `contracts/hooks.py`, `contracts/pack.py`, фикстура `contracts/fixtures/tickets/hooks.json`; `templates/product/`; `stages/scaffold/`, `stages/develop/`; `harness/agent.py` (цикл с инструментами для `custom`); Dockerfile образов инструментов `templates/product/tools/`.

**Не входит:** тесты по AC (Тимофей), спецификация (Саня), формат `ui.json` (Артём), песочница как механизм запуска (Максим — запускает твои команды из `pack.yaml`).

## 6. Задачи

### I0. Контракты и пустой шаблон — первым делом

1. `contracts/hooks.py` — `HookSpec` по §3.8; `contracts/pack.py` — модель `pack.yaml` по §3.9.
2. `templates/product/pack.yaml` — команды сборки, тестов, запуска; `write_roots`, `readonly`.
3. Фикстура `contracts/fixtures/tickets/hooks.json` для хуков `SlaDeadline` и `ResolutionRequired`.
4. **Пустой шаблон, который собирается:** `backend/App.sln` + пять проектов, `admin-web/` на Angular 20.1.6 + Material, `infra/docker-compose.yml`, `.gitlab-ci.yml`. Сборка проходит в образах из `pack.yaml`.

**Готово, когда:** Максим может запустить `build`/`test` по манифесту на пустом шаблоне; Тимофей видит структуру тестового набора (§3.10).

### I1. Золотой шаблон `templates/product/`

**Backend (ASP.NET Core 10, C# 14)** — модульный монолит с вертикальными срезами:

```text
backend/
  global.json                  SDK 10.0.x закреплён
  Directory.Build.props        Nullable, анализаторы; Reliability/Security/Usage — ошибки
  Directory.Packages.props     Central Package Management: версии = allowlist
  BannedSymbols.txt            DateTime.Now, DateTime.UtcNow, Console.WriteLine — ошибка компиляции
  src/App.Api/                 Minimal API (MapGroup по фичам), JWT, OpenAPI 3.1, SSE, health, ProblemDetails
  src/App.Application/         команды, запросы, обработчики, порты
  src/App.Domain/              сущности, машины состояний, Params, Hooks/
  src/App.Infrastructure/      EF Core 10 + Npgsql (+ NetTopologySuite), миграции, outbox → таблица `domain_events`, адаптеры
  src/App.Worker/              обработчики событий из `domain_events`, планировщик таймеров
  tests/App.TestKit/           тестовый набор (§3.10)
  tests/App.Generated.Tests/   права и переходы — генерируются
  tests/App.Acceptance.Tests/  пустой проект: сюда пишет Тимофей
  tests/App.Architecture.Tests/  NetArchTest: Domain не зависит от Infrastructure и т. п.
```

Без MediatR, MassTransit, AutoMapper, FluentAssertions (коммерческие лицензии). Время — только `TimeProvider`. События — только через outbox. Планировщик — свой `BackgroundService` + таблица задач с `FOR UPDATE SKIP LOCKED`.

**Admin-web (Angular 20.1.6 + Angular Material):** standalone, signals, `OnPush`, новый control flow; фасад из ~12 компонентов (`app-page`, `app-data-table`, `app-filter-bar`, `app-status-chip`, `app-map-view`, `app-timeline`, `app-kpi-card`, `app-empty-state`, `app-confirm-dialog`, `app-form-field`, …) с шпаргалкой ≤ 30 строк; клиент API из OpenAPI (`openapi-generator`, `typescript-angular`); SSE через `fetch` + `ReadableStream` (заголовок авторизации); Jest, Playwright, axe.

**Infra:** `infra/docker-compose.yml` — `db` (`postgis/postgis:17`), `backend`, `worker`, `admin` (nginx), `mobile` (nginx, PWA), `mock` (по `integrations`). Kafka нет — события в PostgreSQL; health-check у каждого, `depends_on: service_healthy`, миграции и сид при старте; `infra/smoke.py` — вход демо-пользователем каждой роли и один запрос на роль. `.gitlab-ci.yml` — стадии `lint`, `build`, `test`, `security`, `package`, `deploy`, `e2e`, `docs` (скелет — «Трасса», `docs/trassa/p11.md`, приложение D).

**События через PostgreSQL** (вместо Kafka — решение команды):
- `domain_events` (`id` bigserial, `type`, `subject`, `payload` в конверте CloudEvents, `created_at`) пишется в **той же транзакции**, что и изменение сущности (outbox);
- обработчики в `App.Worker` — цикл «взять пачку через `FOR UPDATE SKIP LOCKED` по позиции обработчика → выполнить → записать `processed_events(consumer, event_id)` в той же транзакции»; повторы с задержкой, после трёх неудач — отметка `failed` и запись в журнал администратора;
- после коммита — `NOTIFY app_events, '<id>'`; мост SSE в `App.Api` слушает `LISTEN` и отдаёт события подписчикам по ролям и фильтрам;
- задача очистки удаляет обработанные события старше срока хранения;
- AsyncAPI-описание генерируется так же: канал = тип события.

**Mobile — PWA `mobile-web/`** (вместо Kotlin/Android — решение команды): Angular 20.1.6 + Angular Material + `@angular/service-worker` (манифест, офлайн-кэш оболочки, установка на домашний экран); экраны из `ui.json` с `platform: mobile` в мобильной вёрстке; тот же клиент API и SSE, что в `admin-web`; возможности устройства через браузерные API (§3.7); Jest и Playwright с мобильной эмуляцией. Фаза 2.

### I2. Генератор `stages/scaffold/`

1. `app.json` → нормализованная модель: имена во всех нотациях, развёрнутые соглашения (CRUD на каждую сущность, событие на каждый переход `<Entity><Transition>ed`, тип события в `domain_events`).
2. Модель → `product/openapi.json` (CRUD + команды + запросы, роли в описании) → `openapi-generator`: клиент TypeScript, общий для `admin-web` и `mobile-web`.
3. Модель → шаблоны Jinja по модулям: сущности, EF-конфигурации, миграции, DTO, эндпоинты с политиками из `permissions` (включая фильтр области `own`/`team`), машины состояний с таблицей переходов, таймеры (`timer`-триггеры), уведомления, outbox, сид, параметры `App.Domain.Params` из `params`.
4. **Хуки:** для каждого хука из `app.json` — интерфейс `I<Name>Hook` в `Generated` и класс `<Name>Hook` в `Hooks/` с **нейтральной** заглушкой; регистрация в DI; если у хука `select` — генератор выполняет query и передаёт результат входом.
5. **`hooks.json`:** для каждого хука `HookSpec`: файл, сигнатура, контракт из BR, `allowed_api` (публичные типы, которые нужны хуку), `examples` — из таблиц «Примеры» Gherkin связанных AC (разбор Gherkin — кодом).
6. **Экраны `admin-web` (`platform: web`) и `mobile-web` (`platform: mobile`) из `ui.json`** по каталогу `contracts/ui_catalog.md` (Артём): маршруты, меню по ролям, страницы паттернов, виджеты, `data-testid`; page objects `*/e2e/pages/*` из testid.
7. **Тесты генератора:** права (каждая пара «роль × операция» → 200 или 403; `own` не видит чужое) и переходы (недопустимый → 409; событие на каждом переходе) → `App.Generated.Tests`.
8. Форматтеры: `dotnet format`, `prettier`.
9. `custom` → заглушка с текстом описания в `Custom/<id>/` и пометка в `reports/develop.json`.

**Generation gap.** Сгенерированное и написанное моделью никогда не лежат в одном файле. Повторная генерация перезаписывает `Generated/**` и не трогает `Hooks/`, `Custom/`, `db/seed/` ручного содержимого. Если сигнатура хука поменялась — ломается компиляция именно в файле хука.

**Детерминизм.** Одинаковый вход → побайтно одинаковый выход. Снапшот-тесты генератора на фикстурах `tickets` и `equipment`: дерево файлов и содержимое ключевых файлов. Ошибка компиляции вне файла хука — баг генератора, а не модели.

### I3. Этап `develop`

**Единица работы** — один хук. Порядок — по зависимостям: домен → приложение → API → UI; хуки одного файла последовательно.

**Лестница попыток** (каждая — один вызов `llm(..., output="code")` со свежим контекстом):

| Попытка | `task_class` | Что добавляется в контекст |
|---:|---|---|
| 1 | `hook_1` | — |
| 2 | `hook_2` | предыдущее тело + ошибки компилятора или упавшие тесты (до 20 строк, с ожидаемым и фактическим) |
| 3 | `hook_3` | то же + расширенные сигнатуры |
| 4 | `hook_4` ×3 | три кандидата; берётся первый, который собирается и проходит тесты |
| — | — | заглушка остаётся, хук и его AC красные с причиной; дальше следующий хук |

**Контекст попытки** (в пределах профиля окна): ролевая карточка, шпаргалка по стеку (≤ 30 строк из шаблона), `HookSpec`, сигнатуры `allowed_api`, один готовый хук того же вида как образец. Образец промпта — «Трасса», `docs/trassa/p11.md`, приложение B.5–B.6.

**После ответа:** тело вставляется в метод хука → `sandbox.run("build", "backend")` → `sandbox.run("test", "backend", filter=<AC хука>)`. Хук принимается, только если зелёные его тесты **и** весь набор тестов стека; иначе откат файла к предыдущему зелёному состоянию.

**Ограничения:** запись только в файл хука; тесты только читаются; новые пакеты добавлять нельзя (хуку нужна библиотека вне allowlist → завершение с причиной «нужна зависимость X»).

**Спор с тестом.** Если модель вместо кода вернула строку `// DISPUTE: <тест> — <причина>, <AC>`, вызови `stages.tests.dispute.resolve(...)` (контракт — `contracts/verification.py`, владелец Тимофей). `fix` → тест исправлен, лестница начинается заново; `reject` → аргумент и ответ — в контекст следующей попытки. Один спор на тест.

**Места `custom`** — цикл с инструментами `harness/agent.py` (`read_file`, `write_file`, `build`, `run_tests`, `finish`): пути из `pack.yaml`, лимит ходов, откат к зелёному снимку при отсутствии прогресса. Доработай: путь записи `mobile-web/src/app/custom`; пути и команды из `pack.yaml` вместо констант; `effort` из класса задачи вместо `xhigh`.

**Выход:** `reports/develop.json`:

```json
{"schema_version": 1,
 "hooks": [{"id": "SlaDeadline", "status": "implemented", "attempts": 2,
            "first_pass": false, "tests": {"passed": 6, "failed": 0}, "disputes": []},
           {"id": "ResolutionRequired", "status": "stub", "attempts": 4,
            "reason": "тест AC-07 красный после 4 попыток: …"}],
 "custom": [{"id": "C-01", "status": "implemented", "turns": 5}],
 "summary": {"total": 2, "implemented": 1, "stub": 1, "first_pass": 0}}
```

`BudgetExceeded` → оставшиеся хуки получают статус `stub` с причиной «бюджет исчерпан»; этап завершается успешно с частичным результатом.

## 7. Как проверять независимо

- Генератор: снапшот-тесты на фикстурах; сборка сгенерированного проекта с нуля в образе; повторная генерация после правки `app.json` не теряет вручную вписанный хук.
- `develop`: `FakeLLM` с записанными телами хуков (правильное, с ошибкой компиляции, с падающим тестом) и `FakeSandbox` → проверка лестницы, отката, `develop.json`. Затем — с настоящей песочницей на фикстуре и эталонными тестами, которые ты сам напишешь для двух хуков `tickets` (Тимофей потом заменит их своими).

## 8. Что ты отдаёшь другим и когда

| Что | Кому | Когда |
|---|---|---|
| `contracts/hooks.py`, `pack.py`, `pack.yaml`, пустой шаблон | Максиму, Тимофею | день 0 |
| Тестовый набор `App.TestKit` (§3.10) | Тимофею | фаза 1 |
| Генератор на фикстурах | всем | фаза 1 |
| `develop` на настоящей модели | всем | фаза 2 |

## 9. Чего не делать

- Не давать модели писать то, что можно сгенерировать: CRUD, миграции, эндпоинты, права, клиенты, CI, Compose.
- Не смешивать сгенерированное и написанное моделью в одном файле.
- Не держать историю диалога между хуками и попытками.
- Не давать модели редактировать `.gitlab-ci.yml`, `docker-compose.yml`, зависимости и тесты.
- Не зашивать домен в шаблоны.

## 10. Definition of Done

- Генератор детерминирован; сгенерированный продукт на `tickets` и `equipment` собирается, поднимается в Compose, проходит тесты прав и переходов и smoke.
- `develop` на `tickets` с настоящей моделью закрывает хуки или честно оставляет заглушки с причиной; `develop.json` заполнен.
- Перегенерация не теряет хуки.
- `.gitlab-ci.yml` продукта проходит на GitLab (или локально через `gitlab-ci-local`) хотя бы до стадии `test`.

## 11. Промпт для нейросети

Скопируй блок ниже в чат вместе с этим файлом целиком (и, если есть доступ, с репозиторием `a-romash/rwb-ai-hack`, ветка `main`).

```text
Ты — сильный инженер (C# 14 / ASP.NET Core 10, EF Core, Angular 20 + Material + PWA, Python 3.12, Jinja2, Docker). Работаешь в команде из пяти человек над хакатонным проектом «универсальный ИИ-конвейер: бизнес-требования → работающее приложение». Выше — полный документ моей задачи: контекст кейса, архитектура, общие контракты команды (раздел 3) и мои задачи (раздел 5 и дальше).

Моя роль: Иван, генератор, шаблон продукта и агент-разработчик (scaffold, develop).
Мои папки: `contracts/hooks.py`, `contracts/pack.py`, фикстура `hooks.json`, `templates/product/`, `stages/scaffold/`, `stages/develop/`, `harness/agent.py`. В чужие папки не пиши. Если там нужно изменение — оформи его отдельным пунктом «Запрос владельцу» с описанием и причиной.

Как работаем:
1. Сначала прочитай документ целиком. Затем в 10–15 строках перескажи: что я строю, что получаю на входе, что отдаю и кому. Перечисли неясности и противоречия, если видишь. Недостающие контракты не придумывай — спроси.
2. Делай задачи по порядку: I0 → I1 → I2 → I3. Начни с I0: от неё зависят коллеги.
3. Каждую задачу выдавай целиком: дерево файлов, затем каждый файл полностью с путём в заголовке, затем тесты, затем команды запуска. Без «…» и «остальное аналогично».
4. Контракты из раздела 3 — закон. Если для работы их нужно изменить, остановись и опиши изменение: что, зачем, кого затрагивает. В коде контракт сам не меняй.
5. Всё, что зависит от чужих частей, делай через фейки и фикстуры (FakeLLM, FakeSandbox, contracts/fixtures/tickets). Не жди коллег и не пиши их код.
6. Никакого домена в коде конвейера: ни парковок, ни заявок. Домен живёт только в фикстурах, тестах и eval.
7. Python 3.12 с аннотациями типов; C# / TypeScript — по правилам стека из документа. Тексты для людей — по-русски, идентификаторы — по-английски. Внешние зависимости — только необходимые, с закреплёнными версиями; перечисли их отдельно.
8. Каждый вызов модели — одноходовый, со свежим контекстом не больше профиля окна; данные от модели — JSON по Pydantic-схеме, код — текстом между <<<CODE и CODE>>>.
9. После каждой задачи — короткий отчёт: что сделано, как проверить, что осталось, какие допущения принял. Проверку «Готово, когда» из задачи выполняй буквально.

Начни с шага 1.
```
