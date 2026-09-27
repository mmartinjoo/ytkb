import logging
from functools import lru_cache

from mistralai.client import Mistral

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

from ytkb.core import storage
from ytkb.core.config import settings

logger = logging.getLogger(__name__)

client = Mistral(settings.mistral_api_key)
model = "voxtral-mini-latest"

@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    path = snapshot_download("Systran/faster-whisper-large-v3")
    return WhisperModel(path, device="cpu", compute_type="int8")

def transcribe(audio_file_path: str):
    segments, info = get_model().transcribe(audio_file_path, beam_size=5)
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
        
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