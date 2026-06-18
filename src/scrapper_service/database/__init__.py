import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import settings, AccessType
from ai_agent_service.logger import logger


class DatabaseFactory:
    """Фабрика для создания репозиториев."""

    def __init__(self):
        self._pool = None
        self._engine = None
        self._session_factory = None
        self.access_type = settings.ACCESS_TYPE

    async def init(self):
        """Инициализирует подключение к БД."""
        if self.access_type == AccessType.SQL:
            self._pool = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD.get_secret_value(),
                min_size=5,
                max_size=20,
            )
            logger.info("SQL connection pool created")
        else:
            # ORM
            self._engine = create_async_engine(
                settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
                echo=True,
            )
            self._session_factory = sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("ORM engine created")

    async def close(self):
        """Закрывает подключения."""
        if self._pool:
            await self._pool.close()
        if self._engine:
            await self._engine.dispose()

    def get_session(self) -> AsyncSession:
        """Возвращает сессию для ORM."""
        if self.access_type != AccessType.ORM:
            raise RuntimeError("ORM not enabled")
        return self._session_factory()

    def get_pool(self) -> asyncpg.Pool:
        """Возвращает пул соединений для SQL."""
        if self.access_type != AccessType.SQL:
            raise RuntimeError("SQL not enabled")
        return self._pool


db_factory = DatabaseFactory()
