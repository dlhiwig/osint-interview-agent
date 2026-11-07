"""Centralized logging setup."""
from __future__ import annotations

import logging
import os
import sys


def configure_logging(level: str | int | None = None, *, stream=sys.stderr) -> None:
    """Idempotent logging setup.

    Level precedence: explicit arg > OSINT_LOG_LEVEL env > INFO.
    """
    if isinstance(level, str):
        resolved = level.upper()
    elif isinstance(level, int):
        resolved = level
    else:
        resolved = os.environ.get("OSINT_LOG_LEVEL", "INFO").upper()

    root = logging.getLogger("osint_agent")
    if getattr(root, "_osint_configured", False):
        root.setLevel(resolved)
        return

    root.setLevel(resolved)
    handler = logging.StreamHandler(stream=stream)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.propagate = False
    root._osint_configured = True  # type: ignore[attr-defined]
