from datetime import datetime

from sqlalchemy import ForeignKey, Integer, DateTime
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
    
    video: Mapped["Video"] = relationship()