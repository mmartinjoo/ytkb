from sqlalchemy import select, exists
from ytkb.apps.videos.models import Channel, Video
from ytkb.apps.videos.schemas import CreateChannelData
from ytkb.core.db import SessionLocal

async def create_channel(data: CreateChannelData) -> Channel:
    async with SessionLocal() as session:
        channel = Channel(
            name=data.name,
            url=data.url,
            handle=data.handle,
        )
        session.add(channel)
        await session.commit()
    return channel

async def get_channels() -> list[Channel]:
    async with SessionLocal() as session:
        result = await session.scalars(select(Channel))
        return list(result.all())
    
async def find_channel(id: int) -> Channel:
    async with SessionLocal() as session:
        return await session.get_one(Channel, id)
    
async def is_video_exist(youtube_id: str) -> Video:
    async with SessionLocal() as session:
        return await session.scalar(select(exists().where(Video.youtube_id == youtube_id)))
    
async def create_videos(videos: list[Video]):
    async with SessionLocal() as session:
        session.add_all(videos)
        await session.commit()