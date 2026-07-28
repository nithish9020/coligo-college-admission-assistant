import logging
import sys
from typing import cast

import structlog

from api.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the whole process.

    Python equivalent of a pino setup: pretty, colored, human-readable
    output in development; single-line JSON in production so log
    aggregators (Datadog, CloudWatch, etc.) can parse it. Called once at
    app startup from `api/main.py`.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.ENVIRONMENT == "production"
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Route uvicorn's own startup/error logs through the same formatter
    # instead of its default plain-text one, so terminal output is uniform.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Layer-scoped logger — equivalent to a pino child logger per module.

    Usage: `logger = get_logger(__name__)` at the top of any router,
    service, or (future) repository module.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
