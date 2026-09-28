import asyncio
import logging

from pydantic import BaseModel
from ytkb.apps.videos.models import Video
from ytkb.core import celery
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import youtube, services as ingestion_services
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

class IngestionTaskResult(BaseModel):
    video_id: int
    ok: bool
    error: str|None = None
    
class IngestionBatchTaskResult(BaseModel):
    succeeded_tasks: list[IngestionTaskResult] = []
    failed_tasks: list[IngestionTaskResult] = []
    
def create_batch_result(results: list[IngestionTaskResult]) -> dict:
    batch_result = IngestionBatchTaskResult()
    for res in results:
        if res.ok:
            batch_result.succeeded_tasks.append(res)
        else:
            batch_result.failed_tasks.append(res)
    return batch_result.model_dump()

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
        
@celery.app.task
def download_video_batch(video_ids: list[int]) -> dict:
    return asyncio.run(adownload_video_batch(video_ids))       

@celery.app.task
def chunk_video_batch(video_ids: list[int]) -> dict:
    return asyncio.run(achunk_video_batch(video_ids))         
    
async def adownload_video_batch(video_ids: list[int]) -> dict:
    videos = await video_services.fetch_videos_by_ids(video_ids)
    semaphore = asyncio.Semaphore(2)
    coros = [adownload_video(semaphore, v) for v in videos]
    results = await asyncio.gather(*coros)
    return create_batch_result(results)

async def achunk_video_batch(video_ids: list[int]) -> dict:
    videos = await video_services.fetch_videos_by_ids(video_ids)
    semaphore = asyncio.Semaphore(8)
    coros = [achunk_video(semaphore, v) for v in videos]
    return await asyncio.gather(*coros)

async def adownload_video(semaphore: asyncio.Semaphore, video: Video) -> IngestionTaskResult:
    try:
        async with semaphore:
            logger.info(f"downloading video {video.id}")
            downloaded_video = await asyncio.to_thread(
                youtube.download_video, 
                video_id=video.id,
                url=video.url,
            )
            
            s3_keys = await asyncio.gather(
                ingestion_services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.video_path, type=ingestion_services.VideoAssetType.VIDEO),
                ingestion_services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.audio_path, type=ingestion_services.VideoAssetType.AUDIO),
            )
            
            assert len(s3_keys) == 2
            
            await video_services.update_s3_keys(
                video_id=video.id,
                video_file_s3_key=s3_keys[0],
                audio_file_s3_key=s3_keys[1],
            )
            
            return IngestionTaskResult(
                video_id=video.id,
                ok=True,
            )
    except Exception as exc:
        return IngestionTaskResult(
            video_id=video.id,
            ok=True,
            error=repr(exc),
        )
        
async def achunk_video(video: Video):
    logger.info(f"chunking video {video.id}")
    assert video.audio_file_s3_key is not None and len(video.audio_file_s3_key) != 0
    
    s3_keys = await ingestion_services.chunk_audio(video=video)
    
    await video_services.create_video_chunks(
        video=video,
        chunk_s3_keys=s3_keys,
    )