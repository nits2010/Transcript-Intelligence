"""Production-grade logging for the Transcript Intelligence pipeline.

Mirrors the slf4j pattern:
    from .logger import get_logger
    _log = get_logger(__name__)

    _log.debug("Chart saved: %s", path)
    _log.info("Loaded %d meetings", n)
    _log.warning("Skipping %s: %s", name, err)

Call setup_logging() once at application entry (pipeline.main()).
All module loggers are children of 'transcript_intelligence' and inherit
its level/handlers automatically.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path

_ROOT = "transcript_intelligence"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """One JSON object per line — compatible with ELK, Datadog, CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class _TextFormatter(logging.Formatter):
    _FMT = "%(asctime)s  %(levelname)-8s  %(name)-36s  %(message)s"
    _DATE = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self._FMT, datefmt=self._DATE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def setup_logging(
    level: str = "INFO",
    fmt: str = "text",
    file: str | None = None,
    max_bytes: int = 10_485_760,
    backup_count: int = 3,
) -> None:
    """Configure the root 'transcript_intelligence' logger.

    Safe to call multiple times (e.g. in notebooks) — clears prior handlers
    before re-applying so output is never duplicated.

    Args:
        level:        Log level string: DEBUG | INFO | WARNING | ERROR
        fmt:          Output format: "text" (human-readable) | "json" (structured)
        file:         Optional log file path. Enables a RotatingFileHandler.
        max_bytes:    Max size per log file before rotation (default 10 MB).
        backup_count: Number of rotated files to keep (default 3).
    """
    root = logging.getLogger(_ROOT)
    root.setLevel(level.upper())
    root.handlers.clear()
    root.propagate = False  # don't bubble up to Python root logger

    formatter: logging.Formatter = _JsonFormatter() if fmt == "json" else _TextFormatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if file:
        log_path = Path(file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger under the 'transcript_intelligence' hierarchy.

    Pass __name__ from the calling module so records show their full path,
    e.g. 'transcript_intelligence.sentiment'.
    """
    return logging.getLogger(name)
