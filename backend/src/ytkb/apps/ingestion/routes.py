import asyncio

from fastapi import APIRouter

from ytkb.apps.ingestion import youtube, stages
from ytkb.apps.videos import services as video_services
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
    video = await video_services.find_video(video_id=379)
    return await stages.download_stage(video)

@router.get("/chunk")
async def chunk():
    video = await video_services.find_video(video_id=379)
    downloaded_video = youtube.DownloadedVideo.create_for_video(379)
    return await stages.chunk_stage(video, downloaded_video)
    
@router.get("/transcribe")
async def transcribe():
    video = await video_services.find_video_with_chunks(video_id=379)
    return await stages.transcribe_stage(video)
        
@router.get("/embed")
async def embed():
    video = await video_services.find_video_with_chunks(video_id=379)
    return await stages.embed_stage(video)

@router.get("/index")
async def index():
    video = await video_services.find_video_with_chunks(video_id=379)
    return await stages.index_stage(video)