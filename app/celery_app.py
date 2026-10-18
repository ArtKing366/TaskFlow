import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

broker_url = os.getenv(
    "CELERY_BROKER_URL",
    "redis://localhost:6379/0",
)

result_backend = os.getenv(
    "CELERY_RESULT_BACKEND",
    "redis://localhost:6379/0",
)

celery_app = Celery(
    "taskflow",
    broker=broker_url,
    backend=result_backend,
    include=["app.celery_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)