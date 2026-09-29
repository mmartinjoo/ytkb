import asyncio

from ytkb.apps.ingestion.pipeline import executor
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum

def download_batch():
    asyncio.run(executor.execute_batch(StepEnum.DOWNLOAD))    

def chunk_batch():
    asyncio.run(executor.execute_batch(StepEnum.CHUNK))