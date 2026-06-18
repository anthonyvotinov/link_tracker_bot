import httpx
import asyncio
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import pybreaker
from src.bot_service.config import settings
from src.bot_service.logger import logger

scrapper_cb = pybreaker.CircuitBreaker(
    fail_max=settings.CB_FAILURE_THRESHOLD, reset_timeout=settings.CB_RECOVERY_TIMEOUT
)


class ScrapperClient:
    """HTTP клиент для взаимодействия с Scrapper сервисом с паттернами надёжности."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._timeout = httpx.Timeout(
            connect=5.0, read=settings.HTTP_TIMEOUT, write=5.0, pool=5.0
        )
        self.client = httpx.AsyncClient(timeout=self._timeout)

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_fixed(settings.RETRY_WAIT_MS / 1000),  # NFR-3: constant backoff
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Низкоуровневый запрос с Retry."""
        response = await self.client.request(method, url, **kwargs)
        if response.status_code in self._parse_retryable():
            raise httpx.RequestError(f"Retryable HTTP {response.status_code}")
        response.raise_for_status()
        return response

    def _parse_retryable(self) -> list:
        try:
            return [int(x.strip()) for x in settings.RETRYABLE_STATUSES.split(",")]
        except (ValueError, AttributeError):
            return [429, 500, 502, 503, 504]

    async def _cb_call(self, coro):
        """Запуск async-корутин под Circuit Breaker без блокировки event loop."""
        return await asyncio.to_thread(scrapper_cb.call, lambda: asyncio.run(coro))

    async def register_chat(self, user_id: int) -> bool:
        try:
            await self._cb_call(
                self._request("POST", f"{self.base_url}/tg-chat/{user_id}")
            )
            return True
        except pybreaker.CircuitBreakerError:
            logger.warning("scrapper_cb_open", method="register_chat", user_id=user_id)
            return False
        except Exception as e:
            logger.error("scrapper_register_chat_error", user_id=user_id, error=str(e))
            return False

    async def delete_chat(self, user_id: int) -> bool:
        try:
            await self._cb_call(
                self._request("DELETE", f"{self.base_url}/tg-chat/{user_id}")
            )
            return True
        except pybreaker.CircuitBreakerError:
            logger.warning("scrapper_cb_open", method="delete_chat", user_id=user_id)
            return False
        except Exception as e:
            logger.error("scrapper_delete_chat_error", user_id=user_id, error=str(e))
            return False

    async def add_link(self, user_id: int, url: str, tags: List[str]) -> Optional[Dict]:
        try:
            response = await self._cb_call(
                self._request(
                    "POST",
                    f"{self.base_url}/links",
                    headers={"Tg-Chat-Id": str(user_id)},
                    json={"link": url, "tags": tags, "filters": []},
                )
            )
            return response.json()
        except pybreaker.CircuitBreakerError:
            logger.warning(
                "scrapper_cb_open", method="add_link", user_id=user_id, url=url
            )
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                logger.info("link_already_tracked", user_id=user_id, url=url)
                return None
            logger.error(
                "scrapper_add_link_error", user_id=user_id, url=url, error=str(e)
            )
            return None
        except Exception as e:
            logger.error(
                "scrapper_add_link_error", user_id=user_id, url=url, error=str(e)
            )
            return None

    async def remove_link(self, user_id: int, url: str) -> bool:
        try:
            await self._cb_call(
                self._request(
                    "DELETE",
                    f"{self.base_url}/links",
                    headers={"Tg-Chat-Id": str(user_id)},
                )
            )
            return True
        except pybreaker.CircuitBreakerError:
            logger.warning(
                "scrapper_cb_open", method="remove_link", user_id=user_id, url=url
            )
            return False
        except Exception as e:
            logger.error(
                "scrapper_remove_link_error", user_id=user_id, url=url, error=str(e)
            )
            return False

    async def get_links(self, user_id: int, tag: Optional[str] = None) -> List[Dict]:
        try:
            response = await self._cb_call(
                self._request(
                    "GET",
                    f"{self.base_url}/links",
                    headers={"Tg-Chat-Id": str(user_id)},
                )
            )
            return response.json().get("links", [])
        except pybreaker.CircuitBreakerError:
            logger.warning("scrapper_cb_open", method="get_links", user_id=user_id)
            return []
        except Exception as e:
            logger.error("scrapper_get_links_error", user_id=user_id, error=str(e))
            return []

    async def close(self):
        await self.client.aclose()


scrapper_client = ScrapperClient(settings.SCRAPPER_URL)
