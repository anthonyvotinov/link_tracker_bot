import httpx
import asyncio
from datetime import datetime
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

github_cb = pybreaker.CircuitBreaker(
    fail_max=settings.CB_FAILURE_THRESHOLD, reset_timeout=settings.CB_RECOVERY_TIMEOUT
)


class GitHubClient:
    """Асинхронный HTTP клиент для GitHub API с паттернами надёжности."""

    def __init__(self):
        self.base_url = settings.GITHUB_API_URL
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "LinkTracker-Scrapper",
        }
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"] = (
                f"token {settings.GITHUB_TOKEN.get_secret_value()}"
            )

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_fixed(settings.RETRY_WAIT_MS / 1000),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.RequestError)),
        reraise=True,
    )
    async def _make_request(self, path: str, params={}) -> dict:
        """Низкоуровневый запрос с таймаутом и ретраями."""
        if params is None:
            params = {}
        timeout = httpx.Timeout(
            connect=5.0, read=settings.HTTP_TIMEOUT, write=5.0, pool=5.0
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{self.base_url}{path}", headers=self.headers, params=params
            )
            if response.status_code in settings.RETRYABLE_STATUSES:
                raise httpx.RequestError(
                    f"Retryable status {response.status_code}", request=response.request
                )
            response.raise_for_status()
            return response.json()

    async def get_latest_activity(self, resource_id: str) -> Optional[Dict]:
        try:
            owner, repo = resource_id.split("/")
        except ValueError:
            logger.error("github_invalid_resource_id", resource_id=resource_id)
            return None

        try:

            def _sync_call():
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(
                        self._make_request(f"/repos/{owner}/{repo}/releases/latest")
                    )
                finally:
                    loop.close()

            data = github_cb.call(_sync_call)
            return {
                "title": data.get("name") or data.get("tag_name") or "New Release",
                "author": data.get("author", {}).get("login") or "unknown",
                "created_at": datetime.fromisoformat(
                    data["published_at"].replace("Z", "+00:00")
                ),
                "preview": (data.get("body") or "")[:300],
            }
        except pybreaker.CircuitBreakerError:
            logger.error("github_circuit_breaker_open")
            return None
        except Exception as e:
            logger.warning("github_fetch_failed", resource_id=resource_id, error=str(e))
            return None

    def parse_github_url(self, url: str) -> Optional[tuple]:
        parts = url.strip("/").split("/")
        if len(parts) >= 5 and parts[2] == "github.com":
            return parts[3], parts[4]
        return None

    async def close(self):
        pass
