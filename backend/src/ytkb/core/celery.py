from celery import Celery

from ytkb.core.config import settings

app = Celery(
    "ytkb",
    broker=settings.redis_url,
    backend=settings.redis_url,
)