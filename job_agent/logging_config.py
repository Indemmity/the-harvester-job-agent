from __future__ import annotations

import logging

from .exceptions import ConfigurationError

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def configure_logging(level: str = "INFO") -> None:
    normalized_level = (level or "INFO").upper()
    numeric_level = getattr(logging, normalized_level, None)
    if not isinstance(numeric_level, int):
        raise ConfigurationError(f"Unsupported log level: {level!r}")

    logging.basicConfig(level=numeric_level, format=DEFAULT_LOG_FORMAT, force=True)

