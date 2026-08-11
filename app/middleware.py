from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        clear_contextvars()

        header_id = request.headers.get("x-request-id", "")
        try:
            int(header_id.removeprefix("req-"), 16)
            valid_header = header_id.startswith("req-") and len(header_id) == 12
        except ValueError:
            valid_header = False

        correlation_id = header_id.lower() if valid_header else f"req-{uuid.uuid4().hex[:8]}"
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = correlation_id
            response.headers["x-response-time-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
            return response
        finally:
            clear_contextvars()
