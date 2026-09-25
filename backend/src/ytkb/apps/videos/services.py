from sqlalchemy import select
from ytkb.apps.videos.models import Channel
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