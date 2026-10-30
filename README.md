# Поток — менеджер ИИ-пайплайна

База универсального конвейера разработки для хакатона. Менеджер создаёт проект, описывает бизнес-требования и видит десять этапов разработки. Исполнение этапов и ИИ-агенты ещё не подключены.

## Запуск

Нужны Docker и Docker Compose. В корне проекта:

```sh
docker compose up --build -d
```

Интерфейс: [http://localhost:8080](http://localhost:8080). Swagger: [http://localhost:8080/api/docs](http://localhost:8080/api/docs). При первом запуске Compose скачает образы и зависимости. Дождитесь готовности API: `docker compose ps`.

Чтобы изменить параметры, скопируйте `.env.example` в `.env` и отредактируйте значения до первого запуска. Порт интерфейса — `FRONTEND_PORT`; PostgreSQL не публикуется наружу. Учётные данные по умолчанию предназначены для локальной разработки. При изменении пароля на уже созданном томе необходимо обновить его и в самой базе.

Остановка без удаления данных: `docker compose down`. Данные PostgreSQL и очередь сохраняются в именованном томе `postgres_data`. Команда `docker compose down -v` удаляет и том, и все проекты.

## Устройство

- `frontend/` — Angular 20.1.6 и Taiga UI 5, nginx раздаёт приложение и проксирует `/api`.
- `backend/app/` — FastAPI, модели SQLAlchemy и Celery. `projects.py` содержит список этапов, `tasks.py` — техническую задачу и место для будущих обработчиков.
- `backend/alembic/` — миграции. API применяет миграции и создаёт таблицы очереди перед запуском worker.
- `postgres` — PostgreSQL 17.9, хранит проекты, сообщения Celery через Kombu SQLAlchemy transport и результаты технических задач. Отдельный брокер не используется; worker запущен в одном процессе.

При следующем изменении моделей создайте миграцию в `backend/alembic/versions/`; существующие миграции повторно не редактируют. Применение вручную: `docker compose exec api alembic upgrade head`.

## Проверка

```sh
docker compose exec api python -m unittest discover -s tests -v
docker compose exec api python -m app.tasks
```

Вторая команда отправляет задачу в очередь PostgreSQL, ждёт ответа worker и выводит `Queue check passed` с идентификатором задачи. Для диагностики: `docker compose logs worker-llm worker-build worker-io`.

Для локальной разработки интерфейса после запуска Compose: `cd frontend && npm ci && npm start`. Dev-сервер проксирует `/api` на Compose по адресу `localhost:8080`.

Сценарии интерфейса и проверка доступности (бэкенд не нужен, API подменяется): `cd frontend && npm run e2e:install && npm run e2e`. Подробности о Студии — в [frontend/README.md](frontend/README.md).

## Границы текущей версии

Это локальный однопользовательский прототип без авторизации. Кнопки запуска и исполнения этапов намеренно отсутствуют. LLM, генерация артефактов, конструктор пайплайнов и интеграция с GitLab добавляются отдельно. SQLAlchemy transport подходит для демонстрации с одним worker; при увеличении нагрузки нужно проверить требования к доставке и заменить транспорт при необходимости.

## Контракты этапов и фейки (M0)

Общие интерфейсы, локальная проверка этапа и примеры API: [contracts/README.md](contracts/README.md).
Запуск фейковой цепочки без БД и модели: `python -m harness.fake_stages`.
Это поставка для независимой разработки этапов; HTTP API прогонов пока не реализован.

## Прогоны пайплайна

Платформа хранит состояние прогонов в PostgreSQL и использует его же как брокер Celery. Запуск: `docker compose up --build`. Рабочие каталоги сохраняются в `./workspaces`, PostgreSQL — в Docker volume. При старте API выполняется `alembic upgrade head`; миграцию вручную можно выполнить командой `docker compose exec api alembic upgrade head`.

Для проверки без этапов команды и без модели запустите с `PIPELINE_FAKE_STAGES=1 docker compose up --build`. Создайте проект через `/api/projects`, затем прогон через `POST /api/projects/{project_id}/runs` с телом `{"autonomy":"A2","budget":{"tokens":1500000,"minutes":60}}`. Состояние и результаты доступны через `/api/runs/{run_id}`, `/artifacts`, `/events` и `/metrics`, документация API — `/api/docs`. Фейковый прогон с отсутствующими гейтами отмечается `partial`: реальная проверка не выполнена.

Для реального прогона подключите этапы коллег в `stages/`, проверки в `gates/`, доверенный `templates/product/pack.yaml` и настройте `OPENROUTER_API_KEY`. Для вызовов Docker build-воркер использует смонтированный сокет и путь рабочего каталога на хосте. `python -m harness doctor` проверяет готовность окружения.

После аварии сначала остановите все воркеры, затем выполните `docker compose exec api python -m harness recover <run_id> --worker-stopped`; повтор упавшего этапа — `POST /api/runs/{run_id}/stages/{key}/retry`. Не запускайте восстановление при работающем воркере: автоматического отзыва выполнения нет.

Проверка Python из корня: `PYTHONPATH=backend python -m unittest discover -s tests -v`. Build-воркер имеет доступ к Docker daemon и должен работать на доверенном изолированном хосте.
