from pydantic import BaseModel
from typing import List, Optional


class RegisterLinkRequest(BaseModel):
    """Запрос на регистрацию ссылки."""

    userId: int
    url: str
    tags: List[str]


class UnregisterLinkRequest(BaseModel):
    """Запрос на удаление ссылки."""

    userId: int
    url: str


class LinkUpdate(BaseModel):
    """Модель обновления ссылки."""

    url: str
    userIds: List[int]
    timestamp: Optional[str] = None
    resourceType: str
