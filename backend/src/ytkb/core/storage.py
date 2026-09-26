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
    
def put_video_file(video_id: int, data: bytes) -> str:
    key = f"videos/{video_id}/{video_id}.mp4"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType="video/mp4"
    )
    
    return key

def put_audio_file(video_id: int, data: bytes) -> str:
    key = f"videos/{video_id}/{video_id}.m4a"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType="audio/mp4"
    )
    
    return key