from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"
    
    video_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    channel_id = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False)
    description = Column(Text)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OpenAIArticle(Base):
    __tablename__ = "openai_articles"
    
    guid = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnthropicArticle(Base):
    __tablename__ = "anthropic_articles"
    
    guid = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    category = Column(String, nullable=True)
    markdown = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Digest(Base):
    __tablename__ = "digests"
    
    id = Column(String, primary_key=True)
    article_type = Column(String, nullable=False)
    article_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DigestRecipient(Base):
    """Legacy: optional fallback for digest sends. Prefer :class:`Subscriber` with ``is_subscribed``."""

    __tablename__ = "digest_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(320), nullable=False, unique=True)
    first_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscriber(Base):
    """Public signup / demo requests. Maps to ``subscribers``."""

    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    first_name = Column(String(120), nullable=True)
    last_name = Column(String(120), nullable=True)
    is_subscribed = Column(Boolean, nullable=False, default=False)
    has_requested_demo = Column(Boolean, nullable=False, default=False)

