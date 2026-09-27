import meilisearch

from pydantic import BaseModel
from ytkb.apps.videos.models import Video
from ytkb.core.config import settings

client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key)
task = client.create_index("chunks", {"primaryKey": "id"})
client.wait_for_task(task.task_uid)
index = client.index("chunks")

task = index.update_settings({
    "searchableAttributes": ["content", "title"],
    "displayedAttributes": ["id", "video_id", "title", "url", "position", "content"],
})
client.wait_for_task(task.task_uid)

def index_video(video: Video):
    assert len(video.chunks) != 0
    
    docs: list[dict] = []
    for chunk in video.chunks:
        docs.append({
            "id": {chunk.id},
            "video_id": video.id,
            "title": video.title,
            "url": video.url,
            "position": chunk.position,
            "content": chunk.content_without_timestamps,    
        })
        
    task = index.add_documents(docs)
    client.wait_for_task(task.task_uid)
    
class SearchResult(BaseModel):
    video_id: int
    chunk_id: int
    
def search(query: str, limit: int = 10, video_id: int|None = None) -> list[SearchResult]:
    params = {"limit": limit}
    if video_id:
        params["filter"] = f"video_id = {video_id}"
    res = index.search(query, params)
    return [SearchResult(video_id=hit["video_id"], chunk_id=hit["id"]) for hit in res["hits"]]