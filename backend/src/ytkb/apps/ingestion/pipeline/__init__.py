from ytkb.apps.ingestion.pipeline.pipeline import Pipeline
from ytkb.apps.ingestion.pipeline.steps import DownloadStep, ChunkStep

PIPELINE = Pipeline([
    DownloadStep(),
    ChunkStep(),
])