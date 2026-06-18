import json
from typing import List
from aiokafka import AIOKafkaProducer
from ai_agent_service.logger import logger
from src.config import settings
from src.models.db_models import LinkDB
from src.services.message_sender import MessageSender


class KafkaMessageSender(MessageSender):
    """Асинхронная отправка уведомлений через Kafka."""

    def __init__(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks=settings.KAFKA_ACKNOWLEDGEMENTS,
            enable_idempotence=False,
        )
        self.topic = settings.KAFKA_TOPIC

    async def start(self):
        await self.producer.start()
        logger.info("kafka_producer_started", topic=self.topic)

    async def send_update(
        self, link: LinkDB, subscribers: List[int], message: str
    ) -> None:
        if not subscribers:
            return

        payload = {
            "id": link.id,
            "url": link.url,
            "tgChatIds": subscribers,
            "resourceType": link.resource_type,
            "message": message,
        }

        try:
            await self.producer.send(self.topic, value=payload)
            logger.info(
                "kafka_update_sent", link_id=link.id, subscribers=len(subscribers)
            )
        except Exception as e:
            logger.error("kafka_send_failed", link_id=link.id, error=str(e))

    async def close(self):
        await self.producer.stop()
        logger.info("kafka_producer_stopped")
