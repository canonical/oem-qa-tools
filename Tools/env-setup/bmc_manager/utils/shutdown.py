"""Graceful shutdown utilities for BMC service."""

import atexit
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

SHUTTING_DOWN = False


def shutdown_handler(
    executor: ThreadPoolExecutor, exit_after: bool = False
) -> None:
    """Shut down executor; optionally exit process (for signal handlers)."""
    global SHUTTING_DOWN
    SHUTTING_DOWN = True
    logger.info("Shutting down...")
    executor.shutdown(wait=True)
    logger.info("Shutdown complete")
    if exit_after:
        sys.exit(0)


def register_shutdown_handlers(executor: ThreadPoolExecutor) -> None:
    """Register shutdown handlers for SIGTERM, SIGINT, and atexit."""

    def signal_handler(signum, frame) -> None:
        shutdown_handler(executor, exit_after=True)

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)
    # atexit: only shut down executor; do not sys.exit() to avoid
    # "Exception ignored in atexit" when running under pytest or other hosts
    atexit.register(lambda: shutdown_handler(executor, exit_after=False))
