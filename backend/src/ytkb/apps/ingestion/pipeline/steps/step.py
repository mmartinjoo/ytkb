from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import ClassVar

from ytkb.apps.videos.models import Video
        
    
class VerifyError(Exception):
    pass

class Step(ABC):
    name: ClassVar[str]
    depends_on: ClassVar[tuple[str]]
    max_attempts: ClassVar[int]
    retry_backoff: ClassVar[timedelta]
    lease: ClassVar[timedelta]
    workers: ClassVar[int] = 4          # how many workers should work on a step at the same time
    batch_size: ClassVar[int] = 25      # how many videos a worker gets
    concurrency: ClassVar[int] = 4      # how many videos a worker processes in parallel
    
    @abstractmethod
    async def run(self, video: Video): ...
    
    @abstractmethod
    async def verify(self, video: Video): ...
    
class StepEnum(Enum):
    DOWNLOAD = "DOWNLOAD"
    CHUNK = "CHUNK"