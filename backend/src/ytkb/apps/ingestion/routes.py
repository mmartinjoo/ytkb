import asyncio

from fastapi import APIRouter

from ytkb.apps.ingestion import youtube, stages
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal

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
        video = await session.get_one(Video, 329)
        return await stages.download_stage(video)