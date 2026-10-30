FROM docker:27-cli AS docker_cli
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker_cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home app
COPY --chown=app:app backend/ /app/
COPY --chown=app:app gates/ /app/gates/
COPY --chown=app:app contracts/ /app/contracts/
COPY --chown=app:app harness/ /app/harness/
COPY --chown=app:app agents/ /app/agents/
COPY --chown=app:app stages/ /app/stages/
COPY --chown=app:app templates/ /app/templates/
COPY --chown=app:app infra/prototype/ /app/infra/prototype/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
