import asyncio
import logging
from enum import Enum, auto
from pathlib import Path
from ytkb.core import storage

logger = logging.getLogger(__name__)

class VideoAssetType(Enum):
    VIDEO = auto()
    AUDIO = auto()

async def move_video_asset_to_s3(video_id: int, path: str, type: VideoAssetType):
    logger.info(f"copying {path} to S3 for video {video_id}")
    with open(path, "rb") as f:
        data = await asyncio.to_thread(f.read)
        fn = storage.put_video_file if type == VideoAssetType.VIDEO else storage.put_audio_file
        await asyncio.to_thread(
            fn,
            video_id=video_id,
            data=data,
        )
        
    logger.info(f"removing {path}")
    Path(path).unlink()