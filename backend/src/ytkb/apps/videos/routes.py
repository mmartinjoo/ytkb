from fastapi import APIRouter

from ytkb.apps.videos import schemas, services

router = APIRouter(prefix="/channels", tags=["channels"])

@router.post("")
async def create_channel(data: schemas.CreateChannelData):
    return await services.create_channel(data)

@router.get("")
async def list_channels():
    return await services.get_channels()