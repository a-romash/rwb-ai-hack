# Передача контекста: интеграция веток и исправления (30.10.2026)

Документ для того, кто продолжает работу: человек или ИИ-агент. В нём собраны ТЗ, устройство кода, принятые решения, сделанное, способ проверки и список дел. Сначала прочитайте разделы 1, 3 и 8.

- Репозиторий: `a-romash/rwb-ai-hack` (GitHub).
- Рабочая ветка интеграции: **`claude/review-docs-branches-48sc58`**. В ней влиты все ветки команды и исправления. Свежее состояние — `git log`; раздел 5 и статусы в разделе 8 обновлены во второй сессии (локальный Docker).
- Ревью со всеми находками: issue **#3** (https://github.com/a-romash/rwb-ai-hack/issues/3), с комментариями-дополнениями.
- Открытые PR: #2 (`feat/artem-ui-contract` → `main`), #4 (`feature/studio-frontend` → `main`). Обе ветки уже влиты в ветку интеграции. Отдельно их сливать не нужно, если в `main` уйдёт ветка интеграции.
- Старые ветки **не удалены**, так попросил владелец: `docs`, `docs-80s7c7`, `feat/maxim-platform`, `feat/timofey-quality`, `feat/artem-ui-stage`, `feat/artem-ui-contract`, `feat/sanya-contracts`, `ivan`, `feature/studio-frontend`.
- В `main` ничего не пушилось. Следующий шаг — PR из ветки интеграции в `main`.

---

## 1. Что строим (ТЗ хакатона Russtech / RWB)

**Кейс:** «Агентский ИИ-пайплайн полного цикла разработки корпоративных приложений». Нужно сделать не одно приложение, а **универсальный конвейер**. На входе только бизнес-требования. На выходе:
- анализ и системный анализ;
- интерфейс и код;
- тесты, инфраструктура, CI/CD;
- документация;
- развёрнутый прототип;
- отчёт о расходе токенов, времени и попыток.

- **7 этапов по ТЗ:** приём и анализ требований → системный анализ → проектирование интерфейса → разработка → тестирование и безопасность → сборка и развёртывание → документация.
- **Оценка (100 баллов):** анализ 20, продукт и интерфейс 15, архитектура и разработка 20, тесты и безопасность 15, инфраструктура 10, документация 10, эффективность пайплайна 10. Отсутствующие этапы не дисквалифицируют, но баллов за них нет.
- **Кейс №1 (открыт):** «Парковочный помощник для технических служб» (СПб). Нужно определять нахождение машины в платной зоне, отслеживать сессию, предупреждать за 10 минут, фиксировать смену зоны, вести историю и админку. **Кейс №2 скрыт:** жюри запустит конвейер на нём при оценке. Поэтому в коде конвейера **нельзя зашивать домен**.
- **Стек генерируемого приложения по ТЗ:** Angular 20.1.6, C# 14 / ASP.NET Core 10, PostgreSQL 17.9 + PostGIS, Kotlin 2.2.21 (Android), Kafka + REST, Docker Compose, GitLab CI 19.4.2, LLM Qwen3.8-27B.
- **Решения команды по стеку** (зафиксированы в `docs/architecture-v2.md`, R17 и R18):
  - **вместо Kafka** — события через PostgreSQL (outbox, `SKIP LOCKED`, `LISTEN/NOTIFY`);
  - **вместо нативного Android** — **PWA** на Angular (`mobile-web/`).

  Это отступление от ТЗ и риск по баллам: в слайде «Ожидаемые компоненты» явно указаны «Мобильное приложение на Kotlin» и Kafka. Отступление нужно громко вынести в README и отчёт.
- **Требования к сдаче:** работающий пайплайн, репозиторий в **локальном GitLab**, документы, код, тесты, Docker-окружение, CI/CD, прототип, пользовательская документация, отчёт о токенах, времени и попытках, видео.

### Данные кейса
Владелец присылал `spb.json` (6867 зон) и `response.json` (Москва, 16656 зон). В репозиторий они не входят. Формат: `{result, message, data: {city, zones: [...]}}`. У зоны:
- `externalZoneId` (строка);
- `displayName`;
- `geometry` — WKT, порядок `lon lat`;
- `price` в копейках;
- `priceDescription`, `minTime`, `timeStep`;
- `tariff.periods[]`: `from`/`to` — минуты суток (480–1200 = 08:00–20:00), `type` — car/truck/bus;
- `hasHolidays`.

**В СПб полигонов нет:** 6563 `LINESTRING`, 299 `MULTILINESTRING`, 5 `GEOMETRYCOLLECTION`. Поэтому «машина в зоне» требует буфера вокруг линии (`detect_area`, решение R10). Профайлер Сани пока видит `geometry` как строку и WKT не разбирает (см. раздел 8).

---

## 2. Команда и владение

Так в `docs/tasks/*.md`. Ветки, если важно авторство, смотреть в `git log`.

| Участник | Зона | Файлы |
|---|---|---|
| Максим (zurgenius) | Платформа: раннер, API прогонов, шлюз LLM, песочница, механизм гейтов | `backend/app/`, `harness/` (кроме `agent.py`), `gates/core.py`, `contracts/{stage,gates,api}.py`, `compose.yaml` |
| Саня (Hausmaster333) | `analysis`, `spec`, G0, G1 | `stages/analysis`, `stages/spec`, `gates/g0_inputs.py`, `gates/g1_spec.py`, `contracts/{analysis,app}.py`, `agents/analyst-*`, `agents/system-analyst-*` |
| Артём (a-romash) | `ui`, G1.5, Студия | `stages/ui`, `gates/g15_ui.py`, `contracts/ui.py`, `agents/ux-*`, `frontend/` |
| Иван (streamferow) | `scaffold`, `develop`, шаблон продукта | `stages/scaffold`, `stages/develop`, `templates/product`, `contracts/{hooks,pack}.py`, `harness/agent.py` |
| Тимофей | `tests`, `verify`, `report`, G2–G5 | `stages/tests`, `stages/verify`, `stages/report`, `stages/quality.py`, `gates/g2..g5`, `contracts/{verification,report}.py` |

Ветку `feat/timofey-quality` коммитил zurgenius. Студию (`feature/studio-frontend`) сделал Тимофей Семикин, хотя по tasks это зона Артёма. Договоритесь о владельце Студии.

---

## 3. Архитектура (как устроено сейчас)

### 3.1 Источник истины в документах
- `docs/architecture-v2.md` + `docs/tasks/*.md` — **актуальные**. Контракты описаны в §3 каждого task-файла, во всех пяти файлах одинаково.
- `docs/architecture-overview.md` — **устаревший** MVP-план. Он противоречит v2: только web, остановка на первом упавшем этапе. Надо пометить его устаревшим (раздел 8).
- `docs/trassa/p1–p11` — справочник «Трасса», откуда взяты идеи.
- В v2 местами остались `*.yaml` (`analysis.yaml`, `app.yaml`, `ui.yaml`). **Принято: всё, что генерирует конвейер, — JSON** (решение владельца и Максима, 30.10). Docker и GitLab-файлы остаются YAML, иначе их не прочитают.

### 3.2 Платформа (Python)
- **Стек:** FastAPI + SQLAlchemy/Alembic + Celery. Брокер — тот же PostgreSQL через Kombu SQLAlchemy transport; Redis и RabbitMQ нет. Студия — Angular 20.1.6 + Taiga UI 5.
- **Сервисы** (`compose.yaml`): `postgres`, `api`, `worker-llm` (очереди `llm,celery`), `worker-build` (`build`, с Docker-сокетом), `worker-io` (`io`), `frontend`.
- **Цепочка этапов** — фиксированная (`harness/registry.py`):
  `analysis(G0) → spec(G1) → ui(G1.5) → scaffold → tests(G2) → develop → verify(G3,G4) → report(G5)`.
  Шаг `report` выполняется всегда.
- **Граница этапа** (`contracts/stage.py`): `execute(inp: StageInput, workspace: Path, llm: LLM, sandbox: Sandbox) -> StageOutput`, опционально `repair(...)`. Этап не знает про HTTP, Celery и БД.
- **Раннер** (`backend/app/runner.py`): `advance()` ставит следующий этап, `_execute()` выполняет этап, гоняет гейты (`gates/core.py::run_gate`, до двух кругов `repair`), коммитит workspace, пишет артефакты, `gate_results`, `spec_flags`, события.
- **Понижение вместо падения (R13):**
  - error-находки гейта в последнем круге становятся `spec_flags`, прогон получает статус `partial`;
  - зависимые элементы ищутся через `contracts.app.dependents` **только для путей `app.json`** (`_is_app_path`);
  - флаги, которые возвращают сами этапы (`StageOutput.flags`), тоже сохраняются (`gate = "stage:<key>"`).
- **Рабочая папка прогона:** `WORKSPACES_DIR/<project_id>/runs/<run_id>/` — это git-репозиторий (`harness/workspace.py`). Создаётся `.gitignore` для `node_modules`, `.nuget`, `bin`, `obj`, `dist`. Git работает со своим глобальным конфигом (`safe.directory=*`), потому что API и воркеры могут работать от разных пользователей.
- **Шлюз LLM** (`harness/llm.py` + `backend/app/llm_binding.py`):
  - классы задач (`TASKS`) и профили окна XS–L;
  - structured JSON с фолбэком;
  - код из модели — между `<<<CODE`/`CODE>>>`;
  - кэш по хэшу, в ключе номер попытки (`cache_salt`);
  - учёт в `llm_calls`;
  - бюджет: стоп только если ответ пришёл без usage; ошибки транспорта бюджет не «отравляют».
- **Песочница** (`harness/sandbox.py::DockerSandbox`):
  - команды только из доверенного `templates/product/pack.json`;
  - `restore` — один раз на цель, с сетью (`bridge`); `build` и `test` — без сети;
  - env цели из манифеста;
  - контейнер работает от владельца workspace;
  - несколько JUnit склеиваются в `reports/junit-merged/<target>.xml`, устаревшие удаляются перед запуском;
  - compose продукта валидируется (`$` запрещён, кроме `$$`, без bind-монтирований, сборка с `network: none`);
  - путь workspace на хосте: `HOST_WORKSPACES_DIR` или `docker inspect` собственного контейнера (`host_workspaces_dir`).
- **API Студии:** `backend/app/runs.py` (`/api/projects/{id}/runs`, `/api/runs/{id}`, `/artifacts`, `/files`, `/events`, `/events/stream` (SSE), `/metrics`, `/retry`, `/answers`, `/gates/{gate}/decision`, `/cancel`). Модели — `contracts/api.py`.

### 3.3 Этапы
- **`analysis`/`spec` (Саня):** цепочки узких шагов с моделью, проверкой и JSON Patch-ремонтом. Выходы — `spec/analysis.json` и `spec/app.json`. Модели `contracts/analysis.py`, `contracts/app.py`. Классы задач `req_extract`, `req_lint`, `spec_step`, `patch`. Свои промпты лежат в `agents/analyst-*` и `agents/system-analyst-*`.
- **`ui` (Артём):** база выводится кодом из `app.json`, модель её дорабатывает (платформы, патчи, проходы US, тексты, устройства). Выход — `spec/ui.json` по строгой схеме `contracts/ui.py` (`extra="forbid"`). Гейт G1.5 — `gates/g15_ui.py`.
- **`scaffold` (Иван + мои доработки):** детерминированный, без модели. Копирует `templates/product` в `product/` и генерирует:
  - `backend/src/App.Domain/Generated/Model.cs` — перечисления, состояния машин (`<Machine>State`), сущности (`[JsonRequired]` на обязательных полях), команды (`record`);
  - `.../Generated/Params.cs` — `App.Domain.Params`: пороги правил (`TimeSpan` для duration, `int[]` для списков);
  - интерфейсы `I<Hook>Hook` и нейтральные заглушки `Hooks/<Hook>Hook.cs`; заглушки при повторной генерации не перезаписываются;
  - `src/App.Api/Features/Generated/Endpoints.cs` — `Access` (роли и гранты) и `GeneratedEndpoints` (CRUD, команды);
  - `src/App.Infrastructure/Generated/AppDbContext.Model.cs`;
  - `tests/App.Generated.Tests/cases/api.json`, `infra/roles.json`;
  - `hooks.json` (с `method`/`returns`/`parameters`), `openapi.json`;
  - маршруты админки и page objects.

  Генератор: `stages/scaffold/generate.py`, `domain.py`, `api.py`.
- **`tests` (переписан):** см. раздел 4.
- **`develop` (Иван + правки):** лестница из четырёх попыток (`hook_1..hook_4`) на хук. Модель возвращает тело файла хука, затем `build` и `test --filter-trait AC=<первый AC>`. Хук без единого прогнанного теста не принимается. `task_id` = id хука.
- **`verify` (Тимофей + правки):**
  - сборка целей по платформам из `ui.json`: backend всегда, admin при web-экранах, pwa при mobile;
  - тесты, мутации хуков, сканеры, `up` стенда, smoke, E2E, `down`;
  - результат — `reports/verification.json`.
- **`report` (Тимофей):** `reports/report.json` и `.md`, `product/docs/`. Числа считает код, модель пишет только связный текст.

### 3.4 Шаблон продукта (`templates/product`)
- **`backend/`** — ASP.NET Core 10:
  - проекты `App.{Api,Application,Domain,Infrastructure,Worker}`;
  - тесты `App.{Acceptance,Generated,Architecture}.Tests` + `App.TestKit`;
  - xunit.v3 в режиме Microsoft.Testing.Platform (`UseMicrosoftTestingPlatformRunner` + `global.json test.runner`).
- **`Program.cs`:**
  - JSON в snake_case, enum — snake_case-строки, `RespectNullableAnnotations`/`RespectRequiredConstructorParameters`, `ThrowOnBadRequest=false` (неполное тело — 400);
  - JWT, у которого и выдача, и проверка срока идут через `TimeProvider`;
  - dev-вход `POST /api/auth/login {role}` и `GET /api/auth/me`;
  - `EnsureCreated()` (миграций нет) и загрузка `seed.json` (scaffold пишет его из `app.json.seed`, id — детерминированные uuid5);
  - `--healthcheck` для контейнера.
- **`App.TestKit`:** `AppFactory` (InMemory-БД, `As(role)` логинится через API), `TestClock`, `Json.Options` (snake_case, `IsRequired` снят для кейсов).
- **`admin-web/`** — Angular 20 + Material. Один рендерер `src/app/screens/screen-page.*` строит экраны по `generated/model.ts`, который scaffold пишет из `ui.json` и `app.json`: списки, формы, карточки, дашборды с `data-testid` из `ui.json`, подтверждение через диалог, KPI, опрос live-экранов. Демо-вход по роли: `?role=` или выбор на стартовой странице.
- **`mobile-web/`** (PWA) — копия рендерера (`screens/`, `ui/` обязаны совпадать, это проверяет тест scaffold) плюс service worker, manifest, нижнее меню, офлайн-бейдж, геолокация (WKT POINT в поля `geo_point`) и локальные уведомления о новых строках.
- **`infra/`:**
  - `docker-compose.yml`: `db` (postgis), `mock` (wiremock), `backend`, `worker`, `admin`, `mobile`; сборка из workspace с `network: none`, эфемерные порты, без Kafka;
  - `smoke.py`: `BASE_URL=http://backend:8080`, логин каждой ролью, отчёт `reports/smoke.json`.
- **`backend/Dockerfile`** (цели `api`/`worker`, контекст — корень продукта) и `admin-web/Dockerfile` (+ `nginx.conf`, прокси `/api`).
- **`tools/Dockerfile.{dotnet,node,security}`** → образы `rwb/tool-dotnet:10`, `rwb/tool-node:22` (на базе playwright), `rwb/tool-security:1` (база trivy вшита). Собираются `docker compose --profile tools build`.
- **`App.Worker`** — раз в 30 с вызывает `Generated/Timers.cs`: переходы машин состояний с `trigger.timer` (например, `expire`: `in_progress → overdue`, когда прошёл `due_at`), guard-хук вызывается, если его аргументы связываются.
- **`pack.json`** — манифест песочницы:
  - цели `backend`, `admin`, `pwa`, `stack`; команды `restore`/`build`/`test`/`filter`/`e2e`/`up`/`smoke`/`down`, `env`, `reports`;
  - `scan`;
  - `write_roots` (куда модели можно писать) и `readonly`.
- **`.gitlab-ci.yml`** продукта: lint (`dotnet format`), build, test (MTP JUnit, jest), security (gitleaks JSON, trivy SARIF), deploy стенда (`environment: review/...` + stop), smoke, E2E admin и PWA, docs.

---

## 4. Тесты продукта: принятый подход

Решение владельца и Максима: **модель не пишет C#. Кейсы — JSON, тесты строятся детерминированно.**

### 4.1 Тесты бизнес-правил (хуков) — этап `tests`
- `stages/tests/cases.py`:
  - `examples()` достаёт строки таблиц `Примеры:` из Gherkin критериев (через `stages.spec.semantics`);
  - `direct()` — если колонки называются как входные параметры хука и есть колонка ожиданий (`expected`/`result`/`результат`/`ожидается`/`итог`), кейсы строятся **без модели**;
  - иначе `ask()` — **один structured-вызов на хук** (`task_class="qa"`, `task_id=<hook>`, `output=ModelCases`). Модель только переводит строки во входы хука; при < 3 примерах добавляет граничные N−1/N/N+1;
  - `check()` требует, чтобы были все строки таблицы и правильные имена входов;
  - `BudgetExceeded` → источник `budget`, этап продолжается.
- **Файлы:**
  - `product/backend/tests/App.Acceptance.Tests/cases/hooks/<Hook>.json`: `{schema_version, hook, method, cases: [{id, ac, inputs: {<param>: ...}, expected}]}`. Входы — объекты с именами полей из `app.json` (snake_case), enum и состояния — их значения, даты — ISO 8601;
  - `Generated/AC_xx.cs` — класс на критерий, генерирует код (`test_class()`): `[Theory, Trait("AC","AC-xx"), MemberData]` → `HookCases.Run`.
- **Раннер** `App.Acceptance.Tests/HookCases.cs` (в шаблоне):
  - находит `App.Domain.Hooks.<Hook>Hook` и метод;
  - параметры, имя которых совпадает с полем `App.Domain.Params`, берутся оттуда, остальные — из `inputs`;
  - `Assert.Equal(expected, actual)`.
- **Red-proof:** на нейтральной заглушке кейс с не нейтральным ожиданием падает на `Assert.Equal`; это и есть доказательство. Манифест — `reports/tests.json` (`TestsManifest`) с хэшами всех файлов тестов, включая кейсы. После этого тесты защищены от `develop`.
- **Сводка источников кейсов:** `reports/test-cases.json` (`gherkin` / `model` / `mixed` / `budget` / `none`).
- **Критерии без хуков** (например, CRUD и уведомления: AC-01, AC-02, AC-07 в `tickets`) unit-тестов не получают. G2 сообщает `AC_NO_TEST`, прогон уходит в `partial`. Это честно, но такие AC стоит покрыть API-сценариями (раздел 8).

### 4.2 API-тесты — этап `scaffold`
- `stages/scaffold/api.py::api_cases()` строит из матрицы прав `cases/api.json`:
  - роль × (`read`, `create`) → 200/201/403;
  - аноним → 401;
  - тело без обязательного поля → 400;
  - команды → 404 (записи нет, но доступ есть) или 403.
- **Раннер** `App.Generated.Tests/ApiCases.cs` гоняет кейсы через `AppFactory` (InMemory).
- **Проверено:** на фикстуре `tickets` **22/22 зелёные** (21 API + архитектурный).

### 4.3 E2E
`stages/tests/e2e.py` компилирует проходы `walks` из `ui.json` (схема Артёма) в Playwright-спеки:
- маршрут `/<ScreenName>`;
- селекторы — только `testid` виджетов и действий;
- значения из `seed`/`params`;
- неоднозначный шаг — `ContractError`.

Спеки выставляют роль прохода (`localStorage.role`) и подтверждают действия с `confirm: true` (`confirm.ok`). Экраны рендерера несут те же `testid`. Отчёты Playwright — JSON в `reports/e2e/{admin,pwa}.json`.

---

## 5. Хронология сделанного

| Коммит | Что |
|---|---|
| `997723f`…`2cfe263` | Слияние веток: `docs` (`--allow-unrelated-histories`), maxim, timofey, artem-ui-contract, sanya, ivan, studio-frontend |
| `da55d38` | Саня: `attempt` с 1; `dependents()` принимает dict; `gherkin-official`/`lxml`/`PyMuPDF`/`python-docx` в `backend/requirements` (пересобрано через `uv pip compile`) |
| `8846d59` | Платформа: R13 в раннере; `StageOutput.flags`; бюджет; кэш с номером попытки; git `safe.directory` + `.gitignore`; compose (`.env`, `./workspaces`, один builder, `user 0:0`); песочница (`restore`, env, владелец, JUnit, `$$`, `host_workspaces_dir`) |
| `50be5c1` | `scaffold`: `Model.cs`/`Params.cs`; `hooks.in` с `Entity.field` и скалярами; `StageOutput`; починен шаблон (`Microsoft.Extensions.Hosting`, MTP) |
| `ca88d9d` | Новый этап `tests` (JSON-кейсы, раннер `HookCases`); E2E под схему Артёма; JUnit-матчинг; `verify` по платформам; `hooks.json` + `method`/`returns`/`parameters` |
| `d24de66` | Генерация API + API-кейсы; стенд продукта (Dockerfile, compose, smoke, healthcheck); PWA вместо Android; `pack.yaml` → `pack.json`; правки `develop`; `agent.py` |
| `994c79c` | Сессия 2, платформа: вложения к проекту, профиль `tools`, CI платформы, шлюз LLM (один бюджет reasoning; обрезанный JSON — повтор с бо́льшим бюджетом), `reconcile`, суженный `dependents()`, `run_pipeline.py`/`local_chain.py` |
| `f429be1` | Сессия 2, продукт: рендерер экранов, PWA, seed, таймер-переходы в `App.Worker`, CI продукта, отчёты сканеров и E2E, споры → QA, мутации по всем AC, профайлер (WKT, единицы) |
| `d830a08` | Сессия 2: Студия на `/runs` (таймлайн, SSE, ворота, вопросы, артефакты, вложения), README и документы |

### Как решены конфликты слияния
- `contracts/fixtures/tickets/ui.json` — версия Артёма (владелец).
- `contracts/fixtures/{tickets,equipment}/{analysis,app}.json` — версии Сани. Фикстуры Тимофея перенесены в `tests/fixtures/quality/{tickets,equipment}/`.
- `contracts/fixtures/tickets/hooks.json` — версия Ивана.
- `contracts/__init__.py` — версия `main`.
- `agents/developer/config.yaml` — `thinking: false` (R9).

### Что удалено и почему
- `templates/product/pack.yaml` — заменён на `pack.json`, удалён самописный YAML-парсер в `contracts/pack.py`.
- `templates/product/tools/Dockerfile.android` и цель `mobile` — решение R18 (PWA).
- `tests/test_qa_lint_repair.py` — тест старого цикла «модель пишет C# + линтер».
- `App.Generated.Tests/PlaceholderTests.cs` и генератор `PermissionsAndTransitions.cs` — тавтология (таблица сравнивалась сама с собой), заменены `ApiCases`.
- `App.Domain/Params/.gitkeep` — `Params` теперь класс в `Generated/`.

---

## 6. Решения, которые стоит знать команде

1. **JSON для всего, что генерирует конвейер,** включая кейсы тестов и манифест `pack.json`. YAML остаётся только у Docker Compose и GitLab CI.
2. **Модель не пишет тесты кодом.** Кейсы — JSON (из Gherkin кодом, с моделью только как переводчиком строк); C# генерирует код.
3. **Сервисы платформы работают от root** (`user: "0:0"` в `x-backend`). У воркера сборки есть Docker-сокет, это и так root на хосте. Зато у файлов workspace один владелец. Контейнеры песочницы запускаются от владельца workspace с `--cap-drop ALL`.
4. **Образ платформы собирает только `api`** (`pull_policy: build`), воркеры `pull_policy: never`. Это убрало гонку «image already exists».
5. **API продукта:**
   - права — роль × операция из `permissions`; области `own`/`team` **не фильтруются**;
   - guard-хуки и вычисляемые поля вызываются, только если все аргументы хука доступны (команда, запись, `Params`, `time`), иначе в коде остаётся комментарий;
   - миграций нет, `EnsureCreated()`;
   - вход — демо по роли (JWT).
6. **API-тесты на InMemory-БД:** Testcontainers в песочнице без сети невозможны.
7. **Сборка без сети:** песочница делает `restore` с сетью в workspace (`.nuget`, `node_modules`), дальше и тесты, и `docker compose build` (`network: none`) работают офлайн. Пути одинаковые (`/work/...`), поэтому `obj/project.assets.json` валиден внутри Dockerfile.
8. **`dotnet test` в .NET 10** требует MTP:
   - `dotnet test --solution backend/App.sln --no-restore --report-xunit-junit --results-directory /work/reports/junit/backend --ignore-exit-code 8`;
   - фильтр `--filter-trait AC=<id>`;
   - код 8 = «тестов не найдено»; его игнорирует команда, а реальное отсутствие тестов ловят `develop` (по JUnit) и G2.
9. **В JUnit от xunit.v3 нет trait'ов,** поэтому AC сопоставляется по имени класса `AC_xx_Tests` (`stages/quality.py::_mentions`).

---

## 7. Как проверять локально

### Python
```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt pyflakes
```

PostgreSQL для backend-тестов (Docker здесь не было, ставился системный PG 16, `pg_ctl` от пользователя `postgres`, сокет `/tmp`, пользователь `pipeline`/`pipeline` superuser):
```bash
POSTGRES_HOST=localhost PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests
cd backend && POSTGRES_HOST=localhost PYTHONPATH=.:.. ../.venv/bin/alembic upgrade head && POSTGRES_HOST=localhost PYTHONPATH=.:.. ../.venv/bin/python -m unittest discover -s tests
```

Тесты этапов (модули, папки `stages` нет как пакета discovery):
```bash
.venv/bin/python -m unittest stages.analysis.tests.test_analysis_stage stages.analysis.tests.test_inputs stages.spec.tests.test_contracts stages.spec.tests.test_eval stages.spec.tests.test_spec_stage gates.tests.test_gates stages.scaffold.tests.test_generate stages.develop.tests.test_ladder contracts.tests.test_hooks_pack
```

Smoke шаблона:
```bash
cd templates/product/infra && ../../../.venv/bin/python -m unittest test_smoke
```

На коммите `d24de66` всё зелёное: root — 92 теста, backend — 28, остальные наборы OK.

**Важно:** корневые тесты требуют `PYTHONPATH=backend`. Без него тест манифеста тестов не находит `app`.

### .NET (генерируемый продукт)
- **SDK:** `apt-get install dotnet-sdk-10.0` (Ubuntu 24.04). Скрипт `dot.net/v1/dotnet-install.sh` за прокси не работает (`builds.dotnet.microsoft.com` закрыт), а **nuget.org открыт**.
- **Сгенерировать продукт и прогнать тесты:**
```bash
mkdir -p /tmp/gen/spec && cp contracts/fixtures/tickets/{app,ui}.json /tmp/gen/spec/
.venv/bin/python -c "from pathlib import Path; from contracts.stage import StageInput; from stages.scaffold import execute; print(execute(StageInput(run_id='x',stage='scaffold',attempt=1,requirements='r',artifacts={'app':'spec/app.json','ui':'spec/ui.json'}), Path('/tmp/gen'), None, None).summary)"
cd /tmp/gen/product/backend && dotnet build App.sln && dotnet test --solution App.sln --no-build
```
- **Admin-web:** `cd templates/product/admin-web && npm ci && npm run build && npx jest --ci` — проходит. npm registry за прокси открыт.

### Фейковый сквозной прогон платформы
Проверялся на ветке Максима **до** слияния; на ветке интеграции **ещё не перепроверен** (раздел 8). Шаги:
1. Запустить uvicorn `app.main:app` и celery worker с `-Q llm,build,io,celery`, окружение `PIPELINE_FAKE_STAGES=1 POSTGRES_HOST=localhost WORKSPACES_DIR=<dir>`.
2. `POST /api/projects`.
3. `POST /api/projects/{id}/runs {"autonomy":"A2"}`.
4. Через ~20 с `GET /api/runs/{id}` — ожидается 8 этапов `succeeded`, прогон `partial`.

### Langfuse: где модель крутится в циклах
`docker compose --profile langfuse up -d`, UI — http://localhost:3000. Вход — `LANGFUSE_INIT_USER_EMAIL` и `LANGFUSE_INIT_USER_PASSWORD` из `.env`. При первом старте Langfuse создаёт по `.env` организацию, проект `pipeline` и ключи. Шаблон — `.env.example`. Без `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY` или `LANGFUSE_SECRET_KEY` трассы не отправляются.

Отправку делает `backend/app/tracing.py`: фоновый поток, OTLP/HTTP JSON. Схема — по `architecture-v2.md`:
- **trace** — прогон;
- **span** `<этап> #<попытка>` — этап;
- **generation** — одна попытка вызова модели, с промптом, ответом и токенами;
- **оценки (scores)** на span этапа — итоги гейтов.

Как читать циклы — по уровню generation в дереве трассы:
- **WARNING `schema_error`** — ремонт формата, следующая попытка получает «Исправь формат ответа…»;
- **WARNING `length`** — ответ обрезан: для JSON бюджет растёт вдвое, для текста — продолжение;
- **ERROR `provider_error`** — ретрай после 429/5xx.

Повторные span одного этапа (`spec #2`, `#3`) — это перезапуски. Фильтр по уровню WARNING показывает самые «дорогие» места.

### Чего не было в среде
Docker-демона нет. Поэтому **не проверены**:
- `docker compose up` платформы;
- песочница с образами `rwb/tool-*`;
- сборка образов продукта с `network: none`;
- подъём стенда, smoke и E2E.

Офлайн-публикацию (`restore` в `/work`, затем `publish --no-restore`) тоже не проверил: команду с `rm -rf /work` заблокировала защита.

---

## 8. Что дальше (по приоритету)

### Статус после сессии 2 (локальный Docker)
- **Сделано:** P0 1–4 (кроме PR — п. 5); P1 6, 7, 9, 11, 12; P2 13, 14, 15, 16, 18, 19 (`reconcile`, README), 20, 21.
- **Проверено на Docker:** `docker compose up` платформы и `doctor`; образы инструментов; песочница на `tickets`: backend build/test 22/22, `dotnet format`, gitleaks JSON и trivy SARIF; admin и PWA собираются офлайн, jest зелёный; Студия — 40/40 E2E с axe.
- **Перепрогон цепочки `tickets` в Docker на шаблонах сессии 2 (до сессии 3; без модели, хуки — заглушки):** admin и PWA — restore/build/jest ok; scan ok; стенд с `mobile` поднялся, smoke ok. E2E admin: 3 прошли (заголовок, AC-01, AC-02); AC-06/07 — таймаут на клике; AC-08 — нет `dashboard.open`; AC-09 — нет `alerts.status` (объясняется находкой сессии 3 про `OverdueTickets`). E2E PWA: смоук ищет `role=banner`, а у мобильной оболочки его нет; AC-10 — нет строк `mobile-queue.row`. На шаблонах сессии 3 стоит перепрогнать.
- **Не дошло до конца на момент пуша:** полный перепрогон цепочки `tickets` со стендом (admin+mobile), smoke и E2E на новых шаблонах; реальный прогон кейса №1 на модели (первые две попытки упали на analysis: HTTP 400 по reasoning и обрезка JSON в `acceptance`, оба исправлены, третья попытка шла во время пуша). Таймер-переходы компилируются, но на живой PostgreSQL не проверены.
- **Открыто после сессии 2:** P1 8 (API-сценарии для AC без хуков), P1 10 (outbox/SSE в продукте), P2 17 (eval Сани на `harness/llm.py`), P2 19 (`input_hash` для пропуска), PR в `main`, закрытие #2/#4, итог в #3; в Студии нет E2E на загрузку вложений.

### Статус после сессии 3 (без Docker: .NET 10, Node, PostgreSQL 16 локально)
- **P1 8 сделано — API-сценарии AC** (`stages/tests/scenarios.py`, раннер `App.Acceptance.Tests/ScenarioCases.cs`):
  - AC, связанный в `app.json` с командой (по `traces` или через историю с той же ролью), получает сценарий: создать запись ролью с `create`, довести командами до нужного состояния (BFS по переходам), выполнить команду, проверить код, новое состояние и событие в `/api/events`;
  - AC без команды, если роль истории может создать сущность — создать и прочитать;
  - модель не участвует; кейсы — `cases/scenarios/<AC>.json`, класс на AC с `Trait("AC")`;
  - сценарии нейтральны для red-proof (проверяют сгенерированный код), если у AC нет кейсов хуков;
  - на `tickets` покрыты AC-01, 02, 03, 08; AC-07 (только таймер и уведомление) — нет.
- **P1 10 сделано — outbox и SSE (R17):**
  - `DomainEvent` (`domain_events`) и `Notification` (`notifications`) в `App.Infrastructure/Outbox`, `DomainEvents.Raise` в той же транзакции;
  - события `<Entity>Created` и по каждому переходу (команды и таймеры) с именами из `stages.ui.appview.derived_event` — совпадают с `live` в `ui.json`;
  - `app.json notifications` → `Generated/Notifications.cs` (текст с полями записи, адресат — роль);
  - API: `GET /api/events?after=`, `GET /api/events/stream` (SSE, `Last-Event-ID`/`after`), `GET /api/notifications?after=`; роль видит события сущностей, которые может читать; PostgreSQL — триггер `NOTIFY domain_events` + `LISTEN`, другие провайдеры — опрос раз в секунду;
  - фронт: `screens/events.ts` (`LiveEvents`) — один fetch-поток с `Authorization` и переподключением; `live`-экраны перезагружаются по своим событиям (опрос 60 с как страховка); счётчик уведомлений в шапке админки и PWA, браузерные уведомления.
- **Проверено на живом PostgreSQL** (сгенерированный `tickets`, `dotnet` без Docker): схема, seed, вход по ролям (неизвестная роль 401), права 403, переход и 409, таймер воркера `in_progress → overdue`, `--healthcheck`, `infra/smoke.py` (все роли), события в SSE за < 2 с через NOTIFY, уведомление диспетчеру с текстом, инженеру — пусто. В браузере (Playwright + `ng serve`): строка ушла из списка за 76 мс после `TakeTicket` без перезагрузки, после таймера счётчик уведомлений = 4.
- **Найдено и исправлено:** seed загружался без вычисляемых полей (`due_at` = null, таймер его не трогал) — `SeedData.Load` вызывает `GeneratedEndpoints.Compute`.
- **Найдено:** канонический `contracts/fixtures/tickets/ui.json` (Артём) ссылается на запрос `OverdueTickets`, которого нет в каноническом `app.json` (Саня), поэтому экран `Alerts` пуст — исправлено во второй части сессии, см. ниже.

### Статус после сессии 3, часть 2
- **LLM из env** (`harness/llm_config.py`): `LLM_BASE_URL` (по умолчанию OpenRouter), `LLM_API_KEY` (запасные `OPENROUTER_API_KEY`, `OPENAI_API_KEY`), `LLM_MODEL`, `LLM_PROVIDER` (пин провайдера только для OpenRouter, пусто — не пинить). Читают `harness/llm.py`, `harness/agent.py`, `doctor`, `compose.yaml`; локальный vLLM без ключа работает. Ключ — только в `.env` (в `.gitignore`).
- **P2 17 сделано:** eval Сани идёт через `harness/llm.py` (`LocalLLM` поверх `Gateway`) и `harness/fakes.py` (`FakeLLM.recorded`); `stages/spec/eval_gateway.py` удалён. `HTTPTransport` отказывает, если провайдер подменил модель.
- **P2 19 сделано — переиспользование по `input_hash`** (`backend/app/runner.py::_reuse`):
  - «Перезапустить шаг» теперь работает и для успешного шага (Студия кнопку уже показывала, бэкенд отказывал); сам шаг выполняется заново;
  - шаги ниже берут результат прошлой попытки, если совпали `input_hash` и дерево workspace, с которого та попытка стартовала; копируются артефакты и результаты ворот, тесты заново принимаются в `test_hashes`, событие `stage.reused`;
  - `input_hash` теперь учитывает и код `stages/`, `gates/`, `harness/`; `report`, шаги с вопросами и шаги, ждущие человека (A0, A1 на spec), не переиспользуются;
  - флаги нижних шагов при перезапуске не стираются, их заменяет следующий прогон этого шага.
- **Фикстуры `tickets` сведены:** канонический `ui.json` проходит G1.5 против канонических `app.json` и `analysis.json` (US-01..05). В `app.json` добавлены `OverdueTickets`, `ResolvedTickets`, `MyTickets` для сотрудника и две записи сида. Прежний `ui.json` переехал к своим подменам в `tests/fixtures/ui/tickets/` — на них тестируется логика G1.5.
  - **Не выражается:** среднее время решения (AC-09). Нужно вычисляемое поле с хуком (и правило BR в анализе) или KPI по разности двух полей; пока KPI считает решённые заявки. Решение за Саней и Артёмом.
  - `contracts/fixtures/equipment/ui.json` не проходит схему `UiSpec` (старый формат: `route`, нет `pattern`).
  - У scaffold свои копии фикстур в `stages/scaffold/tests/fixtures/` — третья версия `tickets`.
- **E2E продукта на локальном стенде** (сгенерированный `tickets`, PostgreSQL, `ng serve`, Playwright; хук `ResolutionRequired` реализован так, как сделал бы develop): admin 6/6, PWA 2/2. Разобраны падения из прогона Максима:
  - строка списка выбиралась по индексу сида, а запрос фильтрует и сортирует — теперь по тексту записи;
  - переход по `nav` открывал голый URL и терял `?id=` — теперь клик по ссылке экрана;
  - у оболочек не было `<header>`, смоук PWA не находил `banner`;
  - отказ guard-хука показывал имя хука — теперь текст `error.<Hook>` из `copy`; команда отправляет пустые текстовые поля, чтобы решал валидатор, а не привязка модели (раньше 400);
  - ввод команды не попадал в запись (`resolution` терялся) — поля ввода с именем и типом поля сущности записываются в неё;
  - числовая ссылка в сиде за пределами строк давала висячий id — теперь ошибка контракта; в каноническом сиде ссылки были с единицы, исправлено.
  - **Осталось:** демо-вход — один пользователь (`current_user` = первая запись `Employee` для всех ролей); `TakeTicket` не назначает исполнителя (AC-02 «исполнителем назначен текущий инженер» — забота develop/custom).
- **E2E Студии на вложения** (`frontend/e2e/attachments.spec.ts`): список, загрузка нескольких файлов телом запроса, отказ по формату. Студия 42/42.
- **Кейс №1 на модели** отсюда не прогнать: прокси среды закрывает `openrouter.ai`. Максим гоняет его у себя (см. `db0875d`).
- **Открыто:** PR в `main`, закрытие #2/#4, итог в #3; полный прогон стенда в Docker на новых шаблонах; AC-09; AC-07 без API-сценария.

### Реальный прогон кейса №1 (qwen3.8-27b, OpenRouter/DeepInfra, A2), 31.10.2026
Прогон `d1f99bfd`: 50 вызовов модели, токены вход/выход 161 673 / 147 021 (reasoning 78 813), около 61 мин модели.
- `analysis` ✔ G0: 35 требований, 15 правил, 30 AC.
- `spec` — G1: 103 ошибки, ремонт ничего не изменил. 67 × `REF_UNRESOLVED` (в `owner` имя сущности вместо поля, переходы на несуществующие команды), `permissions` пуст, роли `ROLE-01/02`. **Главный узкий участок: ремонт spec по находкам G1 на этой модели не работает (зона Сани).**
- `ui` падал дважды на контракте (camelCase-команды из `app.json`), исправлено (`db0875d`, `6f187e3`): 5 экранов-форм, без списков из-за пустых прав.
- `tests` падал на поиске `pack.json` в образе, исправлено (`ea45a53`, заодно `input_hash` в образе хешировал пустоту).
- `verify`: backend, admin и PWA не собрались на слабой спецификации. Исправлено в scaffold (`7b847b3`): несуществующие типы входов хуков, enum с именем сущности, `null` в `model.ts`, пустые маршруты PWA. Проверено перегенерацией из настоящих `app.json`/`ui.json` прогона: все три собираются. Целиком прогон заново не запускался.
- `report` зависал на 9p (раздел 9).

### P0 — до сдачи
1. **Сквозная проверка на ветке интеграции:** фейковый прогон через API и Celery (раздел 7). Затем прогон с реальными этапами и `FakeLLM` на `tickets` через `run_stage_locally`: `analysis → spec → ui → scaffold → tests`. Дальше песочница нужна настоящая. Recorded-ответы для `analysis`/`spec` есть в `stages/*/tests/fixtures/*-responses.json`, через `stages/spec/eval.py::evaluate`.
2. **Сборка образов инструментов.** Добавить в `compose.yaml` сервисы с `profiles: [tools]` и `build` из `templates/product/tools/Dockerfile.*`, `image: rwb/tool-dotnet:10`, `rwb/tool-node:22`, `rwb/tool-security:1`. В README — `docker compose --profile tools build`. `harness/doctor.py` уже подсказывает эту команду.
3. **Проверка на машине с Docker:**
   - `docker compose up --build` платформы (обратить внимание на `pull_policy: never` у воркеров: образ должен собраться раньше их создания);
   - песочница: `restore`, `build`, `test` на продукте `tickets`;
   - `docker compose -f infra/docker-compose.yml up -d --build --wait` стенда;
   - smoke.
4. **CI продукта** (`templates/product/.gitlab-ci.yml`) переписать:
   - команды из `pack.json`: `restore`, `build --no-restore`, `test` с MTP-флагами;
   - `npm ci`/`build`/`jest`;
   - `package`/`deploy` — `docker compose -f infra/docker-compose.yml up -d --build --wait` (нужен раннер с Docker);
   - `e2e` после `deploy`;
   - образы инструментов должны быть доступны раннеру (registry или локальные).

   Пункт ТЗ — «GitLab CI/CD 19.4.2». Платформа тоже должна жить в локальном GitLab; своего CI у платформы нет, нужен хотя бы `unittest`.
5. **PR в `main`** из `claude/review-docs-branches-48sc58`. В описании — итог из разделов 5 и 6 и список нерешённого. После — комментарий в issue #3 со статусами.

### P1 — качество и баллы
6. **Экраны админки из `ui.json`.** Генерировать компоненты `list`/`detail`/`form` с `data-testid` из `ui.json` на Angular Material (каталог виджетов уже есть в `templates/product/admin-web/src/app/ui`). Без этого E2E и балл «продукт и интерфейс» не набираются.
7. **PWA `mobile-web/`.** Добавить шаблон: Angular + service worker, Geolocation и Notification API. Для кейса №1 водитель — mobile. Сейчас цель `pwa` в `pack.json` есть, но шаблона нет, и `verify` честно ставит «не собрано».
8. **API-сценарии для критериев без хуков** (CRUD, переходы, уведомления). Детерминированно из Gherkin + `app.json` (`seed`, команды, переходы) или через structured JSON от модели. Формат — как `cases/api.json`, но с шагами.
9. **Планировщик переходов `timer`/`schedule`** (например, `expire` → `overdue`) в `App.Worker`: опрос по `TimeProvider`, вызов guard-хука. Сейчас такие переходы не исполняются.
10. **События и уведомления** (outbox `domain_events`, SSE): по v2 §10.1 модули `events`/`notify`. В генераторе их нет.
11. **Студия на `/runs`.** Сейчас `frontend` работает через старый `/api/projects/{id}/jobs` (один агент, история в `localStorage`), см. `frontend/CONTRACT.md`. Нужно:
    - таймлайн из `RunRead.stages`, гейты из `StageRunRead.gate`;
    - SSE `/events/stream`;
    - артефакты `/artifacts` и `/files`, кнопки `retry`, `answers`, `decision`;
    - быстро: статусы `pending`, `waiting_human`, `stale` в `frontend/src/app/core/pipeline/status.ts` и подсказку `worker-llm`/`worker-build` вместо `worker`.
12. **Артём, S10:** `derived_event('Ticket','take_overdue')` даёт `TicketTakenOverdue`, а `appview.event_exists` его не признаёт. Нужно согласовать соглашение об именах событий с генератором.

### P2 — долги из ревью (issue #3)
13. **S3 `dependents()` слишком широкий** (`contracts/app.py`): один хук помечает почти всю спецификацию. Ограничить транзитивность.
14. **C11 споры по тестам:** `develop` собирает `// DISPUTE:` в `develop.json`, но не вызывает `stages/tests/dispute.resolve`. Раннер тоже. Связать или упростить.
15. **Мутации** (`stages/verify/mutations.py`) гоняют только первый AC хука. Мутанты на C# работают, а для data-driven кейсов можно мутировать `Params`.
16. **Саня, S7:** профайлер (`stages/analysis/profiling.py`) не разбирает WKT (типы геометрий, линии vs полигоны) и не выводит единицы (копейки, минуты суток). `externalZoneId` ошибочно помечен как `int`.
17. **Саня, S8/S9:**
    - около 106 тыс. строк логов eval (`stages/spec/delivery/*`, `EVAL*.json`, `eval-history/`) — вынести из репо;
    - ~~свои шлюз (`eval_gateway.py`) и заглушки (`stages/analysis/testing.py`) — перейти на `harness/llm.py` и `harness/fakes.py`~~ — сделано в сессии 3;
    - в `stages/spec/README.md` личный путь `/home/haus/...`.
18. **Вложения к прогону** (загрузка в Студии и API `/projects/{id}/attachments` есть, E2E — сессия 3): API прогонов не принимает файлы, `StageInput.attachments` всегда пуст. Нужна загрузка в `input/`, чтобы приложить `spb.json`.
19. **Метрики:**
    - `README.md` основной всё ещё упоминает `docker compose logs worker`;
    - ~~`input_hash` считается, но для пропуска не используется~~ — сделано в сессии 3;
    - `reconcile` переотправляет `queued` раз в 10 с бесконечно, если воркер очереди не запущен.
20. **Документация:**
    - пометить `docs/architecture-overview.md` устаревшим;
    - в `architecture-v2.md` заменить `*.yaml` на `*.json`;
    - в `docs/tasks/*.md` заменить `pack.yaml` на `pack.json`, цель `mobile` на `pwa`, описать новый подход к тестам (раздел 4);
    - обновить `stages/QUALITY.md` и `frontend/CONTRACT.md`;
    - README: запуск, профиль `tools`, стенд, отступления от стека ТЗ.
21. **Линтер:** `pyflakes` даёт мелочи (неиспользуемые импорты в `backend/app/models.py`, `stages/report/documents.py`, `gates/g5_docs.py`, f-string без плейсхолдеров в `gates/g15_ui.py`). Не баги.

---

## 9. Подводные камни среды и процесса
- **Docker Desktop на Windows, bind mount `./workspaces`:** процесс воркера дважды намертво завис в `p9_client_rpc` (состояние D, ввод-вывод стоит) на шаге `report` сразу после `verify`, и один раз так же в `scripts/local_chain.py`. Помогает только `docker compose restart worker-llm` и `python -m harness recover <run> --worker-stopped`. Обход: держать репозиторий в файловой системе WSL (ext4, например `~/rwb-ai-hack` внутри WSL) и запускать `docker compose` оттуда, а не из `C:\Users\...`.
- **Бюджет минут считается по часам с момента старта прогона**, включая простой между ручными перезапусками шагов. После долгой отладки шаги получают `BudgetExceeded` без вызовов модели (так `develop` оставил 23 заглушки).
- **Прокси:**
  - открыты: GitHub, nuget.org, npm registry, PyPI, apt;
  - закрыты: `builds.dotnet.microsoft.com`, отсюда SDK из apt.
- **Защита Claude Code** блокирует `rm -rf` по корневым и неразрешимым путям (`/work`, `cd dir && rm -rf *`). Удалять только по абсолютным путям во временных каталогах.
- **Права на scratchpad:** однажды сбросились, и PostgreSQL упал с `Permission denied`. Данные PG держите в `/var/lib/postgresql/...`.
- **Воркер сессии перезапускался.** Незакоммиченное выжило, но коммитьте и пушьте чаще.
- **Коммиты:**
  - сообщения на английском (так принято с `ca66f81`), в теле — что и почему;
  - в конце строки `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` и `Claude-Session: https://claude.ai/code/session_01BVMh1mqEFn4QysVPTvv8Nu` (для сессий Claude);
  - пушить только в `claude/review-docs-branches-48sc58`: `git push -u origin claude/review-docs-branches-48sc58`.
- **Комментарии на GitHub** от агента заканчиваются подписью `_Generated by [Claude Code](https://claude.ai/code)_`.
- **Стиль кода:** как в окружающем файле. Код Тимофея плотный (`;`, однострочники); новый код в его модулях я писал в обычном стиле. Если будете переписывать — приводите к общему.
