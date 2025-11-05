"""Baseline logging configuration for Spectra App.

Provides console + rotating file handler. Level defaults to INFO and can be
overridden via environment variables:

- SPECTRA_LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- SPECTRA_LOG_DIR: path to directory for log files

This module is safe to import early in app startup.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

from .constants import DEFAULT_LOG_DIR, ensure_dir

_LOGGER_NAME = "spectra"
_LOG_FILE_BASENAME = "spectra-app.log"


def _resolve_log_dir() -> Path:
    env = os.environ.get("SPECTRA_LOG_DIR")
    if env:
        try:
            p = Path(env)
            return ensure_dir(p)
        except Exception:
            pass
    return ensure_dir(DEFAULT_LOG_DIR)


def _parse_level(value: str | None) -> int:
    if not value:
        return logging.INFO
    value = value.strip().upper()
    return getattr(logging, value, logging.INFO)


def setup_logging(*, force: bool = False) -> logging.Logger:
    """Configure root logging for the app and return the app logger.

    If already configured and force=False, this is a no-op and returns the
    existing logger.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers and not force:
        return logger

    # Base level on env var (fallback INFO)
    level = _parse_level(os.environ.get("SPECTRA_LOG_LEVEL"))

    logger.setLevel(level)
    logger.propagate = False

    # Console handler (stderr)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(ch)

    # Rotating file handler
    log_dir = _resolve_log_dir()
    fh = logging.handlers.RotatingFileHandler(
        log_dir / _LOG_FILE_BASENAME,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    logger.debug("Logging initialized (level=%s, dir=%s)", logging.getLevelName(level), str(log_dir))
    return logger
