import asyncio
import logging

from ytkb.apps.videos.models import Channel, Video
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import services, youtube
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

async def discover_channel_stage(channel_id: str):
    channel = await video_services.find_channel(id=channel_id)
    yt_videos = await asyncio.to_thread(youtube.get_all_videos, handle=channel.handle)
    videos = []
    for v in yt_videos:
        videos.append(Video(
            title=v.title,
            url=v.url,
            channel_id=channel.id,
            youtube_id=v.id,
        ))
        
    async with SessionLocal() as session:
        session.add_all(videos)
        await session.commit()
        
async def sync_channels_stage():
    channels = await video_services.get_channels()
    coros = []
    for c in channels:
        coros.append(sync_channel_stage(channel=c))
    await asyncio.gather(*coros)
        
async def sync_channel_stage(channel: Channel):
    yt_videos = await asyncio.to_thread(youtube.get_latest_videos, handle=channel.handle)
    videos = []
    for v in yt_videos:
        found = await video_services.is_video_exist(youtube_id=v.id)
        if found:
            continue

        videos.append(Video(
            title=v.title,
            url=v.url,
            channel_id=channel.id,
            youtube_id=v.id,
        ))
        
    await video_services.create_videos(videos)
    
async def download_stage(video: Video):
    downloaded_video = await asyncio.to_thread(
        youtube.download_video, 
        url=video.url,
        filename=video.id,
    )
    
    await asyncio.gather(
        services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.video_path, type=services.VideoAssetType.VIDEO),
        services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.audio_path, type=services.VideoAssetType.AUDIO),
    )