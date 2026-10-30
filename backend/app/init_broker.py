from app.tasks import celery_app


def initialize():
    with celery_app.connection_for_write() as connection:
        with connection.channel() as channel:
            channel.queue_declare(queue="celery", durable=True)


if __name__ == "__main__":
    initialize()
