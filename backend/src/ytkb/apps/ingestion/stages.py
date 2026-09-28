import asyncio
import logging
from pathlib import Path
from pprint import pprint

from ytkb.apps.videos.models import Channel, Video
from ytkb.apps.videos import services as video_services
from ytkb.apps.ingestion import services, youtube, transcriber, embedder
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
    
async def download_stage(video: Video):
    downloaded_video = await asyncio.to_thread(
        youtube.download_video, 
        video_id=video.id,
        url=video.url,
    )
    
    s3_keys = await asyncio.gather(
        services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.video_path, type=services.VideoAssetType.VIDEO),
        services.move_video_asset_to_s3(video_id=video.id, path=downloaded_video.audio_path, type=services.VideoAssetType.AUDIO),
    )
    
    assert len(s3_keys) == 2
    
    await video_services.update_s3_keys(
        video_id=video.id,
        video_file_s3_key=s3_keys[0],
        audio_file_s3_key=s3_keys[1],
    )
    
    # logger.info(f"removing {path}")
    # Path(path).unlink()

async def chunk_stage(video: Video, downloaded_video: youtube.DownloadedVideo):
    logger.info(f"chunking video {video.id}")
    await asyncio.to_thread(
        services.chunk_audio,
        video_id=video.id,
        downloaded_video=downloaded_video,
    )
    
    s3_keys = await services.move_audio_chunks_to_s3(
        video_id=video.id,
        downloaded_video=downloaded_video,
    )
    
    await video_services.create_video_chunks(
        video=video,
        chunk_s3_keys=s3_keys,
    )
    
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