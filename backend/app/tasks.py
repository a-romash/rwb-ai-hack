from celery import Celery

from app.config import settings

database_url = settings.database_url.render_as_string(hide_password=False)
celery_app = Celery("pipeline", broker=f"sqla+{database_url}", backend=f"db+{database_url}")
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
)


@celery_app.task(name="pipeline.check_queue")
def check_queue():
    return {"status": "ok", "broker": "postgresql"}


if __name__ == "__main__":
    result = check_queue.delay()
    value = result.get(timeout=30)
    assert value == {"status": "ok", "broker": "postgresql"}, value
    print(f"Queue check passed: {result.id}: {value}")
    result.forget()
