#!/bin/sh
# Start the generated product locally. Its images build offline (network: none), so dependencies
# are restored first into .nuget and node_modules, in public SDK containers.
set -e
cd "$(dirname "$0")"
ROOT=$(pwd -W 2>/dev/null || pwd)  # Git Bash on Windows needs C:/... for docker -v
PROJECT=${PROJECT:-parking}
export MSYS_NO_PATHCONV=1  # Git Bash on Windows: keep container paths as written

docker run --rm -v "$ROOT:/work" -w /work/backend -e NUGET_PACKAGES=/work/.nuget/packages \
  mcr.microsoft.com/dotnet/sdk:10.0 dotnet restore App.sln
for app in admin-web mobile-web; do
  docker run --rm -v "$ROOT:/work" -w "/work/$app" -e NPM_CONFIG_CACHE=/work/.npm \
    node:22-bookworm npm ci --no-audit --no-fund
done

docker compose -p "$PROJECT" -f infra/docker-compose.yml up -d --build --wait
echo
echo "Админка (роль ROLE-02):  http://$(docker compose -p "$PROJECT" -f infra/docker-compose.yml port admin 80)"
echo "Мобилка (роль ROLE-01):  http://$(docker compose -p "$PROJECT" -f infra/docker-compose.yml port mobile 80)"
echo "API:                     http://$(docker compose -p "$PROJECT" -f infra/docker-compose.yml port backend 8080)"
echo "Остановить: docker compose -p $PROJECT -f infra/docker-compose.yml down -v"
