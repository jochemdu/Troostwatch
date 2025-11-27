"""HTTP fetching helpers with concurrency, rate limiting and retries.

This module centralises the logic for downloading pages during sync runs. It
supports asyncio-based or thread-pool based concurrency, host-level throttling
and exponential backoff for transient failures. The :class:`HttpFetcher`
provides both synchronous fetching (used for pagination discovery) and
asynchronous bulk fetching (used for lot details).
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urlparse

import aiohttp
import requests


@dataclass
class RequestResult:
    """Result of a single HTTP request."""

    url: str
    text: str | None
    error: str | None
    status: int | None = None

    @property
    def ok(self) -> bool:
        return (
            self.text is not None
            and self.error is None
            and (self.status is None or 200 <= self.status < 400)
        )


class RateLimiter:
    """Simple host-level rate limiter supporting sync and async callers."""

    def __init__(self, requests_per_second: float | None) -> None:
        self.min_interval = 1.0 / requests_per_second if requests_per_second else 0.0
        self._last_seen: dict[str, float] = {}
        self._sync_lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def _next_delay(self, host: str) -> float:
        if self.min_interval <= 0:
            return 0.0
        last = self._last_seen.get(host)
        now = time.monotonic()
        if last is None:
            self._last_seen[host] = now
            return 0.0
        elapsed = now - last
        if elapsed >= self.min_interval:
            self._last_seen[host] = now
            return 0.0
        delay = self.min_interval - elapsed
        self._last_seen[host] = now + delay
        return delay

    def wait_sync(self, host: str) -> None:
        if self.min_interval <= 0:
            return
        with self._sync_lock:
            delay = self._next_delay(host)
        if delay > 0:
            time.sleep(delay)

    async def wait_async(self, host: str) -> None:
        if self.min_interval <= 0:
            return
        async with self._async_lock:
            delay = self._next_delay(host)
        if delay > 0:
            await asyncio.sleep(delay)


class HttpFetcher:
    """HTTP client with retries, backoff and configurable concurrency."""

    def __init__(
        self,
        *,
        max_concurrent_requests: int = 5,
        throttle_per_host: float | None = None,
        retry_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        concurrency_mode: str = "asyncio",
        timeout_seconds: float = 30.0,
        user_agent: str = "",  # Empty string triggers dynamic version lookup
    ) -> None:
        from troostwatch import __version__

        if not user_agent:
            user_agent = f"troostwatch-sync/{__version__}"
        self.max_concurrent_requests = max(1, max_concurrent_requests)
        self.rate_limiter = RateLimiter(throttle_per_host)
        self.retry_attempts = max(1, retry_attempts)
        self.backoff_base_seconds = max(0.0, backoff_base_seconds)
        self.concurrency_mode = concurrency_mode
        self.timeout_seconds = timeout_seconds
        self.headers = {"User-Agent": user_agent}

    def _host_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.hostname or ""

    def _backoff_delay(self, attempt: int) -> float:
        return self.backoff_base_seconds * (2**attempt)

    def fetch_sync(self, url: str) -> RequestResult:
        host = self._host_from_url(url)
        self.rate_limiter.wait_sync(host)
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(
                    url, headers=self.headers, timeout=self.timeout_seconds
                )
                if response.status_code >= 400:
                    raise requests.HTTPError(f"HTTP {response.status_code}")
                return RequestResult(
                    url=url, text=response.text, error=None, status=response.status_code
                )
            except Exception as exc:
                if attempt >= self.retry_attempts - 1:
                    status = None
                    if hasattr(exc, "response") and exc.response is not None:
                        status = getattr(exc.response, "status_code", None)
                    return RequestResult(
                        url=url, text=None, error=str(exc), status=status
                    )
                time.sleep(self._backoff_delay(attempt))
        return RequestResult(url=url, text=None, error="Unknown error", status=None)

    async def _fetch_once_async(
        self, session: aiohttp.ClientSession, url: str
    ) -> RequestResult:
        host = self._host_from_url(url)
        await self.rate_limiter.wait_async(host)
        for attempt in range(self.retry_attempts):
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
                async with session.get(
                    url, headers=self.headers, timeout=timeout
                ) as resp:
                    if resp.status >= 400:
                        raise aiohttp.ClientResponseError(
                            resp.request_info,
                            resp.history,
                            status=resp.status,
                            message=resp.reason or "",
                        )
                    text = await resp.text()
                    return RequestResult(
                        url=url, text=text, error=None, status=resp.status
                    )
            except Exception as exc:
                if attempt >= self.retry_attempts - 1:
                    status = exc.status if hasattr(exc, "status") else None
                    return RequestResult(
                        url=url, text=None, error=str(exc), status=status
                    )
                await asyncio.sleep(self._backoff_delay(attempt))
        return RequestResult(url=url, text=None, error="Unknown error", status=None)

    async def _fetch_many_asyncio(self, urls: Iterable[str]) -> list[RequestResult]:
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def _bounded_fetch(
            session: aiohttp.ClientSession, url: str
        ) -> RequestResult:
            async with semaphore:
                return await self._fetch_once_async(session, url)

        async with aiohttp.ClientSession() as session:
            tasks = [_bounded_fetch(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    async def _fetch_many_threadpool(self, urls: Iterable[str]) -> list[RequestResult]:
        loop = asyncio.get_running_loop()
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        async def _run(url: str) -> RequestResult:
            async with semaphore:
                return await loop.run_in_executor(None, self.fetch_sync, url)

        tasks = [_run(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def fetch_many(self, urls: Iterable[str]) -> list[RequestResult]:
        if self.concurrency_mode not in {"asyncio", "threadpool"}:
            raise ValueError("concurrency_mode must be 'asyncio' or 'threadpool'")
        if self.concurrency_mode == "threadpool":
            return await self._fetch_many_threadpool(urls)
        return await self._fetch_many_asyncio(urls)


__all__ = ["HttpFetcher", "RateLimiter", "RequestResult"]
