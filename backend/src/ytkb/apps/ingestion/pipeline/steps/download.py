import asyncio
from datetime import timedelta
from typing import ClassVar
import logging

from ytkb.core import storage
from ytkb.apps.ingestion import youtube, services as ingestion_services
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum, VerifyError
from ytkb.apps.videos.models import Video
from ytkb.apps.videos import services as video_services

logger = logging.getLogger(__name__)

class DownloadStep(Step):
    name: ClassVar[str] = StepEnum.DOWNLOAD.value
    depends_on: ClassVar[tuple[str]] = ()
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(hours=2)
    lease: ClassVar[timedelta] = timedelta(hours=1)
    workers: ClassVar[int] = 4
    batch_size: ClassVar[int] = 2
    concurrency: ClassVar[int] = 2
    
    async def run(self, video: Video):
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
        
    async def verify(self, video: Video):
        audio_file_exists = await asyncio.to_thread(storage.exists, key=video.video_file_s3_key)
        audio_file_empty = await asyncio.to_thread(storage.empty, key=video.video_file_s3_key)
        if not audio_file_exists or audio_file_empty:
            raise VerifyError(f"video file at {video.audio_file_s3_key} is missing or empty")
            
        audio_file_exists = await asyncio.to_thread(storage.exists, key=video.audio_file_s3_key)
        audio_file_empty = await asyncio.to_thread(storage.empty, key=video.audio_file_s3_key)
        if not audio_file_exists or audio_file_empty:
            raise VerifyError(f"audio file at {video.audio_file_s3_key} is missing or empty")