import uvicorn
from fastapi import APIRouter, FastAPI

from ytkb.core.config import settings
from ytkb.apps.videos import routes as video_router
from ytkb.apps.ingestion import routes as ingestion_router

app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

api = APIRouter(prefix="/api")
api.include_router(video_router.router)
api.include_router(ingestion_router.router)

app.include_router(api)

def main():
    uvicorn.run(
        "ytkb.api:app",
        host="0.0.0.0",
        port=80,
        reload=settings.environment == 'local',
    )