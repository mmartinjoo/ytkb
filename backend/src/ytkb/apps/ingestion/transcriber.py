import logging
from functools import lru_cache

from mistralai.client import Mistral

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

from pydantic import BaseModel
from ytkb.core import storage
from ytkb.core.config import settings

logger = logging.getLogger(__name__)

client = Mistral(settings.mistral_api_key)
model = "voxtral-mini-latest"

@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    path = snapshot_download("Systran/faster-whisper-large-v3")
    return WhisperModel(path, device="cpu", compute_type="int8")

class TranscribeResponse(BaseModel):
    content_with_timestamps: str
    content_without_timestamps: str

def transcribe(audio_file_path: str) -> TranscribeResponse:
    content_with_timestamps = ""
    content_without_timestamps = ""
    segments, info = get_model().transcribe(audio_file_path, beam_size=5)

    for segment in segments:
        content_without_timestamps += f"{segment.text}\n"
        content_with_timestamps = f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")

    return TranscribeResponse(
        content_with_timestamps=content_with_timestamps,
        content_without_timestamps=content_without_timestamps
    )
        
async def transcribe_mistral(video_id: int):
    logger.info(f"transcribing {video_id} with Mistral...")
    data = storage.get_audio_file(video_id=video_id)
    response = client.audio.transcriptions.complete(
        model=model,
        file={
            "content": data,
            "file_name": "audio.m4a",
        },
        language="hu",
    )
    print(response)