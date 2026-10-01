import json
import boto3
from ytkb.core.config import settings


s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
)

try:
    s3.head_bucket(Bucket=settings.s3_bucket)
except Exception:
    s3.create_bucket(Bucket=settings.s3_bucket)
    
def put_audio_file(video_id: int, data: bytes) -> str:
    key = f"videos/{video_id}/{video_id}.m4a"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType="audio/mp4"
    )
    
    return key

def put_audio_chunk_file(video_id: int, data: bytes, position: int) -> str:
    key = f"videos/{video_id}/chunks/{video_id}_{position}.m4a"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType="audio/mp4"
    )
    
    return key

def get_file(key: str) -> bytes:
    resp = s3.get_object(
        Bucket=settings.s3_bucket,
        Key=key,
    )
    return resp["Body"].read()

def exists(key: str) -> bool:
    try:
        s3.head_object(
            Bucket=settings.s3_bucket,
            Key=key,
        )
        return True
    except Exception:
        return False
    
def empty(key: str) -> bool:
    if not exists(key=key):
        return True
    
    resp = s3.head_object(
        Bucket=settings.s3_bucket,
        Key=key,
    )
    
    return resp["ContentLength"] == 0