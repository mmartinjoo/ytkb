import asyncio
from functools import lru_cache
import logging

from fastembed import TextEmbedding

from ytkb.apps.videos.models import Video
from ytkb.core import qdrant

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    return TextEmbedding("intfloat/multilingual-e5-large") # 1024-dim    

async def embed(video: Video):
    assert len(video.chunks) != 0
    texts = []
    chunk_ids = []
    for chunk in video.chunks:
        assert chunk.content_without_timestamps is not None and len(chunk.content_without_timestamps) != 0
        texts.append(chunk.content_without_timestamps)
        chunk_ids.append(chunk.id)
        
    vectors = await asyncio.to_thread(get_model().embed, texts)
    await asyncio.to_thread(
        qdrant.upsert,
        collection_name="video_chunks",
        vectors=vectors,
        video_id=video.id,
        video_chunk_ids=chunk_ids,
    )