import asyncio
import logging

from celery import group

from ytkb.apps.videos.models import Video
from ytkb.core import celery
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import youtube
from ytkb.apps.ingestion.pipeline import repository as pipeline_repository
from ytkb.core.db import SessionLocal
from ytkb.apps.ingestion.pipeline import executor
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum
from ytkb.core.db import engine

logger = logging.getLogger(__name__)

@celery.app.task
def discover_channel(channel_id: int):
    run_async(adiscover_channel(channel_id))
    
@celery.app.task
def sync_channels():
    run_async(async_channels())
    
async def async_channels():
    channels = await video_services.fetch_channels()
    for c in channels:
        sync_channel.delay(c.id)
    
@celery.app.task
def sync_channel(channel_id: int):
    run_async(async_channel(channel_id=channel_id))
    
@celery.app.task
def fanout_download_tasks(n: int = 1):
    group(download_videos.s() for _ in range(n)).apply_async()
    
@celery.app.task
def fanout_chunk_tasks(n: int = 4):
    group(chunk_videos.s() for _ in range(n)).apply_async()
    
@celery.app.task
def fanout_transcribe_tasks(n: int = 1):
    group(transcribe_videos.s() for _ in range(n)).apply_async()
    
@celery.app.task
def fanout_embed_tasks(n: int = 1):
    group(embed_videos.s() for _ in range(n)).apply_async()

@celery.app.task
def fanout_index_tasks(n: int = 4):
    group(index_videos.s() for _ in range(n)).apply_async()

@celery.app.task
def download_videos():
    run_async(executor.execute_batch(StepEnum.DOWNLOAD))

@celery.app.task
def chunk_videos():
    run_async(executor.execute_batch(StepEnum.CHUNK))

@celery.app.task
def transcribe_videos():
    run_async(executor.execute_batch(StepEnum.TRANSCRIBE))

@celery.app.task
def embed_videos():
    run_async(executor.execute_batch(StepEnum.EMBED))

@celery.app.task
def index_videos():
    run_async(executor.execute_batch(StepEnum.INDEX))
    
def run_async(coro):
    async def main():
        try:
            return await coro
        finally:
            await engine.dispose()
    return asyncio.run(main())
    
async def adiscover_channel(channel_id: int):
    logger.info(f"discovering channel {channel_id}")
    
    channel = await video_services.find_channel(id=channel_id)
    yt_videos = await asyncio.to_thread(youtube.get_all_videos, handle=channel.handle)
    
    logger.info(f"found {len(yt_videos)} YouTube videos")
    
    videos = []
    async with SessionLocal() as session:
        for v in yt_videos:
            video = Video(
                title=v.title,
                url=v.url,
                channel_id=channel.id,
                youtube_id=v.id,
            )
            videos.append(video)
            await pipeline_repository.enqueue_video(session=session, video=video)
            session.add_all(videos)
            await session.commit()
        
    logger.info(f"created and enqueued {len(yt_videos)} videos")
        
async def async_channel(channel_id: int):
    logger.info(f"syncing channel {channel_id}")
    channel = await video_services.find_channel(id=channel_id)
    yt_videos = await asyncio.to_thread(youtube.get_latest_videos, handle=channel.handle)    
    
    existing_yt_ids = [v.youtube_id for v in channel.videos]
    new_yt_videos = [v for v in yt_videos if v.id not in existing_yt_ids]
    
    logger.info(f"found {len(yt_videos)} new Youtube videos")
    
    videos = [video_services.new_video(channel, v.title, v.url, v.id) for v in new_yt_videos]
    for video in videos:
        await pipeline_repository.enqueue_video(session=session, video=video)
    
    async with SessionLocal() as session:
        session.add_all(*videos)
        await session.commit()
        
    logger.info(f"created and enqueued {len(videos)} videos")