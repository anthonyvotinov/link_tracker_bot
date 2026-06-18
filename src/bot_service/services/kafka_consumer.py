import asyncio
import json
from aiokafka import AIOKafkaConsumer
from src.bot_service.config import settings
from src.bot_service.logger import logger


class KafkaUpdateConsumer:
    """Kafka consumer для получения обработанных обновлений."""

    def __init__(self, bot):
        self.bot = bot
        self._consumer = None
        self._task = None

    async def start(self):
        if settings.MESSAGE_SOURCE != "kafka":
            logger.info("kafka_consumer_skipped", reason="MESSAGE_SOURCE is not kafka")
            return

        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("kafka_consumer_started", topic=settings.KAFKA_TOPIC)

    async def _consume_loop(self):
        try:
            async for msg in self._consumer:
                await self._process_message(msg.value)
        except asyncio.CancelledError:
            logger.info("kafka_consumer_loop_cancelled")
        except Exception as e:
            logger.error("kafka_consumer_loop_error", error=str(e))

    async def _process_message(self, data: dict):
        chat_ids = data.get("tgChatIds", [])
        description = data.get("description", "")
        url = data.get("url", "Unknown")
        priority = data.get("priority", "MEDIUM")

        message = (
            f"<b>[{priority}] Новое обновление!</b>\n\n"
            f"{description}\n"
            f"<a href='{url}'>Открыть ссылку</a>"
        )

        for chat_id in chat_ids:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.error("telegram_send_failed", chat_id=chat_id, error=str(e))

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer:
            await self._consumer.stop()
        logger.info("kafka_consumer_stopped")
