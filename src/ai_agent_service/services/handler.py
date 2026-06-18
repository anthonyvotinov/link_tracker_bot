import json
import asyncio
import time
from collections import defaultdict
from typing import Dict, List
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.ai_agent_service.config import settings
from src.ai_agent_service.models import RawUpdate
from src.ai_agent_service.services.filter import UpdateFilter
from src.ai_agent_service.services.summarizer import Summarizer
from src.ai_agent_service.logger import logger


class Handler:
    """Оркестратор: читает, фильтрует, суммаризирует, приоритизирует, группирует и публикует."""

    def __init__(self):
        self.filter = UpdateFilter()
        self.summarizer = Summarizer()
        self.consumer = None
        self.producer = None
        self._running = False
        self._process_task = None
        self._flush_task = None

        self._buffer: Dict[int, List[dict]] = defaultdict(list)
        self._buffer_timestamps: Dict[int, float] = {}
        self._lock = asyncio.Lock()

    async def start(self):
        """Запуск consumer, producer и фоновых задач."""
        servers = settings.KAFKA_BOOTSTRAP_SERVERS.split(",")

        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_INPUT_TOPIC,
            bootstrap_servers=servers,
            group_id=settings.KAFKA_CONSUMER_GROUP,
            auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
        )

        self.producer = AIOKafkaProducer(
            bootstrap_servers=servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        await self.consumer.start()
        await self.producer.start()

        self._running = True
        self._process_task = asyncio.create_task(self._process_loop())
        self._flush_task = asyncio.create_task(self._flush_loop())

        logger.info(
            "ai_agent_started",
            input_topic=settings.KAFKA_INPUT_TOPIC,
            output_topic=settings.KAFKA_OUTPUT_TOPIC,
        )

    async def _process_loop(self):
        """Основной цикл чтения из Kafka."""
        try:
            async for msg in self.consumer:
                try:
                    await self._process_message(msg.value)
                except Exception as e:
                    logger.error(
                        "message_processing_error", error=str(e), msg=msg.value
                    )
        except asyncio.CancelledError:
            logger.info("process_loop_cancelled")
        except Exception as e:
            logger.error("process_loop_error", error=str(e))

    def _get_priority(self, description: str) -> str:
        """Определяет приоритет на основе ключевых слов."""
        desc_lower = description.lower()

        if any(
            kw.lower() in desc_lower for kw in settings.PRIORITIZATION_HIGH_KEYWORDS
        ):
            return "HIGH"
        if any(kw.lower() in desc_lower for kw in settings.PRIORITIZATION_LOW_KEYWORDS):
            return "LOW"
        return "MEDIUM"

    def _priority_value(self, priority: str) -> int:
        """Возвращает числовое значение приоритета для сравнения."""
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(priority, 2)

    async def _process_message(self, data: dict):
        """Обработка одного сообщения: фильтрация, суммаризация, приоритизация, буферизация."""
        try:
            raw = RawUpdate(**data)
        except Exception as e:
            logger.error("invalid_message_format", error=str(e), data=data)
            return

        if self.filter.should_skip(raw):
            logger.debug("update_filtered", id=raw.id, author=raw.author)
            return

        summarized_text = self.summarizer.summarize(raw.description)

        priority = self._get_priority(summarized_text)

        processed_update = {
            "id": raw.id,
            "description": summarized_text,
            "tgChatIds": raw.tgChatIds,
            "priority": priority,
        }

        async with self._lock:
            now = time.time()
            for chat_id in raw.tgChatIds:
                self._buffer[chat_id].append(processed_update)
                if chat_id not in self._buffer_timestamps:
                    self._buffer_timestamps[chat_id] = now

    async def _flush_loop(self):
        """Фоновая задача для проверки истекших окон группировки."""
        try:
            while self._running:
                # Проверяем буфер каждые 1/5 окна, но не реже чем раз в 0.1 сек
                sleep_time = max(0.1, (settings.GROUPING_WINDOW_MS / 1000) / 5)
                await asyncio.sleep(sleep_time)
                await self._flush_expired()
        except asyncio.CancelledError:
            logger.info("flush_loop_cancelled")
        except Exception as e:
            logger.error("flush_loop_error", error=str(e))

    async def _flush_expired(self):
        """Отправляет в Kafka сообщения, чьё время окна истекло."""
        now = time.time()
        window_sec = settings.GROUPING_WINDOW_MS / 1000.0

        async with self._lock:
            expired_chats = [
                chat_id
                for chat_id, first_seen in self._buffer_timestamps.items()
                if (now - first_seen) >= window_sec
            ]

            for chat_id in expired_chats:
                updates = self._buffer.pop(chat_id, [])
                self._buffer_timestamps.pop(chat_id, None)

                if not updates:
                    continue

                if len(updates) == 1:
                    await self._send_to_kafka(updates[0])
                else:
                    descriptions = [
                        f"{i + 1}. {u['description']}" for i, u in enumerate(updates)
                    ]
                    grouped_desc = "\n\n".join(descriptions)

                    max_priority = max(
                        updates, key=lambda u: self._priority_value(u["priority"])
                    )["priority"]
                    first_id = updates[0]["id"]

                    grouped_update = {
                        "id": first_id,
                        "description": grouped_desc,
                        "tgChatIds": [chat_id],
                        "priority": max_priority,
                    }
                    await self._send_to_kafka(grouped_update)

    async def _send_to_kafka(self, update_dict: dict):
        """Публикация обработанного сообщения в Kafka."""
        try:
            await self.producer.send_and_wait(
                settings.KAFKA_OUTPUT_TOPIC, value=update_dict
            )
            logger.info(
                "update_sent_to_kafka",
                id=update_dict["id"],
                priority=update_dict["priority"],
                chat_ids=update_dict["tgChatIds"],
            )
        except Exception as e:
            logger.error("kafka_send_failed", error=str(e), update=update_dict)

    async def stop(self):
        """Корректная остановка: отмена задач, финальная отправка буфера, закрытие соединений."""
        self._running = False

        if self._process_task:
            self._process_task.cancel()
            await self._process_task
        if self._flush_task:
            self._flush_task.cancel()
            await self._flush_task

        await self._flush_expired()

        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

        logger.info("ai_agent_stopped")
