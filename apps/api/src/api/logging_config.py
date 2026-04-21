"""Structured logging configuration for the SportsLab API.

Call ``configure_logging()`` once at application startup (FastAPI lifespan).
Production (``env != "dev"``) emits JSON lines so Loki/Better Stack can
index them; dev emits coloured console output for human readability.
"""

import logging

import structlog


def configure_logging(*, json_logs: bool, level: str) -> None:
    """Configure structlog processors and stdlib handler.

    Args:
        json_logs: If True, emit JSON lines (production). Otherwise,
            ConsoleRenderer for local development.
        level: Minimum log level name (``"INFO"``, ``"DEBUG"``, ...).

    Notes:
        Safe to call multiple times — handlers are cleared before adding
        the new one, which matters for Uvicorn's ``--reload`` and pytest.
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
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

    handler = logging.StreamHandler()
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
