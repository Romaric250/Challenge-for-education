import logging
import sys
from collections.abc import MutableMapping
from typing import cast

import structlog

from tutor_api.core.settings import Settings

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "authorization",
        "cookie",
        "set_cookie",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "database_url",
        "api_key",
    }
)


def is_sensitive_key(key: str) -> bool:
    normalised = key.lower().replace("-", "_")
    return normalised in _SENSITIVE_KEYS or normalised.endswith(("_token", "_secret", "_api_key"))


def redact_sensitive(
    _logger: object,
    _method: str,
    event_dict: MutableMapping[str, object],
) -> MutableMapping[str, object]:
    for key in list(event_dict):
        if is_sensitive_key(str(key)):
            event_dict[key] = "[redacted]"
            continue
        value = event_dict[key]
        if isinstance(value, dict):
            event_dict[key] = {
                str(inner_key): "[redacted]" if is_sensitive_key(str(inner_key)) else inner_value
                for inner_key, inner_value in value.items()
            }
    return event_dict


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping()[settings.log_level]
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        redact_sensitive,
        timestamper,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.use_json_logs()
        else structlog.dev.ConsoleRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.error").setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
