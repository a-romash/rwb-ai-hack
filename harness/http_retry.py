"""Retry throttled LLM requests within one monotonic minute."""
import math
import time
import urllib.error
from harness.llm_throttle import AdmissionLimitExceeded, open_throttled


class RateLimitExceeded(RuntimeError):
    def __init__(self):
        super().__init__('Лимит модели (HTTP 429) не снят за 60 секунд. Прогон остановлен. Повторите запуск позже.')


def open_with_rate_limit_retry(opener, request, *, timeout, sleep=None, clock=None):
    sleep = sleep or time.sleep
    clock = clock or time.monotonic
    deadline = None
    while True:
        remaining = deadline - clock() if deadline is not None else timeout
        if remaining <= 0:
            raise RateLimitExceeded() from None
        delay = 5
        try:
            return open_throttled(opener, request, timeout=min(timeout, remaining), sleep=sleep, clock=clock)
        except AdmissionLimitExceeded:
            if deadline is not None:
                raise RateLimitExceeded() from None
            raise
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and (deadline is None or exc.code not in (500, 502, 503, 504)):
                raise
            if deadline is None:
                deadline = clock() + 60
            try:
                advertised = float((exc.headers or {}).get('Retry-After', '5'))
                if math.isfinite(advertised):
                    delay = max(1, advertised)
            except (TypeError, ValueError):
                pass
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError):
            if deadline is None:
                raise
        remaining = deadline - clock()
        if remaining <= 0:
            raise RateLimitExceeded() from None
        sleep(min(delay, remaining))
