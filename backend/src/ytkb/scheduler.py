from celery.schedules import crontab
from ytkb.core.celery import app

app.conf.beat_schedule = {
    "sync_channels": {
        "task": "ytkb.ingestion.tasks.sync_channels",
        "schedule": crontab(hour=0, minute=0),
    },
    "fanout_downloads": {
        "task": "ytkb.apps.ingestion.tasks.fanout_downloads",
        "schedule": 30 * 60,
    },
}