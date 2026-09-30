from celery.schedules import crontab
from ytkb.core.celery import app

app.conf.beat_schedule = {
    "sync_channels": {
        "task": "ytkb.apps.ingestion.tasks.sync_channels",
        "schedule": crontab(hour=0, minute=0),
    },
    "fanout_download_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_download_tasks",
        "schedule": 60 * 60,
    },
    "fanout_chunk_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_chunk_tasks",
        "schedule": 1 * 60,
    },
    "fanout_transcribe_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_transcribe_tasks",
        "schedule": 60 * 60,
    },
    "fanout_embed_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_embed_tasks",
        "schedule": 45 * 60,
    },
    "fanout_index_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_index_tasks",
        "schedule": 10 * 60,
    },
}