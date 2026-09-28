from datetime import datetime
from pathlib import Path
import subprocess
import logging

import yt_dlp
from googleapiclient.discovery import build, Resource

from pydantic import BaseModel
from ytkb.core.config import settings

logger = logging.getLogger(__name__)

class YoutubeVideo(BaseModel):
    id: str
    title: str
    url: str
    published_at: datetime

def get_all_videos(handle: str, max_pages: int = 2) -> list[YoutubeVideo]:
    youtube = _get_youtube()
    playlist_id = _get_uploads_playlist_id(
        youtube=youtube,
        handle=handle,
    )
    
    videos = []
    page_token = None
    n = 0
    
    while True and n <= max_pages:
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
        
        if n >= max_pages:
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

class DownloadedVideo(BaseModel):
    base_path: str
    chunks_path: str
    video_path: str
    audio_path: str
    
    @staticmethod
    def create_for_video(video_id: int) -> "DownloadedVideo":
        base_path = f"/tmp/{video_id}"
        downloaded_video = DownloadedVideo(
            base_path=base_path,
            chunks_path=f"{base_path}/chunks",
            video_path=f"{base_path}/{video_id}.mp4",
            audio_path=f"{base_path}/{video_id}.m4a",
        )
        
        Path(downloaded_video.base_path).mkdir(exist_ok=True, parents=True)
        Path(downloaded_video.chunks_path).mkdir(exist_ok=True, parents=True)
        return downloaded_video

def download_video(video_id: int, url: str) -> DownloadedVideo:
    logger.info(f"downloading {url}")
    
    downloaded_video = DownloadedVideo.create_for_video(video_id)
    assert Path(downloaded_video.base_path).exists()
    
    options = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "merge_output_format": "mp4",
        "outtmpl": f"{downloaded_video.base_path}/{video_id}" + ".%(ext)s",
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url=url, download=True)
        
    downloaded_video.video_path = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp4"    
    downloaded_video.audio_path = downloaded_video.audio_path.rsplit(".", 1)[0] + ".m4a"
    
    logger.info(f"video path={downloaded_video.video_path}")
    logger.info(f"audio path={downloaded_video.audio_path}")    

    subprocess.run([
        "ffmpeg", 
        "-i", 
        downloaded_video.video_path,
        "-vn",          # no video in the audio output
        "-c:a", "copy", # copy audio, do not re-encode
        downloaded_video.audio_path,
    ], check=True)
    
    assert Path(downloaded_video.video_path).exists()
    assert Path(downloaded_video.audio_path).exists()
    
    return downloaded_video
            
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