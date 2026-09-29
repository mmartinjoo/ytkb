from ytkb.apps.ingestion.pipeline.executor import PipelineExecutor
from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.repository import PipelineRepository
from ytkb.apps.ingestion.pipeline.steps import DownloadStep, ChunkStep, TranscribeStep, EmbedStep, IndexStep

PIPELINE = Pipeline([
    DownloadStep(),
    ChunkStep(),
    TranscribeStep(),
    EmbedStep(),
    IndexStep(),
])
repository = PipelineRepository(pipeline=PIPELINE)
executor = PipelineExecutor(
    pipeline=PIPELINE,
    repository=repository,
)