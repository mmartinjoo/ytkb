import asyncio
from datetime import timedelta
from typing import ClassVar

from ytkb.apps.videos.models import Video
from ytkb.core import qdrant
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum
from ytkb.apps.ingestion import embedder


class EmbedStep(Step):
    name: ClassVar[str] = StepEnum.EMBED.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value, StepEnum.CHUNK.value, StepEnum.TRANSCRIBE.value,)
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(hours=2)
    lease: ClassVar[timedelta] = timedelta(hours=1)
    batch_size: ClassVar[int] = 1
    concurrency: ClassVar[int] = 1
    
    async def run(self, video: Video):
        assert len(video.chunks) != 0
            
        texts = []
        chunk_ids = []
        for chunk in video.chunks:
            texts.append(chunk.content_without_timestamps)
            chunk_ids.append(chunk.id)
                
        vectors = await asyncio.to_thread(embedder.embed, texts=texts)
        await asyncio.to_thread(
            qdrant.upsert,
            collection_name="video_chunks",
            vectors=vectors,
            video_id=video.id,
            video_chunk_ids=chunk_ids,
        )
        
    async def verify(self, video: Video):
        pass