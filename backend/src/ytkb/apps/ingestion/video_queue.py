from datetime import datetime, timedelta

from sqlalchemy import select, or_, update
from ytkb.apps.ingestion.models import PipelineStage, PipelineStageStatus, VideoPipelineItem, VideoQueueItem
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal

MAX_ATTEMPTS = 10

class EmptyQueueError(Exception):
    pass

async def claim(stage: PipelineStage, n: int = 100) -> list[Video]:
    stmt = (
        select(Video)
        .select_from(VideoQueueItem)
        .join(VideoPipelineItem, VideoPipelineItem.video_id == VideoQueueItem.video_id)
        .join(Video, Video.id == VideoQueueItem.video_id)
        .where(
            VideoPipelineItem.stage == stage,
            VideoPipelineItem.stage_status.in_([
                PipelineStageStatus.PENDING,
                PipelineStageStatus.FAILED,
            ]),
            VideoQueueItem.attempts < MAX_ATTEMPTS,
            VideoQueueItem.next_attempt_at <= datetime.now(),
            or_(
                VideoPipelineItem.stage == stage,
                VideoPipelineItem.stage_status == PipelineStageStatus.IN_PROGRESS,
                VideoQueueItem.attempts < MAX_ATTEMPTS,
                VideoQueueItem.next_attempt_at <= datetime.now(),
                VideoQueueItem.claimed_until <= datetime.now(),
            ),
        )
        .order_by(VideoQueueItem.queued_at.desc())
        .limit(n)
        .with_for_update(
            of=VideoQueueItem,
            skip_locked=True,
        )
    )
    
    async with SessionLocal() as session:
        res = await session.execute(stmt)
        videos = res.scalars().all()
        
    if len(videos) == 0:
        raise EmptyQueueError()
    
    stmt = (
        update(VideoQueueItem)
        .where(VideoQueueItem.video_id.in_([v.id for v in videos]))
        .values(
            claimed_at=datetime.now(),
            claimed_until=datetime.now() + timedelta(minutes=30),
            attempts=VideoQueueItem.attempts + 1,
            next_attempt_at=datetime.now() + timedelta(minutes=45),
        )
    )
    
    async with SessionLocal() as session:
        await session.execute(stmt)
        await session.commit()
        
    return videos