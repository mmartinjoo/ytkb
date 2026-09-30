import asyncio
import logging

from ytkb.apps.ingestion.models import PipelineRun, StepRun
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.repository import PipelineRepository
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum
from ytkb.apps.videos.models import Video
from ytkb.core.db import SessionLocal

logger = logging.getLogger(__name__)

class PipelineExecutor():
    pipeline: Pipeline
    repository: PipelineRepository
    pipeline_run: PipelineRun | None = None
    
    def __init__(self, pipeline: Pipeline, repository: PipelineRepository):
        self.pipeline = pipeline
        self.repository = repository
        
    async def execute(self, step_run_id: int):
        try:
            logger.info(f"executing step run {step_run_id}")
            await self.repository.mark_running(step_run_id=step_run_id)
            
            step_run: StepRun = await self.repository.find_step_run_with_video(step_run_id)
            step = self.pipeline.get_step(step_run.step_name)
            
            video = step_run.pipeline_run.video
        
            await step.run(video=video)
            
            async with SessionLocal() as session:                
                video = await session.get_one(Video, video.id)
                
            await step.verify(video=video)
            await self.repository.mark_done(step_run_id=step_run_id)
            logger.info(f"step run {step_run_id} executed")
        except Exception as exc:
            logger.error(f"step run {step_run_id} failed: {repr(exc)}")
            step_run: StepRun = await self.repository.find_step_run_with_video(step_run_id)
            step = self.pipeline.get_step(step_run.step_name)
            await self.repository.mark_failed(
                step_run_id=step_run_id,
                step=step,
                exc=exc,
            )
            
    async def execute_with_semaphore(self, semaphore: asyncio.Semaphore, step_run_id: int):
        async with semaphore:
            await self.execute(step_run_id)
            
    async def execute_batch(self, step_name: StepEnum) -> int:
        step = self.pipeline.get_step(name=step_name.value)
        step_run_ids = await self.repository.claim(step_name=step_name, n=step.batch_size)
        
        semaphore = asyncio.Semaphore(step.concurrency)
        coros = [self.execute_with_semaphore(semaphore, id) for id in step_run_ids]        
        
        await asyncio.gather(*coros)
        
        return len(step_run_ids)