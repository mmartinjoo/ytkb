from datetime import datetime, timedelta

from sqlalchemy import select, update
from ytkb.apps.ingestion.models import PipelineStageStatus, VideoPipelineItem, VideoQueueItem
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal


async def mark_many(videos: list[Video], stage_status: PipelineStageStatus, error: str|None = None):
    async with SessionLocal() as session:
        stmt = (
            select(VideoPipelineItem)
            .where(VideoPipelineItem.video_id.in_([v.id for v in videos]))
        )
        res = await session.execute(stmt)
        pipeline_items = res.scalars().all()
        
        for item in pipeline_items:
            guard_stage_status_change(
                from_status=item.stage_status,
                to_status=stage_status,
            )
        
        if stage_status == PipelineStageStatus.FAILED:
            next_attempt_at = datetime.now() + timedelta(hours=1)
        else:
            next_attempt_at = datetime.now()
            
        stmt = (
            update(VideoPipelineItem)
            .where(VideoPipelineItem.video_id.in_([v.id for v in videos]))
            .values(
                stage_status=stage_status,
                error=error,
                updated_at=datetime.now(),
            )
        )
        await session.execute(stmt)
        
        stmt = (
            update(VideoQueueItem)
            .where(VideoQueueItem.video_id.in_([v.id for v in videos]))
            .values(
                next_attempt_at=next_attempt_at,
            )
        )
        await session.execute(stmt)
        await session.commit()
        
def guard_stage_status_change(from_status: PipelineStageStatus, to_status: PipelineStageStatus):
    transitions = {
        PipelineStageStatus.PENDING: [PipelineStageStatus.IN_PROGRESS],
        PipelineStageStatus.IN_PROGRESS: [PipelineStageStatus.FAILED, PipelineStageStatus.DONE],
        PipelineStageStatus.FAILED: [PipelineStageStatus.IN_PROGRESS],
    }
    
    try:
        to_statuses = transitions[from_status]
    except KeyError:
        raise StageStatusTransitionError(f"invalid status: {from_status}")
    
    try:
        to_statuses.index(to_status)
    except ValueError:
        raise StageStatusTransitionError(f"invalid status transition from {from_status} to {to_status}")

class StageStatusTransitionError(Exception):
    pass
    
class StageTransitionError(Exception):
    pass