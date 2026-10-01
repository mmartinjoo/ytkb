import logging
from datetime import timedelta
from typing import ClassVar

from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum, VerifyError
from ytkb.apps.videos.models import Video, VideoStatus
from ytkb.apps.videos import services as video_services
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

class PublishStep(Step):
    name: ClassVar[str] = StepEnum.PUBLISH.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value, StepEnum.CHUNK.value, StepEnum.TRANSCRIBE.value, StepEnum.EMBED.value, StepEnum.INDEX.value, )
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(minutes=5)
    lease: ClassVar[timedelta] = timedelta(minutes=2)
    claim_limit: ClassVar[int] = 64
    queue: ClassVar[str] = "io"
    
    async def run(self, video: Video):
        logger.info(f"publishing video {video.id}")
        
        await video_services.publish(video)
        
    async def verify(self, video: Video):
        async with SessionLocal() as session:
            video_reloaded = await session.get_one(Video, video.id)
            
        if video_reloaded.status != VideoStatus.PUBLISHED:
            raise VerifyError(f"video has not been published")