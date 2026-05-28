import os
from celery import Celery

# Брокером будет Redis (уже запущен)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_teacher",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Автоматическое обнаружение задач в папке app/tasks
celery_app.autodiscover_tasks(["app.tasks"])