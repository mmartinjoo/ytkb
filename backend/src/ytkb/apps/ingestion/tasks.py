import asyncio
import logging

from ytkb.apps.videos.models import Video
from ytkb.core import celery
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import youtube
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

@celery.app.task
def discover_channel(channel_id: int):
    asyncio.run(adiscover_channel(channel_id))
    
async def adiscover_channel(channel_id: int):
    channel = await video_services.find_channel(id=channel_id)
    yt_videos = await asyncio.to_thread(youtube.get_all_videos, handle=channel.handle)
    videos = []
    for v in yt_videos:
        videos.append(Video(
            title=v.title,
            url=v.url,
            channel_id=channel.id,
        ))
        
    async with SessionLocal() as session:
        session.add_all(videos)
        await session.commit()