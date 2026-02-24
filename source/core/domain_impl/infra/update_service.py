"""Core updater retry/backoff and error formatting helpers."""

import logging
import os
import secrets
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from core.exceptions import AppRuntimeError

_LOG = logging.getLogger(__name__)
_RETRY_AFTER_PARSE_ERRORS = (TypeError, ValueError, OverflowError)
_RETRYABLE_TRANSFER_EXCEPTIONS = (
    RuntimeError,
    urllib.error.HTTPError,
    urllib.error.URLError,
    TimeoutError,
    OSError,
)


def walk_exception_chain(exc: Any, max_depth: Any = 8) -> Any:
    # Walk cause/context exception chain without infinite recursion.
    seen = set()
    current = exc
    depth = 0
    while current is not None and depth < max_depth:
        ident = id(current)
        if ident in seen:
            break
        seen.add(ident)
        yield current
        current = getattr(current, "__cause__", None) or getattr(current, "__context__", None)
        depth += 1


def format_update_error(exc: Any) -> Any:
    # Map low-level update errors to readable UI-safe messages.
    base = "Update failed."
    for err in walk_exception_chain(exc):
        if isinstance(err, PermissionError):
            return (
                "Update failed: Windows denied file access.\n"
                "Close the app and retry, or run from a user-writable folder."
            )
        if isinstance(err, OSError):
            winerr = int(getattr(err, "winerror", 0) or 0)
            match winerr:
                case 5:
                    return (
                        "Update failed: access denied while replacing app files.\n"
                        "Retry update, or run from a user-writable folder."
                    )
                case 32 | 33:
                    return (
                        "Update failed: app file is in use by another process.\n"
                        "Close the app and retry update."
                    )
        if isinstance(err, urllib.error.HTTPError):
            code = int(getattr(err, "code", 0) or 0)
            match code:
                case 404:
                    return "Update failed: release file not found (HTTP 404)."
                case 403:
                    return "Update failed: access denied by server (HTTP 403)."
                case 429:
                    return "Update failed: rate-limited by server (HTTP 429). Please retry shortly."
                case 500 | 502 | 503 | 504:
                    return f"Update failed: server temporarily unavailable (HTTP {code})."
                case _:
                    return f"Update failed: server responded with HTTP {code}."
        if isinstance(err, urllib.error.URLError):
            reason = getattr(err, "reason", None)
            reason_text = str(reason or "").strip()
            lower = reason_text.lower()
            if isinstance(reason, socket.gaierror) or "name or service not known" in lower or "getaddrinfo" in lower:
                return "Update failed: DNS lookup failed (can't resolve update server)."
            if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in lower:
                return "Update failed: connection timed out."
            if isinstance(reason, ssl.SSLError) or "ssl" in lower or "tls" in lower or "certificate" in lower:
                return "Update failed: secure connection (TLS/SSL) error."
            if "connection refused" in lower:
                return "Update failed: connection refused by server."
            if reason_text:
                return f"Update failed: network error ({reason_text})."
            return "Update failed: network connection error."
        if isinstance(err, (socket.timeout, TimeoutError)):
            return "Update failed: connection timed out."
        if isinstance(err, ssl.SSLError):
            return "Update failed: secure connection (TLS/SSL) error."

        text = str(err or "").strip()
        if text:
            lower = text.lower()
            if "checksum mismatch" in lower:
                return (
                    "Update failed: downloaded file integrity check failed (checksum mismatch).\n"
                    "Use manual download to replace the app."
                )
            if "checksum file missing" in lower or "checksum" in lower:
                return "Update failed: checksum validation data is unavailable."
            if "authenticode" in lower or "signature" in lower:
                return (
                    "Update failed: signature verification failed for downloaded update.\n"
                    "Use manual download if this build is intentionally unsigned."
                )
            if "not a valid exe" in lower:
                return "Update failed: downloaded file is not a valid Windows executable."
            if "download failed" in lower:
                continue
            return f"Update failed: {text}"
    return base


def parse_retry_after_seconds(value: Any) -> Any:
    # Parse Retry-After as seconds or HTTP-date.
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        secs = int(raw)
        if secs > 0:
            return secs
    except _RETRY_AFTER_PARSE_ERRORS as exc:
        _LOG.debug("Retry-After parse as seconds failed for value %r: %s", raw, exc)
    try:
        dt = parsedate_to_datetime(raw)
        now = datetime.now(dt.tzinfo) if getattr(dt, "tzinfo", None) else datetime.now()
        delta = (dt - now).total_seconds()
        if delta > 0:
            return int(delta)
    except _RETRY_AFTER_PARSE_ERRORS as exc:
        _LOG.debug("Retry-After parse as HTTP-date failed for value %r: %s", raw, exc)
    return None


def is_retryable_download_error(exc: Any) -> Any:
    if isinstance(exc, RuntimeError):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        return int(getattr(exc, "code", 0) or 0) in (408, 409, 425, 429, 500, 502, 503, 504)
    if isinstance(exc, urllib.error.URLError):
        return True
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, OSError):
        return True
    return False


def download_backoff_delay(exc: Any, attempt_index: Any, base_delay: Any = 0.45, max_delay: Any = 12.0) -> Any:
    # Exponential backoff with Retry-After and jitter.
    attempt = max(0, int(attempt_index))
    delay = min(float(max_delay), float(base_delay) * (2 ** attempt))
    retry_after = None
    if isinstance(exc, urllib.error.HTTPError):
        try:
            retry_after = parse_retry_after_seconds(exc.headers.get("Retry-After"))
        except (AttributeError, TypeError, ValueError):
            retry_after = None
    if retry_after is not None:
        delay = max(delay, min(float(max_delay), float(retry_after)))
    jitter = 0.05 + (secrets.randbelow(301) / 1000.0)
    return max(0.05, delay + jitter)


def download_bytes_with_retries(
    url: Any,
    headers: Any,
    attempts: Any = 3,
    timeout: Any = 60,
    request_factory: Any = urllib.request.Request,
    urlopen_fn: Any = urllib.request.urlopen,
    is_retryable_fn: Any = is_retryable_download_error,
    backoff_fn: Any = download_backoff_delay,
    sleep_fn: Any = time.sleep,
) -> Any:
    last_exc = None
    max_attempts = max(1, int(attempts))
    for attempt in range(max_attempts):
        try:
            req = request_factory(url, headers=headers)
            with urlopen_fn(req, timeout=timeout) as resp:
                return resp.read()
        except _RETRYABLE_TRANSFER_EXCEPTIONS as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts:
                break
            if not is_retryable_fn(exc):
                break
            sleep_fn(backoff_fn(exc, attempt))
    raise AppRuntimeError("Download failed after retries.") from last_exc


def download_to_file_with_retries(
    url: Any,
    out_path: Any,
    headers: Any,
    attempts: Any = 3,
    timeout: Any = 60,
    chunk_size: Any = 1024 * 1024,
    request_factory: Any = urllib.request.Request,
    urlopen_fn: Any = urllib.request.urlopen,
    is_retryable_fn: Any = is_retryable_download_error,
    backoff_fn: Any = download_backoff_delay,
    sleep_fn: Any = time.sleep,
) -> Any:
    last_exc = None
    chunk_size = max(1024, int(chunk_size))
    max_attempts = max(1, int(attempts))
    for attempt in range(max_attempts):
        try:
            req = request_factory(url, headers=headers)
            with urlopen_fn(req, timeout=timeout) as resp, open(out_path, "wb") as handle:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
            if os.path.getsize(out_path) <= 0:
                raise AppRuntimeError("Downloaded file is empty.")
            return
        except _RETRYABLE_TRANSFER_EXCEPTIONS as exc:
            last_exc = exc
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError as cleanup_exc:
                _LOG.debug("Partial download cleanup failed for %s: %s", out_path, cleanup_exc)
            if attempt + 1 >= max_attempts:
                break
            if not is_retryable_fn(exc):
                break
            sleep_fn(backoff_fn(exc, attempt))
    raise AppRuntimeError("Download failed after retries.") from last_exc
