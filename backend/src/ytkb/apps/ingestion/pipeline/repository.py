from datetime import datetime
from typing import TypeAlias

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import aliased, selectinload
from ytkb.apps.ingestion.models import PipelineRun, PipelineStatus, StepRun, StepStatus
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum, Step
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal

StepRunId: TypeAlias = int

class PipelineRepository():
    pipeline: Pipeline
    
    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
    
    async def create_pipeline_run(self, video: Video, pipeline: Pipeline) -> PipelineRun:
        async with SessionLocal() as session:
            pipeline_run = PipelineRun(
                video=video,
                status=PipelineStatus.PENDING,
            )
            
            session.add(pipeline_run)
            await session.flush()
            
            for name in pipeline.steps.keys():
                step_run = StepRun(
                    pipeline_run=pipeline_run,
                    step_name=name,
                    status=StepStatus.PENDING,                    
                )
                session.add(step_run)
            
            await session.commit()
            
        return pipeline_run
    
    async def claim(self, step_name: StepEnum, n: int = 100) -> list[StepRunId]:
        step = self.pipeline.get_step(step_name)
        dep_names = [dep.name for dep in step.depends_on]
        
        dep = aliased(StepRun)
        unfinished_deps = (
            select(dep.id)
            .where(
                dep.pipeline_run_id == StepRun.pipeline_run_id,
                dep.step_name.in_(dep_names),
                dep.status.not_in([StepStatus.DONE])
            )
            .exists()
        )
        
        claimable = or_(
            StepRun.status == StepStatus.PENDING,
            and_(
                StepRun.status == StepStatus.FAILED,
                StepRun.next_attempt_at <= datetime.now(),
            ),
            and_(
                StepRun.status == StepStatus.RUNNING,
                StepRun.claimed_until <= datetime.now(),
            ),  # dead worker
        )
        
        candidates = (
            select(StepRun.id)
            .where(
                StepRun.step_name == step_name,
                claimable,
                StepRun.attempts < step.max_attempts,
                ~unfinished_deps,
            )
            .order_by(StepRun.id)
            .limit(n)
            .with_for_update(skip_locked=True)
        )
        
        stmt = (
            update(StepRun)
            .where(StepRun.id.in_(candidates.scalar_subquery()))
            .values(
                status=StepStatus.RUNNING,
                attempts=StepRun.attempts + 1,
                started_at=datetime.now(),
                claimed_until=datetime.now() + step.lease,
            )
            .returning(StepRun.id)
        )
        
        async with SessionLocal() as session:
            ids = (await session.execute(stmt)).scalars().all()
            await session.commit()
            
        return ids
    
    async def mark_failed(step_run_id: int, step: Step, exc: Exception):
        async with SessionLocal() as session:
            stmt = (
                update(StepRun)
                .where(StepRun.id == step_run_id)
                .values(
                    status=StepStatus.FAILED,
                    error=repr(exc),
                    next_attempt_at=datetime.now() + step.retry_backoff,
                    finished_at=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()
            
    async def mark_running(step_run_id: int):
        async with SessionLocal() as session:
            stmt = (
                update(StepRun)
                .where(StepRun.id == step_run_id)
                .values(
                    status=StepStatus.RUNNING,
                    started_at=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()
            
    async def mark_done(step_run_id: int):
            async with SessionLocal() as session:
                stmt = (
                    update(StepRun)
                    .where(StepRun.id == step_run_id)
                    .values(
                        status=StepStatus.DONE,
                        finished_at=datetime.now(),
                    )
                )
                await session.execute(stmt)
                await session.commit()
    
    async def find_step_run_with_video(step_run_id: int) -> StepRun:
        async with SessionLocal() as session:
            return await session.get_one(
                StepRun, 
                step_run_id, 
                selectinload(StepRun.pipeline_run).selectinload(PipelineRun.video),
            )
            