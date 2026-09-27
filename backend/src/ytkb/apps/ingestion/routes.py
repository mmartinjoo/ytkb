import asyncio

from fastapi import APIRouter

from ytkb.apps.ingestion import youtube, stages
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@router.get("/yt")
async def get_yt():
    return await asyncio.to_thread(
        youtube.get_all_videos,
        handle="@Topburkolo",
    )
    
@router.get("/download")
async def download():
    async with SessionLocal() as session:
        video = await session.get_one(Video, 379)
        return await stages.download_stage(video)

@router.get("/chunk")
async def chunk():
    async with SessionLocal() as session:
        video = await session.get_one(Video, 379)
        downloaded_video = youtube.DownloadedVideo.create_for_video(379)
        return await stages.chunk_stage(video, downloaded_video)
    
@router.get("/transcribe")
async def transcribe():
    async with SessionLocal() as session:
        video = await session.get_one(
            Video, 379,
            options=[selectinload(Video.chunks)],
        )
        return await stages.transcribe_stage(video)