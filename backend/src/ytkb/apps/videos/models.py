from typing import List, Optional

from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey, String, Integer

from ytkb.core.models import Base

class Channel(Base):
    __tablename__ = "videos__channels"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(150), unique=True)
    handle: Mapped[str] = mapped_column(String(100), unique=True)
    
    videos: Mapped[List["Video"]] = relationship(
        back_populates="channel", 
        cascade="all, delete-orphan",
    )
    
    def __repr__(self):
        return f"Channel(id={self.id}, name={self.name}, url={self.url})"
    
class Video(Base):
    __tablename__ = "videos__videos"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(250))
    content: Mapped[Optional[str]]
    channel_id: Mapped[int] = mapped_column(ForeignKey("videos__channels.id"))

    channel: Mapped["Channel"] = relationship(back_populates="videos")
    chunks: Mapped[List["VideoChunk"]] = relationship(
        back_populates="video", 
        cascade="all, delete-orphan",
    )
    
    def __repr__(self):
        return f"Video(id={self.id}, title={self.title}, url={self.url})"
    
class VideoChunk(Base):
    __tablename__ = "videos__video_chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(Integer())
    content: Mapped[str]
    video_id: Mapped[int] = mapped_column(ForeignKey("videos__videos.id"))

    video: Mapped["Video"] = relationship(back_populates="chunks")
    
    def __repr__(self):
        return f"VideoChunk(id={self.id}, video_id={self.video_id}, position={self.position}, content={self.content[:100]}...)"
    
