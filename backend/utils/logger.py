"""
Centralized logging configuration for the Medical Triage system.
Outputs structured logs with timestamps and agent context.
"""

import logging
import sys
from config.settings import app_config


def get_logger(name: str) -> logging.Logger:
    """
    Factory function — returns a configured logger for a given module/agent.
    Usage: logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Avoid duplicate handlers on re-import
        return logger

    logger.setLevel(getattr(logging, app_config.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger
