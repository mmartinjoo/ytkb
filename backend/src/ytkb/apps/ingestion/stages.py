import asyncio
import logging
from pathlib import Path
from pprint import pprint

from ytkb.apps.ingestion.models import PipelineStage, PipelineStageStatus
from ytkb.apps.ingestion import tasks, video_pipeline
from ytkb.apps.videos.models import Channel, Video
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import services, video_queue, youtube, transcriber, embedder
from ytkb.core import storage, meilisearch, qdrant
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

async def discover_channel_stage(channel: Channel):
    yt_videos = await asyncio.to_thread(youtube.get_all_videos, handle=channel.handle)
    await sync_channel_stage(channel=channel, yt_videos=yt_videos)
        
async def sync_channels_stage():
    channels = await video_services.fetch_channels()
    for c in channels:
        yt_videos = await asyncio.to_thread(youtube.get_latest_videos, handle=c.handle)
        await sync_channel_stage(channel=c, yt_videos=yt_videos)
        
async def sync_channel_stage(channel: Channel, yt_videos: list[youtube.YoutubeVideo]):
    existing_yt_ids = [v.youtube_id for v in channel.videos]
    new_yt_videos = [v for v in yt_videos if v.id not in existing_yt_ids]
    
    videos = [video_services.new_video(channel, v.title, v.url, v.id) for v in new_yt_videos]
    pipeline_items = [services.new_pipeline_item(v) for v in videos]
    queue_items = [services.new_queue_item(v) for v in videos]
    
    async with SessionLocal() as session:
        session.add_all([*videos, *pipeline_items, *queue_items])
        await session.commit()
    
async def download_stage():
    videos = await video_queue.claim(stage=PipelineStage.DOWNLOAD, n=1)
    task_results = []
    
    await video_pipeline.mark_many(videos=videos, stage_status=PipelineStageStatus.IN_PROGRESS)
    logger.info(f"{len(videos)} videos marked as in progress: {[v.id for v in videos]}")
    
    for chunk in chunked(videos, size=5):
        task_results.append(
            tasks.download_video_batch.delay([v.id for v in chunk])
        )
        logger.info(f"video batch dispatched for {len(chunk)} videos: {[v.id for v in chunk]}")
        
    results: list[dict] = await asyncio.gather(
        *[asyncio.to_thread(task_res.get, timeout=3000) for task_res in task_results],
        return_exceptions=True
    )
    logger.info(f"{len(results)} tasks finished")
    
    await process_task_results(results)
    
async def transition_to_chunk_stage():
    videos = await video_pipeline.fetch(
        stage=PipelineStage.DOWNLOAD,
        stage_status=PipelineStageStatus.DONE,
    )
    
    for video in videos:
        audio_file_exists = await asyncio.to_thread(storage.exists, key=video.video_file_s3_key)
        audio_file_empty = await asyncio.to_thread(storage.empty, key=video.video_file_s3_key)
        if not audio_file_exists or audio_file_empty:
            await video_pipeline.mark_many(
                [video], 
                stage_status=PipelineStageStatus.FAILED,
                error=f"video file at {video.video_file_s3_key} is missing or empty",
            )
            
        audio_file_exists = await asyncio.to_thread(storage.exists, key=video.audio_file_s3_key)
        audio_file_empty = await asyncio.to_thread(storage.empty, key=video.audio_file_s3_key)
        if not audio_file_exists or audio_file_empty:
            await video_pipeline.mark_many(
                [video], 
                stage_status=PipelineStageStatus.FAILED,
                error=f"video file at {video.audio_file_s3_key} is missing or empty",
            )
            
    
async def chunk_stage():
    videos = video_queue.claim(stage=PipelineStage.CHUNK, n=100)
    for chunk in chunked(videos, size=5):
        tasks.chunk_video_batch.delay([v.id for v in chunk])
    
async def transcribe_stage(video: Video):
    assert len(video.chunks) != 0
    
    for chunk in video.chunks:
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
        Path(tmp_file_path).unlink()
        
    await video_services.update_video_content(video.id)
    
async def embed_stage(video: Video):
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
    
async def index_stage(video: Video):
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
    
def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]
        
async def process_task_results(results: list[dict]):
    for result in results:
        if isinstance(result, BaseException):
            logger.error(f"task failed: {repr(result)}")            
            continue
        
        try:
            assert isinstance(result, dict)
            ingestion_task_result = tasks.IngestionBatchTaskResult(**result)
        except Exception as exc:
            logger.error(f"failed to convert task result: {repr(exc)}, result: {result}")
            continue
        
        await mark_batch_result(ingestion_task_result)
        
async def mark_batch_result(result: tasks.IngestionBatchTaskResult):
    assert isinstance(result, tasks.IngestionBatchTaskResult), f"expected: tasks.IngestionBatchTaskResult, got: {type(result)}"
    
    succeeded_videos = await video_services.fetch_videos_by_ids(
        [t.video_id for t in result.succeeded_tasks],
    )
    logger.info(f"{len(succeeded_videos)} videos marked as done: {[v.id for v in succeeded_videos]}")
    await video_pipeline.mark_many(succeeded_videos, stage_status=PipelineStageStatus.DONE)
    
    failed_videos = await video_services.fetch_videos_by_ids(
        [t.video_id for t in result.failed_tasks],
    )
    logger.info(f"{len(succeeded_videos)} videos marked as failed: {[v.id for v in failed_videos]}")
    await video_pipeline.mark_many(failed_videos, stage_status=PipelineStageStatus.FAILED)
