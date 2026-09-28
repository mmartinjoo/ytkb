from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel
from ytkb.apps.ingestion.pipeline.steps.chunk import ChunkStep
from ytkb.apps.ingestion.pipeline.steps.download import DownloadStep
from ytkb.apps.videos.models import Video
        
    
class VerifyError(Exception):
    pass

class Step(ABC):
    name: ClassVar[str]
    depends_on: ClassVar[tuple[str]]
    max_attempts: ClassVar[int]
    retry_backoff: ClassVar[timedelta]
    lease: ClassVar[timedelta]
    
    @abstractmethod
    async def run(self, video: Video): ...
    
    @abstractmethod
    async def verify(self, video: Video): ...
    
class StepEnum(Enum):
    DOWNLOAD = "DOWNLOAD"
    CHUNK = "CHUNK"
    
    @classmethod
    def create_step(cls, value: "StepEnum") -> Step:
        if value == cls.DOWNLOAD:
            return DownloadStep()
        if value == cls.CHUNK:
            return ChunkStep()
        raise ValueError(f"invalid step: {value}")