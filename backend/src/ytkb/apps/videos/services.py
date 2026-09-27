from sqlalchemy import select, exists
from sqlalchemy.dialects.postgresql import insert
from ytkb.apps.videos.models import Channel, Video, VideoChunk
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
        
async def update_s3_keys(video: Video, video_file_s3_key: str, audio_file_s3_key: str):    
    async with SessionLocal() as session:
        video.audio_file_s3_key = audio_file_s3_key
        video.video_file_s3_key = video_file_s3_key
        await session.commit()
        
async def create_video_chunks(video: Video, chunk_s3_keys: list[str]):
    async with SessionLocal() as session:
        for idx, s3_key in enumerate(chunk_s3_keys):
            stmt = insert(VideoChunk).values(
                video_id=video.id,
                position=idx,
                audio_file_s3_key=s3_key,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[VideoChunk.video_id, VideoChunk.position],
                set_={
                    "audio_file_s3_key": s3_key,
                },
            )
            await session.execute(stmt)
        await session.commit()