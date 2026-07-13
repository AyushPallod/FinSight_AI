from celery import Celery
from app.core.config import settings

# Initialize Celery app instance
# We configure both the broker (where task tickets are clipped) and backend 
# (where task output statuses are stored) to use Redis.
celery_app = Celery(
    "finsight_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.ingestion"]
)

# Apply default performance and serialization settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Automatically clean up task history from Redis memory after 1 hour
    result_expires=3600,

)
