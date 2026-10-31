# Эксплуатация

Запуск: `docker compose -f infra/docker-compose.yml up -d --wait`.

Статусы сервисов: `docker compose -f infra/docker-compose.yml ps`.
Логи: `docker compose -f infra/docker-compose.yml logs`.

При ошибке health проверьте подключение БД, миграции и переменные окружения продукта. Секреты платформы в продукт не передаются.
