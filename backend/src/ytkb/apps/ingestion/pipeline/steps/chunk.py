import asyncio
import logging
from datetime import timedelta
from typing import ClassVar

from ytkb.core import storage
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum, VerifyError
from ytkb.apps.videos.models import Video
from ytkb.apps.ingestion import services as ingestion_services
from ytkb.apps.videos import services as video_services
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

class ChunkStep(Step):
    name: ClassVar[str] = StepEnum.CHUNK.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value,)
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(minutes=30)
    lease: ClassVar[timedelta] = timedelta(minutes=15)
    batch_size: ClassVar[int] = 4
    concurrency: ClassVar[int] = 2
    
    async def run(self, video: Video):
        logger.info(f"chunking video {video.id}")
        assert video.audio_file_s3_key is not None and len(video.audio_file_s3_key) != 0
        
        s3_keys = await ingestion_services.chunk_audio(video=video)
        
        await video_services.create_video_chunks(
            video=video,
            chunk_s3_keys=s3_keys,
        )
        
    async def verify(self, video: Video):
        async with SessionLocal() as session:
            await session.refresh(video, attribute_names=["chunks"])
        
        if len(video.chunks) == 0:
            raise VerifyError(f"video {video.id} has 0 chunks")
        
        for chunk in video.chunks:
            exists = await asyncio.to_thread(storage.exists, key=chunk.audio_file_s3_key)
            empty = await asyncio.to_thread(storage.empty, key=chunk.audio_file_s3_key)
            if not exists or empty:
                raise VerifyError(f"video chunk {chunk.id} does not exist or empty")