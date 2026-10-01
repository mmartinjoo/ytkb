from fastapi import APIRouter

from sqlalchemy import select
from ytkb.apps.ingestion.models import PipelineRun, StepRun, StepStatus
from ytkb.apps.ingestion.pipeline.steps.step import StepEnum
from ytkb.apps.videos import schemas, services
from ytkb.apps.ingestion.tasks import discover_channel
from ytkb.apps.ingestion.pipeline import repository
from ytkb.core.db import SessionLocal

router = APIRouter(prefix="/channels", tags=["channels"])

@router.post("")
async def create_channel(data: schemas.CreateChannelData):
    channel = await services.create_channel(data)
    discover_channel.delay(channel.id)
    return channel

@router.get("")
async def list_channels():
    return await services.get_channels()

@router.post("/search/")
async def search(data: schemas.SearchData):
    return await services.search(data.question)

@router.get("/test")
async def test():
    stmt = (
        select(StepRun)
        .where(
            StepRun.step_name == "DOWNLOAD",
            StepRun.status != "PENDING"
        )
    )
    async with SessionLocal() as session:
        step_runs = (await session.scalars(stmt)).all()
        
    for sr in step_runs:
        await repository.reset(sr.id)

@router.get("/test2")
async def test2():
    async with SessionLocal() as session:
        pipeline_runs = (await session.scalars(select(PipelineRun))).all()
        step_runs = []
        
        for pipeline in pipeline_runs:
            step_runs.append(StepRun(
                pipeline_run=pipeline,
                step_name=StepEnum.PUBLISH.value,
                status=StepStatus.PENDING.value,                
            ))
        session.add_all(step_runs)
        await session.commit()