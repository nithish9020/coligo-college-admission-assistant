import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.core.logging import get_logger

logger = get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Access-log middleware — equivalent to Express's `pino-http`.

    Logs one structured line per request: method, path, status code, and
    duration. This is what makes requests visible in the terminal when
    running `make dev`.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log = logger.info if response.status_code < 500 else logger.error
        log(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
