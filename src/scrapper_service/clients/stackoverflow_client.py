import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)
import pybreaker
from src.scrapper_service.logger import logger
from src.scrapper_service.config import settings

so_cb = pybreaker.CircuitBreaker(
    fail_max=settings.CB_FAILURE_THRESHOLD, reset_timeout=settings.CB_RECOVERY_TIMEOUT
)


class StackOverflowClient:
    """Асинхронный HTTP клиент для StackExchange API с паттернами надёжности."""

    def __init__(self):
        self.base_url = settings.STACKOVERFLOW_API_URL

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_fixed(settings.RETRY_WAIT_MS / 1000),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def _make_request(self, path: str, params: dict = {}) -> dict:
        timeout = httpx.Timeout(
            connect=5.0, read=settings.HTTP_TIMEOUT, write=5.0, pool=5.0
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{self.base_url}{path}", params=params)
            if response.status_code in settings.RETRYABLE_STATUSES:
                raise httpx.RequestError(
                    f"Retryable status {response.status_code}", request=response.request
                )
            response.raise_for_status()
            return response.json()

    async def get_latest_answer(self, question_id: int) -> Optional[Dict]:
        def _sync_call():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self._make_request(
                        f"/questions/{question_id}",
                        params={"site": "stackoverflow", "filter": "withbody"},
                    )
                )
            finally:
                loop.close()

        try:
            data = so_cb.call(_sync_call)
            items = data.get("items", [])
            if not items:
                return None

            q = items[0]
            if q.get("answer_count", 0) > 0:

                def _sync_ans():
                    loop = asyncio.new_event_loop()
                    try:
                        return loop.run_until_complete(
                            self._make_request(
                                f"/questions/{question_id}/answers",
                                params={
                                    "site": "stackoverflow",
                                    "order": "desc",
                                    "sort": "creation",
                                    "pagesize": 1,
                                    "filter": "withbody",
                                },
                            )
                        )
                    finally:
                        loop.close()

                ans_data = so_cb.call(_sync_ans)
                if ans_data.get("items"):
                    ans = ans_data["items"][0]
                    return {
                        "title": q.get("title", "StackOverflow Question"),
                        "author": ans.get("owner", {}).get("display_name", "unknown"),
                        "created_at": datetime.fromtimestamp(
                            ans["creation_date"], tz=timezone.utc
                        ),
                        "preview": (ans.get("body") or "")
                        .replace("<p>", "")
                        .replace("</p>", "")[:300],
                    }

            return {
                "title": q.get("title", "StackOverflow Question"),
                "author": q.get("owner", {}).get("display_name", "unknown"),
                "created_at": datetime.fromtimestamp(
                    q["last_activity_date"], tz=timezone.utc
                ),
                "preview": (q.get("body") or "")
                .replace("<p>", "")
                .replace("</p>", "")[:300],
            }
        except pybreaker.CircuitBreakerError:
            logger.error("stackoverflow_circuit_breaker_open")
            return None
        except Exception as e:
            logger.warning(
                "stackoverflow_fetch_failed", question_id=question_id, error=str(e)
            )
            return None

    def parse_stackoverflow_url(self, url: str) -> Optional[int]:
        import re

        match = re.search(r"/questions/(\d+)", url)
        return int(match.group(1)) if match else None

    async def close(self):
        pass
