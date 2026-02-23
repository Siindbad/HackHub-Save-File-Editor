"""Update download helper wiring around shared update service functions."""

import time
import urllib.request
from services import update_service
from typing import Any


def download_bytes_with_retries(
    owner: Any,
    url: Any,
    attempts: Any=3,
    timeout: Any=60,
    request_factory: Any=None,
    urlopen_fn: Any=None,
    is_retryable_fn: Any=None,
    backoff_fn: Any=None,
    sleep_fn: Any=None,
) -> Any:
    """Delegate byte-download with shared retry policy wiring."""
    use_request_factory = request_factory or urllib.request.Request
    use_urlopen = urlopen_fn or urllib.request.urlopen
    use_retryable = is_retryable_fn or getattr(owner, "_is_retryable_download_error", update_service.is_retryable_download_error)
    use_backoff = backoff_fn or getattr(owner, "_download_backoff_delay", update_service.download_backoff_delay)
    use_sleep = sleep_fn or time.sleep
    return update_service.download_bytes_with_retries(
        url=url,
        headers=owner._download_headers(),
        attempts=attempts,
        timeout=timeout,
        request_factory=use_request_factory,
        urlopen_fn=use_urlopen,
        is_retryable_fn=use_retryable,
        backoff_fn=use_backoff,
        sleep_fn=use_sleep,
    )


def download_to_file_with_retries(
    owner: Any,
    url: Any,
    out_path: Any,
    attempts: Any=3,
    timeout: Any=60,
    chunk_size: Any=1024 * 1024,
    request_factory: Any=None,
    urlopen_fn: Any=None,
    is_retryable_fn: Any=None,
    backoff_fn: Any=None,
    sleep_fn: Any=None,
) -> Any:
    """Delegate stream-download with shared retry policy wiring."""
    use_request_factory = request_factory or urllib.request.Request
    use_urlopen = urlopen_fn or urllib.request.urlopen
    use_retryable = is_retryable_fn or getattr(owner, "_is_retryable_download_error", update_service.is_retryable_download_error)
    use_backoff = backoff_fn or getattr(owner, "_download_backoff_delay", update_service.download_backoff_delay)
    use_sleep = sleep_fn or time.sleep
    return update_service.download_to_file_with_retries(
        url=url,
        out_path=out_path,
        headers=owner._download_headers(),
        attempts=attempts,
        timeout=timeout,
        chunk_size=chunk_size,
        request_factory=use_request_factory,
        urlopen_fn=use_urlopen,
        is_retryable_fn=use_retryable,
        backoff_fn=use_backoff,
        sleep_fn=use_sleep,
    )
