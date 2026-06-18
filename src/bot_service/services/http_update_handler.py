from telegram import Bot
from telegram.error import TelegramError

from src.bot_service.api.models import LinkUpdate
from src.bot_service.logger import logger


class UpdateHandler:
    """Обработчик обновлений от Scrapper сервиса."""

    def __init__(self):
        self.bot = None

    def init_bot(self, telegram_bot: Bot):
        """Инициализация с Telegram ботом."""
        self.bot = telegram_bot

    async def process_update(self, update: LinkUpdate):
        """Обрабатывает обновление и отправляет уведомления пользователям."""
        if not self.bot:
            logger.error("bot_not_initialized")
            return

        logger.info("processing_update", link_id=update.id, url=str(update.url))

        # Формируем сообщение для пользователей
        message = self._format_update_message(update)

        # Отправляем каждому пользователю
        for chat_id in update.tgChatIds:
            try:
                await self.bot.send_message(
                    chat_id=chat_id, text=message, disable_web_page_preview=True
                )
                logger.info("notification_sent", chat_id=chat_id, link_id=update.id)
            except TelegramError as e:
                logger.error(
                    "failed_to_send_notification",
                    chat_id=chat_id,
                    link_id=update.id,
                    error=str(e),
                )

    def _format_update_message(self, update: LinkUpdate) -> str:
        """Форматирует сообщение об обновлении."""
        return (
            f"🔔 **Обнаружены изменения!**\n\n"
            f"Ссылка: {update.url}\n"
            f"Что изменилось: {update.description}\n\n"
            f"Используйте /list чтобы посмотреть все отслеживаемые ссылки."
        )


# Глобальный экземпляр
update_handler = UpdateHandler()
