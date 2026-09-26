from datetime import datetime

from googleapiclient.discovery import build, Resource

from pydantic import BaseModel
from ytkb.core.config import settings

class YoutubeVideo(BaseModel):
    id: str
    title: str
    url: str
    published_at: datetime

def get_all_videos(handle: str) -> list[YoutubeVideo]:
    youtube = _get_youtube()
    playlist_id = _get_uploads_playlist_id(
        youtube=youtube,
        handle=handle,
    )
    
    videos = []
    page_token = None
    n = 0
    
    while True and n <= 2:
        response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        
        for item in response["items"]:
            video_id = item["contentDetails"]["videoId"]
            
            videos.append(YoutubeVideo(
                id=video_id,
                title=item["snippet"]["title"],
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=item["contentDetails"].get("videoPublishedAt"),
            ))
            
        page_token = response.get("nextPageToken")
        
        if not page_token:
            return videos
        
        n += 1
        
def get_latest_videos(handle: str) -> list[YoutubeVideo]:
    youtube = _get_youtube()
    playlist_id = _get_uploads_playlist_id(
        youtube=youtube,
        handle=handle,
    )
    
    videos = []
    page_token = None
    
    response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=50,
        pageToken=page_token,
    ).execute()
    
    for item in response["items"]:
        video_id = item["contentDetails"]["videoId"]
        
        videos.append(YoutubeVideo(
            id=video_id,
            title=item["snippet"]["title"],
            url=f"https://www.youtube.com/watch?v={video_id}",
            published_at=item["contentDetails"].get("videoPublishedAt"),
        ))
        
    return videos
            
def _get_youtube() -> Resource:
    return build(
        serviceName="youtube", 
        version="v3", 
        developerKey=settings.youtube_api_key,
        cache_discovery=False,
    )
    
def _get_uploads_playlist_id(youtube: Resource, handle: str) -> str:
    response = youtube.channels().list(
        part="contentDetails",
        forHandle=handle
    ).execute()
    
    items = response.get("items", [])
    if not items:
        raise ValueError(f"playlist not found for {handle}")
    
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]