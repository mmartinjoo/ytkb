import asyncio
import logging
import subprocess
import glob
from enum import Enum, auto
from typing import TypeAlias
from pathlib import Path
from ytkb.core import storage
from ytkb.apps.ingestion.youtube import DownloadedVideo

logger = logging.getLogger(__name__)

S3Key: TypeAlias = str

class VideoAssetType(Enum):
    VIDEO = auto()
    AUDIO = auto()

async def move_video_asset_to_s3(video_id: int, path: str, type: VideoAssetType) -> S3Key:
    logger.info(f"copying {path} to S3 for video {video_id}")
    with open(path, "rb") as f:
        data = await asyncio.to_thread(f.read)
        fn = storage.put_video_file if type == VideoAssetType.VIDEO else storage.put_audio_file
        return await asyncio.to_thread(
            fn,
            video_id=video_id,
            data=data,
        )
        
def chunk_audio(video_id: int, downloaded_video: DownloadedVideo):
    logger.info(f"chunk audio for {video_id}")
    assert Path(downloaded_video.chunks_path).exists()
    
    command = [
        "ffmpeg",
        "-i", downloaded_video.audio_path,
        "-c:a", "copy",
        "-f", "segment",
        "-segment_time", "300",
        "-reset_timestamps", "1",
        f"{downloaded_video.chunks_path}/{video_id}_%03d.m4a",
    ]
    
    try:
        res = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        
        if res.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed ({res.returncode})\n"
                f"stdout:\n{res.stdout}\n"
                f"stderr:\n{res.stderr}"
            )
    except subprocess.CalledProcessError as exc:
        logger.error("FFmpeg stderr: %s", exc.stderr)
        raise
    
async def move_audio_chunks_to_s3(video_id: int, downloaded_video: DownloadedVideo) -> list[S3Key]:
    assert Path(downloaded_video.chunks_path).exists()
    
    files = glob.glob(downloaded_video.chunks_path + "/*.m4a")
    assert len(files) != 0
    
    files.sort()
    semaphore = asyncio.Semaphore(8)
    coros = []
    for idx, file in enumerate(files):
        coros.append(move_audio_chunk_to_s3(
            semaphore=semaphore,
            filename=file,
            video_id=video_id,
            position=idx,
        ))
    
    return await asyncio.gather(*coros)
        
async def move_audio_chunk_to_s3(semaphore: asyncio.Semaphore, filename: str, video_id: int, position: int) -> S3Key:
    def copy_file():
        with open(filename, "rb") as f:
            return storage.put_audio_chunk_file(
                video_id=video_id,
                data=f.read(),  
                position=position,      
            )
            
    async with semaphore:
        return await asyncio.to_thread(copy_file)
