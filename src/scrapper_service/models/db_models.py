from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ChatDB(BaseModel):
    """Модель чата для БД."""

    id: int
    created_at: datetime


class LinkDB(BaseModel):
    """Модель ссылки для БД."""

    id: int
    url: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    last_checked: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SubscriptionDB(BaseModel):
    """Модель подписки для БД."""

    id: int
    chat_id: int
    link_id: int
    tags: List[str] = []
    created_at: datetime


class UpdateDB(BaseModel):
    """Модель обновления для БД."""

    id: int
    link_id: int
    checked_at: datetime
    last_updated: Optional[datetime] = None
    had_changes: bool = False
