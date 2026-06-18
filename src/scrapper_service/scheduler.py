from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.scrapper_service.logger import logger
from src.scrapper_service.config import settings


class Scheduler:
    """Планировщик периодических задач."""

    def __init__(self, tracker_service):
        self._tracker_service = tracker_service
        self._scheduler = AsyncIOScheduler()

    def start(self):
        """Запускает планировщик."""
        self._scheduler.add_job(
            self._check_links_job,
            trigger=IntervalTrigger(seconds=settings.CHECK_INTERVAL_SECONDS),
            id="check_links",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("scheduler_started", interval=settings.CHECK_INTERVAL_SECONDS)

    async def _check_links_job(self):
        """Задача проверки ссылок."""
        logger.debug("running_check_links_job")
        await self._tracker_service.check_all_links()

    def shutdown(self):
        """Останавливает планировщик."""
        self._scheduler.shutdown()
        logger.info("scheduler_shutdown")
