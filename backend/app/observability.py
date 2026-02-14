"""Observability utilities: structured logging, request IDs, and basic in-memory metrics."""

from __future__ import annotations

import contextvars
import json
import logging
import os
import time
from collections import defaultdict
from typing import Any


request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload.update(extra_fields)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers on hot reload
    root.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    logger.log(level, message, extra={"extra_fields": fields})


class Metrics:
    """Very small in-memory metric sink (hook point for Prometheus/OpenTelemetry later)."""

    def __init__(self) -> None:
        self.counters: defaultdict[str, int] = defaultdict(int)

    def incr(self, key: str, value: int = 1) -> None:
        self.counters[key] += value

    def snapshot(self) -> dict[str, int]:
        return dict(self.counters)


metrics = Metrics()


def classify_error(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()

    if "timeout" in name or "timeout" in msg:
        return "timeout"
    if "auth" in name or "unauthorized" in msg or "invalid api key" in msg:
        return "auth"
    if "connection" in name or "network" in msg:
        return "network"
    if "validation" in name or "pydantic" in msg:
        return "validation"
    return "internal"
