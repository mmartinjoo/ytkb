from fastapi import APIRouter

from ytkb.apps.videos import schemas, services
from ytkb.apps.ingestion.tasks import discover_channel
from ytkb.apps.ingestion.pipeline import repository

router = APIRouter(prefix="/channels", tags=["channels"])

@router.post("")
async def create_channel(data: schemas.CreateChannelData):
    channel = await services.create_channel(data)
    discover_channel.delay(channel.id)
    return channel

@router.get("")
async def list_channels():
    return await services.get_channels()

@router.get("/test/{step_run_id}")
async def test(step_run_id: int):
    await repository.reset(step_run_id)
