from celery.schedules import crontab
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum
from ytkb.core.celery import app

app.conf.beat_schedule = {
    "sync_channels": {
        "task": "ytkb.apps.ingestion.tasks.sync_channels",
        "schedule": crontab(hour=0, minute=0),
    },
    "fanout_download_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_ingestion_tasks",
        "schedule": 60 * 60,
        "args": (StepEnum.DOWNLOAD.value,),
    },
    "fanout_chunk_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_ingestion_tasks",
        "schedule": 10 * 60,
        "args": (StepEnum.CHUNK.value,),
    },
    "fanout_transcribe_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_ingestion_tasks",
        "schedule": 30 * 60,
        "args": (StepEnum.TRANSCRIBE.value,),
    },
    "fanout_embed_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_ingestion_tasks",
        "schedule": 30 * 60,
        "args": (StepEnum.TRANSCRIBE.value,),
    },
    "fanout_index_tasks": {
        "task": "ytkb.apps.ingestion.tasks.fanout_ingestion_tasks",
        "schedule": 5 * 60,
        "args": (StepEnum.TRANSCRIBE.value,),
    },
}