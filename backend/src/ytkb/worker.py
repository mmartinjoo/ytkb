from ytkb.core.celery import app

app.autodiscover_tasks([
    "ytkb.apps.ingestion",
])