import asyncpg
from datetime import datetime
from typing import Optional, List
from src.scrapper_service.repos.base import LinkRepository
from src.scrapper_service.models.db_models import LinkDB
from src.scrapper_service.logger import logger


class SqlLinkRepository(LinkRepository):
    """Реализация LinkRepository через raw SQL."""

    async def get_all_links(self) -> List[LinkDB]:
        """Возвращает все ссылки из БД (для планировщика)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, url, resource_type, resource_id,
                       last_checked, last_updated, created_at, updated_at
                FROM links
                ORDER BY id
            """
            )
        logger.debug("sql_get_all_links", count=len(rows))
        return [LinkDB(**row) for row in rows]

    async def get_links_batch(self, limit: int, offset: int) -> List[LinkDB]:
        """Возвращает батч ссылок с пагинацией (для планировщика)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, url, resource_type, resource_id,
                       last_checked, last_updated, created_at, updated_at
                FROM links
                ORDER BY id
                LIMIT $1 OFFSET $2
            """,
                limit,
                offset,
            )
        logger.debug("sql_get_links_batch", limit=limit, offset=offset, count=len(rows))
        return [LinkDB(**row) for row in rows]

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_or_create(
        self, url: str, resource_type: str, resource_id: str
    ) -> int:
        async with self._pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM links WHERE url = $1", url)
            if existing:
                return existing["id"]

            link_id = await conn.fetchval(
                """
                INSERT INTO links (url, resource_type, resource_id, created_at, updated_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
                """,
                url,
                resource_type,
                resource_id,
            )
            logger.info("sql_link_created", url=url, link_id=link_id)
            return link_id

    async def get_by_id(self, link_id: int) -> Optional[LinkDB]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, url, resource_type, resource_id,
                       last_checked, last_updated, created_at, updated_at
                FROM links WHERE id = $1
                """,
                link_id,
            )
            if not row:
                return None
            return LinkDB(**row)

    async def update_timestamp(self, link_id: int, last_updated: datetime) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                """
                UPDATE links 
                SET last_updated = $2, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id
                """,
                link_id,
                last_updated,
            )
            return result is not None

    async def update_last_checked(self, link_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                """
                UPDATE links 
                SET last_checked = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id
                """,
                link_id,
            )
            return result is not None
