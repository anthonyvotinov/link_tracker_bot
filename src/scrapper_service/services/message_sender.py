from abc import ABC, abstractmethod
from src.models.db_models import LinkDB
from typing import List


class MessageSender(ABC):
    """Интерфейс для отправки уведомлений"""

    @abstractmethod
    async def send_update(
        self, link: LinkDB, subscribers: List[int], message: str
    ) -> None:
        """Отправляет сформированное сообщение подписчикам."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Инициализирует соединение"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Закрывает соединение"""
        pass
