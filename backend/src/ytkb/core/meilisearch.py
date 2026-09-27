import meilisearch
from meilisearch.errors import MeilisearchApiError

from pydantic import BaseModel
from ytkb.apps.videos.models import Video
from ytkb.core.config import settings

client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key)
index = None

try:
    index = client.get_index("chunks")
except MeilisearchApiError as exc:
    task = client.create_index("chunks", {"primaryKey": "id"})
    task = client.wait_for_task(task.task_uid)
    if task.status == "failed":
        raise RuntimeError(task.error)
    
    index = client.index("chunks")
    task = index.update_settings({
        "searchableAttributes": ["content", "title"],
        "displayedAttributes": ["id", "video_id", "title", "url", "position", "content"],
    })
    task = client.wait_for_task(task.task_uid)
    if task.status == "failed":
        raise RuntimeError(task.error)
    
assert index is not None

class MeiliSearchChunk(BaseModel):
    id: int
    video_id: int
    title: str
    url: str
    position: int
    content: str

def index_video(chunks: list[MeiliSearchChunk]):
    docs = [c.model_dump() for c in chunks]
    task = index.add_documents(docs)
    task = client.wait_for_task(task.task_uid)
    if task.status == "failed":
        raise RuntimeError(task.error)
    
class SearchResult(BaseModel):
    video_id: int
    chunk_id: int
    
def search(query: str, limit: int = 10, video_id: int|None = None) -> list[SearchResult]:
    params = {"limit": limit}
    if video_id:
        params["filter"] = f"video_id = {video_id}"
    res = index.search(query, params)
    return [SearchResult(video_id=hit["video_id"], chunk_id=hit["id"]) for hit in res["hits"]]