from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from ytkb.core.config import settings

client = QdrantClient(f"http://{settings.qdrant_host}:{settings.qdrant_port}")

def create_collection_if_not_exists(collection_name: str):
    if client.collection_exists(collection_name):
        return
    
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.qdrant_vector_dims,
            distance=Distance.COSINE,
        ),
    )

def upsert(collection_name: str, vectors, video_id: int, video_chunk_ids: list[int]):
    assert video_id is not None
    assert len(video_chunk_ids) != 0
    
    create_collection_if_not_exists(collection_name)
    
    points = []
    for idx, vector in enumerate(vectors):
        points.append(PointStruct(
            id=video_chunk_ids[idx],
            vector=vector,
            payload={
                "video_id": video_id,
                "video_chunk_id": video_chunk_ids[idx],
            },
        ))
    
    client.upsert(
        collection_name=collection_name,
        points=points,
    )
    
def search(collection_name: str, vectors):
    return client.query_points(
        collection_name=collection_name, 
        query=vectors,
        with_payload=True,
    )