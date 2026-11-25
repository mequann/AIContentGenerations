"""Retry with exponential backoff + jitter, aware of rate limits.

Free tiers fail in predictable ways: 429 (quota / rate limit), 5xx
(overloaded), timeouts. We retry those; we do NOT retry 4xx client errors
(bad prompt, bad key) because retrying cannot fix them.
"""
from __future__ import annotations

import functools
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryableError(Exception):
    """Raise to signal a transient failure. retry_after (seconds) is honoured if set."""

    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


class QuotaExhausted(Exception):
    """Daily/weekly quota gone — retrying now is pointless. Stage should degrade or stop cleanly."""


def is_transient(exc: BaseException) -> bool:
    if isinstance(exc, RetryableError):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    if any(k in name for k in ("timeout", "connectionerror", "serviceunavailable", "servererror")):
        return True
    return any(k in text for k in (" 429", "429 ", "rate limit", "resource_exhausted", " 500", " 502",
                                   " 503", " 504", "overloaded", "unavailable", "deadline", "timed out"))


def with_retries(max_attempts: int = 5, base: float = 2.0, cap: float = 60.0,
                 on_retry: Callable[[int, BaseException, float], None] | None = None):
    def deco(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except QuotaExhausted:
                    raise
                except BaseException as exc:  # noqa: BLE001
                    if attempt == max_attempts or not is_transient(exc):
                        raise
                    wait = getattr(exc, "retry_after", None) or min(cap, base * 2 ** (attempt - 1))
                    wait *= 0.8 + 0.4 * random.random()
                    if on_retry:
                        on_retry(attempt, exc, wait)
                    else:
                        print(f"    ! transient error ({exc}); retry {attempt}/{max_attempts - 1} in {wait:.1f}s")
                    time.sleep(wait)
            raise RuntimeError("unreachable")
        return wrapper
    return deco
