import asyncio

from fastapi import APIRouter

from ytkb.apps.ingestion import youtube

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@router.get("/yt")
async def get_yt():
    return await asyncio.to_thread(
        youtube.get_all_videos,
        handle="@Topburkolo",
    )