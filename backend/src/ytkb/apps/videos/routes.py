from fastapi import APIRouter

from sqlalchemy import select
from ytkb.apps.ingestion.models import StepRun
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

@router.get("/test")
async def test():
    stmt = (
        select(StepRun)
        .where(
            StepRun.step_name == "CHUNK",
            StepRun.status != "PENDING"
        )
    )
    async with SessionLocal() as session:
        step_runs = (await session.scalars(stmt)).all()
        
    for sr in step_runs:
        await repository.reset(sr.id)
