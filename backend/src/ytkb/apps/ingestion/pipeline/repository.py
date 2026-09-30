from datetime import datetime
from typing import TypeAlias
import traceback

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
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
    
    async def enqueue_video(self, session: AsyncSession, video: Video):
        pipeline_run = PipelineRun(
            video=video,
            status=PipelineStatus.PENDING,
        )
        
        session.add(pipeline_run)
        await session.flush()
        
        for name in self.pipeline.steps.keys():
            step_run = StepRun(
                pipeline_run=pipeline_run,
                step_name=name,
                status=StepStatus.PENDING.value,                    
            )
            session.add(step_run)
        
    async def fetch_claimable(self, step_name: StepEnum, n: int = 100) -> list[StepRunId]:
        step = self.pipeline.get_step(step_name.value)
        dep_names = [dep for dep in step.depends_on]
        
        dep = aliased(StepRun)
        unfinished_deps = (
            select(dep.id)
            .where(
                dep.pipeline_run_id == StepRun.pipeline_run_id,
                dep.step_name.in_(dep_names),
                dep.status.not_in([StepStatus.DONE.value])
            )
            .exists()
        )
        
        claimable = or_(
            StepRun.status == StepStatus.PENDING.value,
            and_(
                StepRun.status == StepStatus.FAILED.value,
                StepRun.next_attempt_at <= datetime.now(),
            ),
            and_(
                StepRun.status == StepStatus.RUNNING.value,
                StepRun.claimed_until <= datetime.now(),
            ),  # dead worker
        )
        
        candidates = (
            select(StepRun.id)
            .where(
                StepRun.step_name == step_name.value,
                claimable,
                StepRun.attempts < step.max_attempts,
                ~unfinished_deps,
            )
            .order_by(StepRun.id)
            .limit(n)
            .cte("candidates")
        )
        
        stmt = (
            select(StepRun.id)
            .where(StepRun.id.in_(select(candidates.c.id)))
        )
        
        async with SessionLocal() as session:
            ids = (await session.scalars(stmt)).all()
            
        return ids
    
    async def reset(self, step_run_id: int):
        async with SessionLocal() as session:
            stmt = (
                update(StepRun)
                .where(StepRun.id == step_run_id)
                .values(
                    status=StepStatus.PENDING.value,
                    attempts=0,
                    next_attempt_at=datetime.now(),
                    error=None,
                    claimed_at=None,
                    claimed_until=None,
                    started_at=None,
                    finished_at=None,
                )
            )
            await session.execute(stmt)
            await session.commit()
    
    async def mark_failed(self, step_run_id: int, step: Step, exc: Exception):
        async with SessionLocal() as session:            
            stmt = (
                update(StepRun)
                .where(StepRun.id == step_run_id)
                .values(
                    status=StepStatus.FAILED.value,
                    error=self.format_error(exc),
                    next_attempt_at=datetime.now() + step.retry_backoff,
                    finished_at=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()
            
    async def mark_running(self, step_run_id: int, step: Step) -> bool:
        async with SessionLocal() as session:
            claimable = or_(
                StepRun.status == StepStatus.PENDING.value,
                and_(
                    StepRun.status == StepStatus.FAILED.value,
                    StepRun.next_attempt_at <= datetime.now(),
                ),
                and_(
                    StepRun.status == StepStatus.RUNNING.value,
                    StepRun.claimed_until <= datetime.now(),
                ),  # dead worker
            )
            stmt = (
                update(StepRun)
                .where(
                    StepRun.id == step_run_id,
                    claimable,
                    StepRun.attempts < step.max_attempts,
                )
                .values(
                    status=StepStatus.RUNNING.value,
                    started_at=datetime.now(),
                    claimed_at=datetime.now(),
                    claimed_until=datetime.now() + step.lease,
                    attempts=StepRun.attempts + 1,
                )
                .returning(StepRun.id)
            )
            claimed_id = (await session.execute(stmt)).scalar_one_or_none()
            await session.commit()
            return claimed_id is not None
            
    async def mark_done(self, step_run_id: int):
            async with SessionLocal() as session:
                stmt = (
                    update(StepRun)
                    .where(StepRun.id == step_run_id)
                    .values(
                        status=StepStatus.DONE.value,
                        finished_at=datetime.now(),
                    )
                )
                await session.execute(stmt)
                await session.commit()
    
    async def find_step_run_with_video(self, step_run_id: int) -> StepRun:
        async with SessionLocal() as session:
            return await session.get_one(
                StepRun, 
                step_run_id, 
                options=[selectinload(StepRun.pipeline_run).selectinload(PipelineRun.video)],
            )
            
    def format_error(self, exc: BaseException):
        text = "".join(traceback.format_exception(exc))
        text = text.replace("\x00", "")                                # Postgres rejects NUL
        return text.encode("utf-8", errors="replace").decode("utf-8")  # drops lone surrogates
            