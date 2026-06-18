import httpx
import asyncio
from typing import List
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import pybreaker
from ai_agent_service.logger import logger
from src.config import settings
from src.models.db_models import LinkDB
from src.services.message_sender import MessageSender
from src.services.kafka_sender import KafkaMessageSender

http_cb = pybreaker.CircuitBreaker(
    fail_max=settings.CB_FAILURE_THRESHOLD, reset_timeout=settings.CB_RECOVERY_TIMEOUT
)


class UpdateSender(MessageSender):
    def __init__(self):
        self.bot_url = settings.BOT_URL.rstrip("/")
        self._http_client = httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT)
        self._kafka_sender = KafkaMessageSender()

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_fixed(settings.RETRY_WAIT_MS / 1000),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def _send_http_request(self, payload: dict) -> None:
        """HTTP-запрос с Timeout и Retry"""
        response = await self._http_client.post(
            f"{self.bot_url}/api/updates", json=payload
        )
        if response.status_code not in settings.RETRYABLE_STATUSES:
            response.raise_for_status()
        raise httpx.RequestError(f"Retryable HTTP {response.status_code}")

    def _cb_http_call(self, payload: dict) -> None:
        """Синхронная обёртка для pybreaker (выполняется в отдельном потоке)"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._send_http_request(payload))
        finally:
            loop.close()

    async def send_update(
        self, link: LinkDB, subscribers: List[int], message: str
    ) -> None:
        if not subscribers:
            return

        payload = {
            "id": link.id,
            "url": str(link.url),
            "tgChatIds": subscribers,
            "resourceType": link.resource_type,
            "message": message,
        }

        try:
            await asyncio.to_thread(http_cb.call, self._cb_http_call, payload)
            logger.info("update_sent_http", link_id=link.id)

        except pybreaker.CircuitBreakerError:
            logger.warning("http_circuit_open_fallback_to_kafka", link_id=link.id)
            await self._publish_to_kafka(link, subscribers, message)

        except Exception as e:
            logger.error("http_send_failed_fallback", link_id=link.id, error=str(e))
            await self._publish_to_kafka(link, subscribers, message)

    async def _publish_to_kafka(
        self, link: LinkDB, subscribers: List[int], message: str
    ) -> None:
        """Прямая публикация в Kafka при недоступности HTTP"""
        await self._kafka_sender.send_update(link, subscribers, message)

    async def start(self) -> None:
        """Инициализация соединений"""
        await self._kafka_sender.start()

    async def close(self) -> None:
        """Graceful shutdown"""
        await self._kafka_sender.close()
        await self._http_client.aclose()
