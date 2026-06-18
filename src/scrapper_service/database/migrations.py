import asyncpg
from pathlib import Path
from src.scrapper_service.config import settings
from src.scrapper_service.logger import logger


async def run_migrations():
    """Выполняет миграции базы данных из SQL файлов."""
    logger.info("running_migrations")

    migrations_dir = Path(__file__).resolve().parent / "migrations"

    if not migrations_dir.exists():
        logger.warning(f"migrations_directory_not_found: {migrations_dir}")
        migrations_dir.mkdir(parents=True, exist_ok=True)

    try:
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD.get_secret_value(),
            database=settings.DB_NAME,
        )
    except Exception as e:
        logger.error(f"database_connection_failed: {e}")
        raise

    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                filename VARCHAR(255)
            )
        """
        )

        applied = set()
        rows = await conn.fetch("SELECT version, filename FROM schema_migrations")
        for row in rows:
            applied.add(row["version"])

        sql_files = sorted(migrations_dir.glob("*.sql"), key=lambda x: x.name)

        for sql_file in sql_files:
            try:
                version = int(sql_file.stem.split("_")[0])
            except (ValueError, IndexError):
                logger.warning(f"invalid_migration_filename: {sql_file.name}")
                continue

            if version in applied:
                logger.debug(f"migration_already_applied: {sql_file.name}")
                continue

            logger.info(f"applying_migration: {sql_file.name}")
            sql = sql_file.read_text(encoding="utf-8")

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES ($1, $2)",
                    version,
                    sql_file.name,
                )
            logger.info(f"migration_applied: {sql_file.name}")

        logger.info("migrations_completed")

    except Exception as e:
        logger.error(f"migration_failed: {e}")
        raise
    finally:
        await conn.close()
