import asyncio
from datetime import timedelta
from typing import ClassVar

from sqlalchemy import select
from ytkb.apps.videos.models import Video, VideoChunk
from ytkb.core import embedding, qdrant
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum
from ytkb.core.db import SessionLocal


class EmbedStep(Step):
    name: ClassVar[str] = StepEnum.EMBED.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value, StepEnum.CHUNK.value, StepEnum.TRANSCRIBE.value,)
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(hours=3)
    lease: ClassVar[timedelta] = timedelta(hours=2)
    claim_limit: ClassVar[int] = 5
    queue: ClassVar[str] = "cpu"
    
    async def run(self, video: Video):
        async with SessionLocal() as session:
            stmt = (
                select(VideoChunk)
                .where(VideoChunk.video_id == video.id)
            )
            chunks = (await session.scalars(stmt)).all()

        assert len(chunks) != 0
            
        texts = []
        chunk_ids = []
        for chunk in chunks:
            texts.append(chunk.content_without_timestamps)
            chunk_ids.append(chunk.id)
                
        embedder = embedding.create_embedder()
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