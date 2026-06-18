from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional


class ApiErrorResponse(BaseModel):
    """Ответ с ошибкой API."""

    description: str = Field(..., description="Описание ошибки")
    code: str = Field(..., description="Код ошибки")
    exceptionName: Optional[str] = Field(None, description="Имя исключения")
    exceptionMessage: Optional[str] = Field(None, description="Сообщение исключения")
    stacktrace: Optional[List[str]] = Field(None, description="Стек вызовов")


class LinkUpdate(BaseModel):
    """Модель обновления ссылки."""

    id: int = Field(..., description="ID ссылки")
    url: HttpUrl = Field(..., description="URL отслеживаемой ссылки")
    description: str = Field(..., description="Описание обновления")
    tgChatIds: List[int] = Field(..., description="ID чатов для уведомления")
