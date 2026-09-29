import asyncio
from datetime import timedelta
from typing import ClassVar

from ytkb.apps.videos.models import Video
from ytkb.core import meilisearch
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum


class IndexStep(Step):
    name: ClassVar[str] = StepEnum.INDEX.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value, StepEnum.CHUNK.value, StepEnum.TRANSCRIBE.value,)
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(minutes=45)
    lease: ClassVar[timedelta] = timedelta(minutes=30)
    batch_size: ClassVar[int] = 10
    concurrency: ClassVar[int] = 2
    
    async def run(self, video: Video):
        assert len(video.chunks) != 0
            
        meili_chunks: list[meilisearch.MeiliSearchChunk] = []
        for chunk in video.chunks:
            meili_chunks.append(meilisearch.MeiliSearchChunk(
                id=chunk.id,
                video_id=video.id,
                title=video.title,
                url=video.url,
                position=chunk.position,
                content=chunk.content_without_timestamps,
            ))
            
        await asyncio.to_thread(meilisearch.index_video, chunks=meili_chunks)
        
    async def verify(self, video: Video):
        pass