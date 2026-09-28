from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import ClassVar

from pydantic import BaseModel
from ytkb.apps.videos.models import Video

class StepEnum(Enum):
    DOWNLOAD = "download"
    CHUNK = "chunk"
    
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
    