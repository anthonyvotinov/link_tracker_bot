import asyncpg
from typing import List, Dict, Optional
from src.scrapper_service.repos.base import SubscriptionRepository
from src.scrapper_service.logger import logger


class SqlSubscriptionRepository(SubscriptionRepository):
    """Реализация SubscriptionRepository через raw SQL."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def add(self, chat_id: int, link_id: int, tags: List[str]) -> bool:
        async with self._pool.acquire() as conn:
            try:
                result = await conn.fetchval(
                    """
                    INSERT INTO subscriptions (chat_id, link_id, tags)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (chat_id, link_id) DO UPDATE
                    SET tags = EXCLUDED.tags
                    RETURNING id
                    """,
                    chat_id,
                    link_id,
                    tags,
                )
                logger.info("sql_subscription_added", chat_id=chat_id, link_id=link_id)
                return result is not None
            except Exception as e:
                logger.error("sql_add_subscription_error", error=str(e))
                raise

    async def remove(self, chat_id: int, link_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                """
                DELETE FROM subscriptions
                WHERE chat_id = $1 AND link_id = $2
                RETURNING id
                """,
                chat_id,
                link_id,
            )
            return result is not None

    async def get_chat_links(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[Dict]:
        async with self._pool.acquire() as conn:
            if tag:
                # Фильтруем по тегу (поиск в массиве)
                rows = await conn.fetch(
                    """
                    SELECT l.id, l.url, l.last_updated, s.tags
                    FROM subscriptions s
                    JOIN links l ON s.link_id = l.id
                    WHERE s.chat_id = $1 AND $2 = ANY(s.tags)
                    """,
                    chat_id,
                    tag,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT l.id, l.url, l.last_updated, s.tags
                    FROM subscriptions s
                    JOIN links l ON s.link_id = l.id
                    WHERE s.chat_id = $1
                    """,
                    chat_id,
                )

            return [dict(row) for row in rows]

    async def get_link_subscribers(self, link_id: int) -> List[int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT chat_id FROM subscriptions WHERE link_id = $1", link_id
            )
            return [row["chat_id"] for row in rows]
