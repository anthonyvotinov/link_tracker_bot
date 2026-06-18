from pydantic import BaseModel, Field
from typing import List


class RawUpdate(BaseModel):
    """Входящее сообщение из link.raw-updates."""

    id: int = Field(..., description="ID обновления")
    description: str = Field(..., description="Текст обновления")
    author: str = Field(..., description="Автор обновления")
    tgChatIds: List[int] = Field(..., description="ID чатов для уведомления")


class ProcessedUpdate(BaseModel):
    """Исходящее сообщение в link.processed-updates."""

    id: int = Field(..., description="ID обновления")
    description: str = Field(..., description="Обработанный текст")
    tgChatIds: List[int] = Field(..., description="ID чатов")
    priority: str = Field(default="MEDIUM", description="Приоритет (заглушка)")
