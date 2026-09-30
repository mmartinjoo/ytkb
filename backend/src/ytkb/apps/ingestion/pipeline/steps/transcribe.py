import asyncio
from datetime import timedelta
from pathlib import Path
from typing import ClassVar
import logging

from sqlalchemy import select
from ytkb.apps.ingestion.pipeline.steps.step import Step, StepEnum
from ytkb.apps.ingestion import transcriber
from ytkb.apps.videos.models import Video, VideoChunk
from ytkb.apps.videos import services as video_services
from ytkb.core import storage
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

class TranscribeStep(Step):
    name: ClassVar[str] = StepEnum.TRANSCRIBE.value
    depends_on: ClassVar[tuple[str]] = (StepEnum.DOWNLOAD.value, StepEnum.CHUNK.value,)
    max_attempts: ClassVar[int] = 3
    retry_backoff: ClassVar[timedelta] = timedelta(hours=3)
    lease: ClassVar[timedelta] = timedelta(hours=2)
    claim_limit: ClassVar[int] = 1
    queue: ClassVar[str] = "cpu"
    
    async def run(self, video: Video):
        logger.info(f"transcribing video {video.id}")
        
        async with SessionLocal() as session:
            stmt = (
                select(VideoChunk)
                .where(VideoChunk.video_id == video.id)
            )
            chunks = (await session.scalars(stmt)).all()
            
        assert len(chunks) != 0
            
        for chunk in chunks:
            try:
                logger.info(f"transcribing video chunk {chunk.id}")
                
                assert chunk.audio_file_s3_key is not None
                
                data = await asyncio.to_thread(storage.get_file, key=chunk.audio_file_s3_key)
                tmp_file_path = f"/tmp/{video.id}_{chunk.position}.m4a"
                
                with open(tmp_file_path, "wb") as f:
                    await asyncio.to_thread(f.write, data)
        
                resp = await asyncio.to_thread(transcriber.transcribe, tmp_file_path)
                assert resp.content_with_timestamps is not None and len(resp.content_with_timestamps) != 0
                assert resp.content_without_timestamps is not None and len(resp.content_without_timestamps) != 0
                
                await video_services.update_chunk_content(
                    chunk_id=chunk.id,
                    content_with_timestamps=resp.content_with_timestamps,
                    content_without_timestamps=resp.content_without_timestamps,
                )
            except Exception as exc:
                raise exc
            finally:
                Path(tmp_file_path).unlink(missing_ok=True)
            
        await video_services.update_video_content(video.id)
        
    async def verify(self, video: Video):
        pass