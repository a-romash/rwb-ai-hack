# Поток — ИИ-конвейер разработки RWB

Аналитик описывает бизнес-требования и прикладывает данные. Конвейер из восьми шагов превращает их в работающий продукт: ASP.NET Core 10 API, админку на Angular 20.1.6, PWA для мобильных ролей, стенд в Docker Compose, тесты, CI GitLab и документацию. Студия показывает каждый шаг, ворота качества с находками, вопросы аналитику и артефакты.

```text
analysis ─G0→ spec ─G1→ ui ─G1.5→ scaffold → tests ─G2→ develop → verify ─G3,G4→ report ─G5
```

Модель пишет только то, что нельзя вывести детерминированно: разбор требований, спецификацию, тексты экранов и тела хуков бизнес-правил. Всё остальное генерирует код: сущности, API, права, экраны, тесты из Gherkin, CI, стенд. Ворота проверяют каждый артефакт кодом, а не моделью. Подробно — в [docs/architecture-v2.md](docs/architecture-v2.md), состояние работ — в [docs/HANDOFF.md](docs/HANDOFF.md).

## Запуск

Нужны Docker с Compose v2. На Windows подходит Docker Desktop.

```sh
cp .env.example .env                      # LLM_API_KEY=... (и при необходимости LLM_BASE_URL, LLM_MODEL) для реального прогона
docker compose --profile tools build      # образы песочницы: rwb/tool-dotnet:10, rwb/tool-node:22, rwb/tool-security:1
docker compose up --build -d
```

Студия: [http://localhost:8080](http://localhost:8080), Swagger: [http://localhost:8080/api/docs](http://localhost:8080/api/docs).

Образы инструментов собираются один раз. Песочница запускает в них сборку, тесты, сканеры и E2E продукта. В `rwb/tool-security` вшита база уязвимостей trivy, поэтому сканирование идёт без сети. Чтобы обновить базу, пересоберите образ.

Сервисы платформы:

| Сервис | Что делает |
|---|---|
| `api` | FastAPI: проекты, прогоны, SSE событий, артефакты, метрики |
| `worker-llm`, `worker-build`, `worker-io` | Celery на брокере PostgreSQL; `worker-build` управляет Docker через сокет |
| `frontend` | Студия: Angular 20.1.6, Taiga UI, nginx |
| `postgres` | состояние прогонов и очередь |

`docker compose down` останавливает платформу и сохраняет данные. `docker compose down -v` удаляет том PostgreSQL. Рабочие каталоги прогонов лежат в `./workspaces`: каждый прогон — отдельный git-репозиторий с историей шагов.

## Прогон

В Студии создайте проект, вставьте требования и на вкладке «Конвейер» нажмите «Запустить конвейер». Режимы автономности:

- **A2** — человек не участвует, на вопросы отвечают значения по умолчанию;
- **A1** — человек отвечает на вопросы и замораживает спецификацию;
- **A0** — человек принимает каждые ворота.

Таймлайн обновляется по SSE. У каждого шага видны статус, попытка, итог и кнопка перезапуска. У ворот видны находки и, в режимах A0 и A1, кнопки решения.

Из терминала то же самое, с вложением данных кейса:

```sh
python scripts/run_pipeline.py --requirements stages/spec/eval/case1/requirements.md --attach spb.json --autonomy A2
```

Скрипт создаёт проект и загружает вложения: `POST /api/projects/{id}/attachments?name=spb.json`, тело — сам файл. Затем он запускает прогон, печатает статусы шагов и вердикты ворот, а в конце — расход токенов. Вложения попадают в `input/` прогона, их разбирает шаг `analysis`: профиль JSON, CSV и GeoJSON, текст DOCX и PDF.

Проверка платформы без модели: `PIPELINE_FAKE_STAGES=1 docker compose up -d`. Фейковые шаги проходят цепочку, прогон завершается `partial`.

## Что получается на выходе

`workspaces/<project>/runs/<run>/product/` — готовый репозиторий продукта:

- `backend/` — ASP.NET Core 10: Minimal API с правами по ролям, EF Core на PostgreSQL/PostGIS, хуки бизнес-правил в `App.Domain/Hooks`, тесты xunit.v3 на Microsoft.Testing.Platform. Каждый хук проверяют кейсы из примеров Gherkin, а права — матрица ролей.
- `admin-web/` — Angular 20.1.6 и Material. Экраны строятся из `ui.json` одним рендерером: списки, карточки, формы и дашборды с `data-testid`. Есть демо-вход по роли.
- `mobile-web/` — PWA на том же рендерере: service worker, офлайн-кэш, геолокация, локальные уведомления, нижнее меню.
- `infra/docker-compose.yml` — стенд: postgis, wiremock, backend, worker, admin, mobile. Образы собираются без сети из восстановленных зависимостей. `infra/smoke.py` входит под каждой ролью.
- `.gitlab-ci.yml` — CI продукта: lint, build, test, security, deploy, smoke, E2E, docs. Команды те же, что в `pack.json`.
- `docs/` и `mkdocs.yml` — паспорт, роли, трассировка критериев и эксплуатация.

## Отступления от стека ТЗ

| ТЗ | Сделано | Почему |
|---|---|---|
| Kotlin Android | PWA `mobile-web` | Собирается и проверяется E2E в той же песочнице. Нужные API — геолокация, уведомления, офлайн — есть в браузере (R18). |
| Kafka | события через PostgreSQL | Один брокер на стенд; outbox и SSE (R17) |
| Angular 20.1.6 | как в ТЗ | У версии есть HIGH CVE. Trivy пропускает только их по политике `infra/trivy-pinned-stack.rego`, остальное блокирует. |

## Проверка

```sh
# все Python-наборы: корень, backend, этапы, ворота, смоук стенда; отдельная PostgreSQL, не база платформы
docker network create rwbtest
docker run -d --rm --name rwbtest-pg --network rwbtest -e POSTGRES_USER=pipeline -e POSTGRES_PASSWORD=pipeline \
  -e POSTGRES_DB=pipeline postgres:17.9-bookworm
docker run --rm --network rwbtest -v "$PWD":/src -w /src -e POSTGRES_HOST=rwbtest-pg rwb-pipeline-backend:local \
  sh scripts/test-all.sh
# Студия: сценарии с подменой API и axe
cd frontend && npm ci && npm run e2e:install && npm run e2e
```

Цепочка продукта на фикстуре без модели и с настоящей песочницей. Она проходит scaffold → tests → develop → verify → report: собирает, тестирует, сканирует, поднимает стенд, выполняет smoke и E2E.

```sh
MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -v ./scripts:/app/scripts worker-build \
  python scripts/local_chain.py --fixture tickets
```

## CI

- `.gitlab-ci.yml` — CI платформы: pyflakes, все Python-наборы с PostgreSQL, сборка и E2E Студии, сборка образов, gitleaks и trivy.
- `templates/product/.gitlab-ci.yml` — CI каждого сгенерированного продукта.

Обоим нужен раннер с Docker executor. Для deploy, smoke и E2E продукта раннер должен монтировать `/var/run/docker.sock`. Образы `rwb/tool-*` собираются на хосте раннера командой `docker compose --profile tools build`.

## Восстановление

Остановите воркеры и выполните `docker compose exec api python -m harness recover <run_id> --worker-stopped`. Упавший шаг повторяется кнопкой в Студии или через `POST /api/runs/{run_id}/stages/{key}/retry`. Готовность окружения проверяет `docker compose exec api python -m harness doctor`.

`worker-build` получает доступ к Docker daemon. Запускайте его только на доверенном изолированном хосте. Песочница отклоняет compose-файлы с привилегиями, монтированиями хоста и подстановкой переменных.
