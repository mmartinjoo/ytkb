from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload
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

async def fetch_channels() -> list[Channel]:
    async with SessionLocal() as session:
        result = await session.scalars(
            select(Channel).options(selectinload(Channel.videos))
        )
        return list(result.all())
    
async def find_channel(id: int) -> Channel:
    async with SessionLocal() as session:
        return await session.get_one(Channel, id)
    
def new_video(channel: Channel, title: str, url: str, youtube_id: str) -> Video:
    return Video(
        title=title,
        url=url,
        channel=channel,
        youtube_id=youtube_id,
    )
        
async def update_s3_key(video_id: int, audio_file_s3_key: str):    
    async with SessionLocal() as session:
        await session.execute(
            update(Video)
            .where(Video.id == video_id)
            .values(
                audio_file_s3_key = audio_file_s3_key,
            )
        )
        await session.commit()
        
async def create_video_chunks(video: Video, chunk_s3_keys: list[str]):
    async with SessionLocal() as session:
        stmt = (
            delete(VideoChunk)
            .where(VideoChunk.video_id == video.id)    
        )
        await session.execute(stmt)
        
        for idx, s3_key in enumerate(chunk_s3_keys):
            stmt = (
                insert(VideoChunk)
                .values(
                    video_id=video.id,
                    position=idx,
                    audio_file_s3_key=s3_key,
                )
                .on_conflict_do_update(
                    index_elements=[VideoChunk.video_id, VideoChunk.position],
                    set_={
                        "audio_file_s3_key": s3_key,
                    },
                )
            )
            await session.execute(stmt)
        await session.commit()
        
async def update_chunk_content(chunk_id: int, content_with_timestamps: str, content_without_timestamps: str):
    async with SessionLocal() as session:
        await session.execute(
            update(VideoChunk)
                .where(VideoChunk.id == chunk_id)
                .values(
                    content_with_timestamps=content_with_timestamps,
                    content_without_timestamps=content_without_timestamps,
                )    
        )
        await session.commit()
        
async def update_video_content(video_id: int):
    async with SessionLocal() as session:
        video = await session.get_one(
            Video, 
            video_id,
            options=[selectinload(Video.chunks)],
        )
        
        content_with_timestamps = ""
        content_without_timestamps = ""
        for chunk in video.chunks:
            content_with_timestamps += chunk.content_with_timestamps + "\n"
            content_without_timestamps += chunk.content_without_timestamps + "\n"
        
        await session.execute(
            update(Video)
                .where(Video.id == video_id)
                .values(
                    content_with_timestamps=content_with_timestamps,
                    content_without_timestamps=content_without_timestamps,
                )
        )
        await session.commit()
        
async def find_video_with_chunks(video_id: int) -> Video:
    async with SessionLocal() as session:
        return await session.get_one(
            Video,
            video_id,
            options=[selectinload(Video.chunks)],
        )
        
async def find_video(video_id: int) -> Video:
    async with SessionLocal() as session:
        return await session.get_one(Video, video_id)
    
async def fetch_videos_by_ids(ids: list[int]) -> list[Video]:
    async with SessionLocal() as session:
        stmt = (
            select(Video)
            .where(Video.id.in_(ids))
        )
        res = await session.execute(stmt)
        return res.scalars().all()
    
async def find_channel_with_videos(channel_id: int) -> Channel:
    async with SessionLocal() as session:
        return await session.get_one(
            Channel,
            channel_id,
            options=[selectinload(Channel.videos)],
        )