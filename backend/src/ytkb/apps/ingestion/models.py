from datetime import datetime
import enum
from typing import Optional

from sqlalchemy import ForeignKey, Integer, DateTime, String, Text, Enum, UniqueConstraint, func
from sqlalchemy.orm import Mapped, relationship, mapped_column

from ytkb.apps.videos.models import Video
from ytkb.core.models import Base

class VideoQueueItem(Base):
    __tablename__ = "ingestion__video_queue"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos__videos.id"))
    attempts: Mapped[int] = mapped_column(Integer(), default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        nullable=False,
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        nullable=False,
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claimed_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    video: Mapped["Video"] = relationship()
    
class PipelineStage(enum.Enum):
    DOWNLOAD = "DOWNLOAD"
    CHUNK = "CHUNK"
    TRANSCRIBE = "TRANSCRIBE"
    EMBED = "EMBED"
    INDEX = "INDEX"
    
class PipelineStageStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    
class VideoPipelineItem(Base):
    __tablename__ = "ingestion__video_pipeline"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos__videos.id", ondelete="CASCADE"))

    stage: Mapped[PipelineStage] = mapped_column(
        Enum(PipelineStage, name="pipeline_stage"),
        default=PipelineStage.DOWNLOAD,
        server_default=PipelineStage.DOWNLOAD.value,
    )
    stage_status: Mapped[PipelineStageStatus] = mapped_column(
        Enum(PipelineStageStatus, name="pipeline_stage_status"),
        default=PipelineStageStatus.PENDING,
        server_default=PipelineStageStatus.PENDING.value,
    )
    
    error: Mapped[Optional[str]] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    video: Mapped["Video"] = relationship()
    
class PipelineStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DONE = "DONE"
    
class PipelineRun(Base):
    __tablename__ = "ingestion__pipeline_runs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos__videos.id", ondelete="CASCADE"))
    video: Mapped["Video"] = relationship()
    
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus, name="pipeline_status"),
        default=PipelineStatus.PENDING,
        server_default=PipelineStatus.PENDING.value,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
class StepStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DONE = "DONE"
    
class StepRun(Base):
    __tablename__ = "ingestion__step_runs"
        
    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion__pipeline_runs.id", ondelete="CASCADE"))
    pipeline_run: Mapped["PipelineRun"] = relationship()
    
    step_name: Mapped[str] = mapped_column(String(30))
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, name="step_status"),
        default=StepStatus.PENDING,
        server_default=StepStatus.PENDING.value,
    )
    
    attempts: Mapped[int] = mapped_column(Integer(), default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        nullable=False,
    )
    error: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    claimed_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "step_name"),
    )