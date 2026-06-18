from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.scrapper_service.repos.base import ChatRepository
from src.scrapper_service.repos.orm.models import Chat
from src.scrapper_service.logger import logger


class OrmChatRepository(ChatRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, chat_id: int) -> bool:
        try:
            chat = Chat(id=chat_id)
            self._session.add(chat)
            await self._session.flush()
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            logger.error("orm_add_chat_failed", chat_id=chat_id, error=str(e))
            return False

    async def exists(self, chat_id: int) -> bool:
        result = await self._session.execute(select(Chat).where(Chat.id == chat_id))
        return result.scalar_one_or_none() is not None

    async def delete(self, chat_id: int) -> bool:
        try:
            result = await self._session.execute(select(Chat).where(Chat.id == chat_id))
            chat = result.scalar_one_or_none()
            if chat:
                await self._session.delete(chat)
                await self._session.flush()
                await self._session.commit()
                return True
            return False
        except Exception as e:
            await self._session.rollback()
            logger.error("orm_delete_chat_failed", chat_id=chat_id, error=str(e))
            return False
