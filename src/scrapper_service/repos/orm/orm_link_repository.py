from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
from src.scrapper_service.repos.base import LinkRepository
from src.scrapper_service.repos.orm.models import Link
from src.scrapper_service.models.db_models import LinkDB
from src.scrapper_service.logger import logger


class OrmLinkRepository(LinkRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_or_create(
        self, url: str, resource_type: str, resource_id: str
    ) -> int:
        try:
            result = await self._session.execute(select(Link).where(Link.url == url))
            link = result.scalar_one_or_none()
            if link:
                return link.id

            new_link = Link(
                url=url, resource_type=resource_type, resource_id=resource_id
            )
            self._session.add(new_link)
            await self._session.flush()
            await self._session.commit()
            return new_link.id
        except Exception as e:
            await self._session.rollback()
            logger.error("orm_link_create_failed", url=url, error=str(e))
            raise

    async def get_by_id(self, link_id: int) -> Optional[LinkDB]:
        result = await self._session.execute(select(Link).where(Link.id == link_id))
        link = result.scalar_one_or_none()
        if not link:
            return None
        return self._map_to_db(link)

    async def update_timestamp(self, link_id: int, last_updated: datetime) -> bool:
        try:
            result = await self._session.execute(select(Link).where(Link.id == link_id))
            link = result.scalar_one_or_none()
            if not link:
                return False

            link.last_updated = last_updated
            link.updated_at = datetime.now()
            await self._session.flush()
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error("orm_update_timestamp_failed", link_id=link_id, error=str(e))
            return False

    async def update_last_checked(self, link_id: int) -> bool:
        try:
            result = await self._session.execute(select(Link).where(Link.id == link_id))
            link = result.scalar_one_or_none()
            if not link:
                return False

            link.last_checked = datetime.now()
            await self._session.flush()
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error(
                "orm_update_last_checked_failed", link_id=link_id, error=str(e)
            )
            return False

    async def get_all_links(self) -> List[LinkDB]:
        result = await self._session.execute(select(Link))
        return [self._map_to_db(link) for link in result.scalars().all()]

    async def get_links_batch(self, limit: int, offset: int) -> List[LinkDB]:
        stmt = select(Link).order_by(Link.id).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._map_to_db(link) for link in result.scalars().all()]

    def _map_to_db(self, link: Link) -> LinkDB:
        return LinkDB(
            id=link.id,
            url=link.url,
            resource_type=link.resource_type,
            resource_id=link.resource_id,
            last_checked=link.last_checked,
            last_updated=link.last_updated,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )
