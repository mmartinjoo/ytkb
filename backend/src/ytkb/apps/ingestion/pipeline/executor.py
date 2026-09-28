from ytkb.apps.ingestion.models import PipelineRun
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.repository import PipelineRepository
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum
from ytkb.apps.videos.models import Video


class PipelineExecutor():
    pipeline: Pipeline
    repository: PipelineRepository
    pipeline_run: PipelineRun | None = None
    
    def __init__(self, pipeline: Pipeline, repository: PipelineRepository):
        self.pipeline = pipeline
        self.repository = repository
        
    async def create_pipeline_run(self, video: Video):
        self.pipeline_run = await self.repository.create_pipeline_run(video, self.pipeline)
        
    async def execute(step_run_id: int): ...            # run & verify
    async def execute_ready(step_name: StepEnum): ...   # claim + execute
        