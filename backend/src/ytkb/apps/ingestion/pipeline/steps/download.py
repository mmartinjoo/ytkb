import asyncio
from datetime import timedelta
from typing import ClassVar
import logging
import shutil

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
    claim_limit: ClassVar[int] = 3
    queue: ClassVar[str] = "io"
    
    async def run(self, video: Video):
        try:
            logger.info(f"downloading video {video.id}") 
            audio_path = await asyncio.to_thread(
                youtube.download_video, 
                video_id=video.id,
                url=video.url,
            )
            
            s3_key = await ingestion_services.move_audio_to_s3(video_id=video.id, path=audio_path)   
            assert s3_key is not None and len(s3_key) != 0
            
            await video_services.update_s3_key(
                video_id=video.id,
                audio_file_s3_key=s3_key,
            )
        finally:
            await asyncio.to_thread(shutil.rmtree, f"/tmp/{video.id}", ignore_errors=True)
        
    async def verify(self, video: Video):
        audio_file_exists = await asyncio.to_thread(storage.exists, key=video.audio_file_s3_key)
        audio_file_empty = await asyncio.to_thread(storage.empty, key=video.audio_file_s3_key)
        if not audio_file_exists or audio_file_empty:
            raise VerifyError(f"audio file at {video.audio_file_s3_key} is missing or empty")