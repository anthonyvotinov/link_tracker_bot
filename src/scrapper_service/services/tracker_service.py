# src/services/tracker_service.py
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from clients.github_client import GitHubClient
from clients.stackoverflow_client import StackOverflowClient
from ai_agent_service.logger import logger
from src.config import settings
from src.services.message_sender import MessageSender
from src.repos.base import LinkRepository, SubscriptionRepository
from src.models.db_models import LinkDB


@dataclass
class ChangeInfo:
    """Структура изменения по FR-2.2"""

    title: str
    author: str
    created_at: datetime
    preview: str  # первые 200 символов


class TrackerService:
    def __init__(
        self,
        link_repo: LinkRepository,
        sub_repo: SubscriptionRepository,
        message_sender: MessageSender,
    ):
        self.link_repo = link_repo
        self.sub_repo = sub_repo
        self.message_sender = message_sender
        self._semaphore = asyncio.Semaphore(settings.PARALLEL_WORKERS)
        self.github_client = GitHubClient()
        self.stackoverflow_client = StackOverflowClient()

    async def check_all_links(self) -> Dict[str, Any]:
        """Проверяет ссылки батчами, параллельно внутри батча."""
        batch_size = min(max(settings.BATCH_SIZE, 50), 500)
        offset = 0
        failed_links = []

        while True:
            links = await self.link_repo.get_links_batch(batch_size, offset)
            if not links:
                break

            logger.info("processing_batch", offset=offset, count=len(links))

            tasks = [self._safe_check_link(link) for link in links]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for link, result in zip(links, results):
                if isinstance(result, Exception):
                    logger.error("link_check_failed", url=link.url, error=str(result))
                    failed_links.append({"url": link.url, "error": str(result)})

            offset += batch_size

        if failed_links:
            logger.warning(
                "batch_processing_report",
                failed_count=len(failed_links),
                details=failed_links[:5],
            )

        return {"processed": offset, "failed": len(failed_links)}

    async def _safe_check_link(self, link: LinkDB) -> None:
        """Безопасная проверка одной ссылки (изолирует ошибки)."""
        async with self._semaphore:
            try:
                await self._check_link_internal(link)
            except Exception as e:
                await self.link_repo.update_last_checked(link.id)
                raise e

    async def _check_link_internal(self, link: LinkDB) -> None:
        change = await self._fetch_latest_change(link)
        if not change:
            await self.link_repo.update_last_checked(link.id)
            return

        if link.last_updated and change.created_at <= link.last_updated:
            await self.link_repo.update_last_checked(link.id)
            return

        await self.link_repo.update_last_checked(link.id)
        await self.link_repo.update_timestamp(link.id, change.created_at)

        message = self._format_message(link, change)

        subscribers = await self.sub_repo.get_link_subscribers(link.id)
        await self.message_sender.send_update(link, subscribers, message)

    async def _fetch_latest_change(self, link: LinkDB) -> Optional[ChangeInfo]:
        if link.resource_type == "github" and link.resource_id:
            data = await self.github_client.get_latest_activity(link.resource_id)
            if data:
                return ChangeInfo(**data)

        elif link.resource_type == "stackoverflow" and link.resource_id:
            try:
                qid = int(link.resource_id)
                data = await self.stackoverflow_client.get_latest_answer(qid)
                if data:
                    return ChangeInfo(**data)
            except ValueError:
                pass

        return None

    def _format_message(self, link: LinkDB, change: ChangeInfo) -> str:
        """Форматирует сообщение по FR-2.2"""
        preview = change.preview[: settings.PREVIEW_MAX_LENGTH]
        time_str = change.created_at.strftime("%d.%m.%Y %H:%M")

        if link.resource_type == "github":
            return (
                f"*GitHub Update*\n"
                f"`{link.url}`\n"
                f"*{change.title}*\n"
                f"Автор: {change.author}\n"
                f"Время: {time_str}\n"
                f"Превью: {preview}"
            )
        else:
            return (
                f"*StackOverflow Update*\n"
                f"`{link.url}`\n"
                f"Вопрос: {change.title}\n"
                f"Автор: {change.author}\n"
                f"Время: {time_str}\n"
                f"Превью: {preview}"
            )
