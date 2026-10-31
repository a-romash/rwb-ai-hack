#!/bin/sh
# Start the generated product from a clean clone; dependencies are fetched inside the image builds.
set -e
cd "$(dirname "$0")"
PROJECT=${PROJECT:-parking}
compose() { docker compose -p "$PROJECT" -f infra/docker-compose.yml -f infra/docker-compose.online.yml "$@"; }

compose up -d --build --wait
echo
echo "Админка (роль ROLE-02):  http://$(compose port admin 80)"
echo "Мобилка (роль ROLE-01):  http://$(compose port mobile 80)"
echo "API:                     http://$(compose port backend 8080)"
echo "Остановить: docker compose -p $PROJECT -f infra/docker-compose.yml down -v"
