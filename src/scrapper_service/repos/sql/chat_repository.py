import asyncpg
from src.scrapper_service.repos.base import ChatRepository
from src.scrapper_service.logger import logger


class SqlChatRepository(ChatRepository):
    """Реализация ChatRepository через raw SQL."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def add(self, chat_id: int) -> bool:
        async with self._pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO chats (id) VALUES ($1) ON CONFLICT (id) DO NOTHING",
                    chat_id,
                )
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM chats WHERE id = $1)", chat_id
                )
                return result
            except Exception as e:
                logger.error("sql_add_chat_error", chat_id=chat_id, error=str(e))
                raise

    async def exists(self, chat_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM chats WHERE id = $1)", chat_id
            )
            return result

    async def delete(self, chat_id: int) -> bool:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM chats WHERE id = $1", chat_id)
                result = await conn.fetchval(
                    "SELECT NOT EXISTS(SELECT 1 FROM chats WHERE id = $1)", chat_id
                )
                return result
