from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime
from src.scrapper_service.models.db_models import LinkDB


class ChatRepository(ABC):
    """Абстрактный репозиторий для работы с чатами."""

    @abstractmethod
    async def add(self, chat_id: int) -> bool:
        """Добавляет чат."""
        pass

    @abstractmethod
    async def exists(self, chat_id: int) -> bool:
        """Проверяет существование чата."""
        pass

    @abstractmethod
    async def delete(self, chat_id: int) -> bool:
        """Удаляет чат и все его подписки."""
        pass


class LinkRepository(ABC):
    """Абстрактный репозиторий для работы со ссылками."""

    @abstractmethod
    async def get_or_create(
        self, url: str, resource_type: str, resource_id: str
    ) -> int:
        """Получает или создаёт ссылку. Возвращает ID."""
        pass

    @abstractmethod
    async def get_by_id(self, link_id: int) -> Optional[LinkDB]:
        """Получает ссылку по ID."""
        pass

    @abstractmethod
    async def update_timestamp(self, link_id: int, last_updated: datetime) -> bool:
        """Обновляет время последнего изменения."""
        pass

    @abstractmethod
    async def update_last_checked(self, link_id: int) -> bool:
        """Обновляет время последней проверки."""
        pass

    @abstractmethod
    async def get_all_links(self) -> List[LinkDB]:
        """Возвращает все ссылки (для планировщика)."""
        pass

    @abstractmethod
    async def get_links_batch(self, limit: int, offset: int) -> List[LinkDB]:
        """Возвращает часть ссылок (для планировщика)."""
        pass


class SubscriptionRepository(ABC):
    """Абстрактный репозиторий для работы с подписками."""

    @abstractmethod
    async def add(self, chat_id: int, link_id: int, tags: List[str]) -> bool:
        """Добавляет подписку."""
        pass

    @abstractmethod
    async def remove(self, chat_id: int, link_id: int) -> bool:
        """Удаляет подписку."""
        pass

    @abstractmethod
    async def get_chat_links(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[Dict]:
        """Получает все ссылки чата, опционально фильтруя по тегу."""
        pass

    @abstractmethod
    async def get_link_subscribers(self, link_id: int) -> List[int]:
        """Получает всех подписчиков ссылки."""
        pass


class UpdateRepository(ABC):
    """Абстрактный репозиторий для работы с историей обновлений."""

    @abstractmethod
    async def save(
        self, link_id: int, last_updated: Optional[datetime], had_changes: bool
    ):
        """Сохраняет запись о проверке."""
        pass
