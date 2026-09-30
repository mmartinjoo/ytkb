import logging

from ytkb.apps.ingestion.models import PipelineRun, StepRun
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.repository import PipelineRepository
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
            
            step_run: StepRun = await self.repository.find_step_run_with_video(step_run_id)
            step = self.pipeline.get_step(step_run.step_name)
            
            # another worker might have started this task already
            claimed = await self.repository.mark_running(step_run_id=step_run_id, step=step)
            logger.info(f"step run {step_run_id} is {claimed}")
            if not claimed:
                logger.info(f"step run {step_run_id} not claimable, skipping")
                return
            
            video = step_run.pipeline_run.video
        
            logger.info("----RUN----")
            await step.run(video=video)
            
            async with SessionLocal() as session:                
                video = await session.get_one(Video, video.id)
                
            await step.verify(video=video)
            await self.repository.mark_done(step_run_id=step_run_id)
            logger.info(f"step run {step_run_id} executed")
        except Exception as exc:
            try:
                logger.error(f"step run {step_run_id} failed: {repr(exc)}")
                step_run: StepRun = await self.repository.find_step_run_with_video(step_run_id)
                step = self.pipeline.get_step(step_run.step_name)            
                await self.repository.mark_failed(
                    step_run_id=step_run_id,
                    step=step,
                    exc=exc,
                )
            except Exception as exc:
                logger.error(exc)
            