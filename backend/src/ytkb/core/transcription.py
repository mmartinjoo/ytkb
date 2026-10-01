import shutil
from enum import Enum
from abc import ABC, abstractmethod
import logging
from functools import lru_cache

from mistralai.client import Mistral

from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download

from pydantic import BaseModel
from ytkb.core import storage
from ytkb.core.config import settings

logger = logging.getLogger(__name__)

class TranscriberProvider(Enum):
    LOCAL = "LOCAL"
    MISTRAL = "MISTRAL"

class TranscribeResponse(BaseModel):
    content_with_timestamps: str
    content_without_timestamps: str

class Transriber(ABC):
    @abstractmethod
    def transcribe(self, audio_file_path: str) -> TranscribeResponse: ...
    
class LocalTranscriber(Transriber):
    @lru_cache(maxsize=1)
    def get_model(self) -> WhisperModel:
        path = snapshot_download("Systran/faster-whisper-large-v3")
        return WhisperModel(path, device="cpu", compute_type="int8")

    def transcribe(self, audio_file_s3_key: str) -> TranscribeResponse:
        try:
            logger.info(f"transcribing {audio_file_s3_key} with Mistral...")
            filename = audio_file_s3_key.split(".")[-1]
            assert filename
            
            audio_file_path = "/tmp/{filename}"
            data = storage.get_file(key=audio_file_s3_key)
            with open(audio_file_path, "wb") as f:
                f.write(data)
                
            content_with_timestamps = ""
            content_without_timestamps = ""
            segments, info = self.get_model().transcribe(audio_file_path, beam_size=5)

            for segment in segments:
                content_without_timestamps += f"{segment.text}\n"
                content_with_timestamps += f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n")

            return TranscribeResponse(
                content_with_timestamps=content_with_timestamps,
                content_without_timestamps=content_without_timestamps
            )
        finally:
            shutil.rmtree(audio_file_path)
        
class MistralTranscriber(Transriber):
    client: Mistral
    
    def __init__(self, api_key):
        self.client = Mistral(api_key)
        
    def transcribe_mistral(self, audio_file_s3_key: str):
        logger.info(f"transcribing {audio_file_s3_key} with Mistral...")
        data = storage.get_file(key=audio_file_s3_key)
        response = self.client.audio.transcriptions.complete(
            model="voxtral-mini-latest",
            file={
                "content": data,
                "file_name": "audio.m4a",
            },
            language="hu",
        )
        return TranscribeResponse(
            content_with_timestamps=response.text,
            content_without_timestamps=response.text,
        )
        
def create_transcriber(provider: str):
    prov = TranscriberProvider(provider.upper())
    match prov:
        case TranscriberProvider.LOCAL:
            return LocalTranscriber()
        case TranscriberProvider.MISTRAL:
            return MistralTranscriber()