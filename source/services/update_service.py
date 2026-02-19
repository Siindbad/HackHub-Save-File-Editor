"""Updater service facade.

Keeps editor entrypoints importing updater logic from a service-layer path
while core logic remains in `core.update_service`.

This file intentionally re-exports functions only (no runtime logic).
"""

from core.update_service import (  # noqa: F401
    download_backoff_delay,
    download_bytes_with_retries,
    download_to_file_with_retries,
    format_update_error,
    is_retryable_download_error,
    parse_retry_after_seconds,
    walk_exception_chain,
)
