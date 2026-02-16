"""Safety controls: lightweight input guardrails and rate limiting for chat."""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from typing import Deque

# Try to import bleach for input sanitization
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    print("⚠️ bleach not installed. HTML sanitization will use fallback.")


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


# =============================================================================
# Input Sanitization for User-Generated Content
# =============================================================================

# Allowed HTML tags (very restrictive for user-generated content)
ALLOWED_TAGS = []  # No HTML allowed in text inputs
ALLOWED_ATTRIBUTES = {}  # No attributes allowed

# Pattern to detect script tags and event handlers
SCRIPT_PATTERN = re.compile(r'<script.*?>.*?</script>', re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
JS_URL_PATTERN = re.compile(r'javascript:', re.IGNORECASE)


def sanitize_text_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user text input to prevent XSS attacks.
    
    - Strips all HTML tags
    - Removes event handlers
    - Removes javascript: URLs
    - Truncates to max_length
    
    Args:
        text: Raw user input
        max_length: Maximum allowed length
        
    Returns:
        Clean, sanitized text safe for storage and display
    """
    if not text:
        return ""
    
    # Convert to string if needed
    text = str(text)
    
    # Use bleach if available for proper HTML sanitization
    if BLEACH_AVAILABLE:
        text = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    else:
        # Fallback: manual HTML tag stripping
        text = re.sub(r'<[^>]+>', '', text)
    
    # Remove any remaining event handlers (onload, onclick, etc.)
    text = EVENT_HANDLER_PATTERN.sub('', text)
    
    # Remove javascript: URLs
    text = JS_URL_PATTERN.sub('', text)
    
    # Remove script tags (defense in depth)
    text = SCRIPT_PATTERN.sub('', text)
    
    # Normalize whitespace
    text = normalize_text(text)
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
    
    return text


def sanitize_activity_title(title: str) -> str:
    """Sanitize activity title - strict sanitization, no HTML."""
    return sanitize_text_input(title, max_length=200)


def sanitize_activity_description(description: str) -> str:
    """Sanitize activity description - strict sanitization, no HTML."""
    return sanitize_text_input(description, max_length=2000)


def sanitize_schedule_title(title: str) -> str:
    """Sanitize schedule title - strict sanitization, no HTML."""
    return sanitize_text_input(title, max_length=200)


def sanitize_activity_data(activity_data: dict) -> dict:
    """
    Sanitize all text fields in an activity dictionary.
    
    Args:
        activity_data: Dictionary containing activity fields
        
    Returns:
        Sanitized activity dictionary
    """
    sanitized = dict(activity_data)
    
    # Sanitize common text fields
    text_fields = ['title', 'name', 'description', 'instructions', 'notes']
    for field in text_fields:
        if field in sanitized and sanitized[field]:
            if field in ['title', 'name']:
                sanitized[field] = sanitize_activity_title(sanitized[field])
            else:
                sanitized[field] = sanitize_activity_description(sanitized[field])
    
    # Sanitize supplies list if present
    if 'supplies' in sanitized and isinstance(sanitized['supplies'], list):
        sanitized['supplies'] = [
            sanitize_text_input(s, max_length=100) 
            for s in sanitized['supplies']
        ]
    
    return sanitized
