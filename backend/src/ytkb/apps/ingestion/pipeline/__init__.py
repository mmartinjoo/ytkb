from ytkb.apps.ingestion.pipeline.executor import PipelineExecutor
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.repository import PipelineRepository
from ytkb.apps.ingestion.pipeline.steps import DownloadStep, ChunkStep

PIPELINE = Pipeline([
    DownloadStep(),
    ChunkStep(),
])
repository = PipelineRepository(pipeline=PIPELINE)
executor = PipelineExecutor(
    pipeline=PIPELINE,
    repository=repository,
)