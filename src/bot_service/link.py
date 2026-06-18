from pydantic import BaseModel, HttpUrl
from typing import List


class LinkResponse(BaseModel):
    """Модель ссылки из ответа Scrapper API."""

    id: int
    url: HttpUrl
    tags: List[str] = []
    filters: List[str] = []

    class Config:
        from_attributes = True


class LinkUpdate(BaseModel):
    """Модель обновления от Scrapper"""

    id: int
    url: HttpUrl
    description: str
    tgChatIds: List[int]
