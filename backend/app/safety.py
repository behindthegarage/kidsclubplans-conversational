"""Safety controls: lightweight input guardrails and rate limiting for chat."""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from typing import Deque


# Very lightweight policy checks for child-care planning domain.
BLOCKED_PATTERNS = [
    r"\bsexual\b",
    r"\bporn\b",
    r"\bexplicit\b",
    r"\bself[- ]?harm\b",
    r"\bsuicide\b",
    r"\bkill\b",
    r"\bweapon\b",
    r"\bdrugs?\b",
    r"\bhow to hack\b",
]


def normalize_text(text: str) -> str:
    # Collapse whitespace, keep punctuation for model quality.
    return re.sub(r"\s+", " ", text or "").strip()


def check_input_safety(message: str) -> tuple[bool, str | None]:
    text = (message or "").lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text):
            return False, "This request is outside safe-use policy for KidsClubPlans."
    return True, None


class SlidingWindowRateLimiter:
    """Simple in-memory limiter: N requests per window seconds per key."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: defaultdict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        q = self._events[key]
        cutoff = now - self.window_seconds

        while q and q[0] < cutoff:
            q.popleft()

        if len(q) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - q[0])))
            return False, retry_after

        q.append(now)
        return True, 0


CHAT_RATE_LIMIT_PER_MIN = int(os.getenv("CHAT_RATE_LIMIT_PER_MIN", "20"))
chat_rate_limiter = SlidingWindowRateLimiter(max_requests=CHAT_RATE_LIMIT_PER_MIN, window_seconds=60)
