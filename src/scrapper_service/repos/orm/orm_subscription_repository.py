from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Dict, Optional
from src.scrapper_service.repos.base import SubscriptionRepository
from src.scrapper_service.repos.orm.models import Subscription, Link
from src.scrapper_service.logger import logger


class OrmSubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, chat_id: int, link_id: int, tags: List[str]) -> bool:
        try:
            subscription = Subscription(chat_id=chat_id, link_id=link_id, tags=tags)
            self._session.add(subscription)
            await self._session.flush()
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error(
                "orm_add_subscription_failed",
                chat_id=chat_id,
                link_id=link_id,
                error=str(e),
            )
            return False

    async def remove(self, chat_id: int, link_id: int) -> bool:
        try:
            result = await self._session.execute(
                delete(Subscription).where(
                    Subscription.chat_id == chat_id, Subscription.link_id == link_id
                )
            )
            await self._session.flush()
            await self._session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self._session.rollback()
            logger.error(
                "orm_remove_subscription_failed",
                chat_id=chat_id,
                link_id=link_id,
                error=str(e),
            )
            return False

    async def get_chat_links(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[Dict]:
        query = (
            select(Subscription, Link)
            .join(Link, Subscription.link_id == Link.id)
            .where(Subscription.chat_id == chat_id)
        )
        if tag:
            query = query.where(Subscription.tags.contains([tag]))

        result = await self._session.execute(query)
        return [
            {
                "id": link.id,
                "url": link.url,
                "last_updated": link.last_updated,
                "tags": sub.tags,
            }
            for sub, link in result.all()
        ]

    async def get_link_subscribers(self, link_id: int) -> List[int]:
        result = await self._session.execute(
            select(Subscription.chat_id).where(Subscription.link_id == link_id)
        )
        return [row[0] for row in result.all()]
