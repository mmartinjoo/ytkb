import asyncio
import logging

from ytkb.apps.videos.models import Video
from ytkb.core import celery
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import youtube
from ytkb.apps.ingestion.pipeline import repository as pipeline_repository
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

@celery.app.task
def discover_channel(channel_id: int):
    asyncio.run(adiscover_channel(channel_id))
    
@celery.app.task
def sync_channels():
    asyncio.run(async_channels())
    
@celery.app.task
def sync_channel(channel_id: int):
    asyncio.run(async_channel(channel_id=channel_id))
    
async def async_channels():
    channels = await video_services.fetch_channels()
    for c in channels:
        sync_channel.delay(c.id)
    
async def adiscover_channel(channel_id: int):
    logger.ingo(f"discovering channel {channel_id}")
    
    channel = await video_services.find_channel(id=channel_id)
    yt_videos = await asyncio.to_thread(youtube.get_all_videos, handle=channel.handle)
    
    logger.info(f"found {len(yt_videos)} YouTube videos")
    
    videos = []
    for v in yt_videos:
        video = Video(
            title=v.title,
            url=v.url,
            channel_id=channel.id,
        )
        videos.append(video)
        await pipeline_repository.enqueue_video(session=session, video=video)
        
    async with SessionLocal() as session:
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