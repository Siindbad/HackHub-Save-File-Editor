"""Consolidated update infra domain master.

Contains merged logic from update_* infra modules.
"""


# --- Merged from update_asset_service.py ---
"""Update asset download and validation helpers."""

import os
import tempfile
import zipfile
from typing import Any
from core.exceptions import AppRuntimeError


def download_dist_asset(owner: Any) -> Any:
    """Download latest update asset and validate payload integrity/trust signals."""
    release_info = None
    try:
        release_info = owner._fetch_latest_release_info()
    except RuntimeError:
        release_info = None
    url = owner._release_asset_download_url(release_info, owner.GITHUB_ASSET_NAME)
    if not url:
        url = owner._dist_url(owner.GITHUB_ASSET_NAME)
    tmp_dir = tempfile.mkdtemp(prefix="sins_update_")
    new_path = os.path.join(tmp_dir, owner.GITHUB_ASSET_NAME)
    owner._download_to_file_with_retries(url, new_path)
    if not os.path.isfile(new_path) or os.path.getsize(new_path) <= 0:
        raise AppRuntimeError("Downloaded update is empty.")
    update_asset_name = str(getattr(owner, "GITHUB_ASSET_NAME", "")).strip().lower()
    if update_asset_name.endswith(".zip"):
        if not zipfile.is_zipfile(new_path):
            raise AppRuntimeError("Downloaded update is not a valid ZIP package.")
    else:
        # Basic sanity check for a Windows PE executable.
        with open(new_path, "rb") as handle:
            signature = handle.read(2)
        if signature != b"MZ":
            raise AppRuntimeError("Downloaded update is not a valid EXE file.")
    expected_sha256 = owner._fetch_dist_asset_sha256(release_info=release_info)
    if not expected_sha256:
        if owner.UPDATE_REQUIRE_SHA256:
            raise AppRuntimeError("Update checksum file missing or invalid.")
    else:
        actual_sha256 = owner._sha256_file(new_path).strip().lower()
        if actual_sha256 != expected_sha256:
            raise AppRuntimeError("Downloaded update checksum mismatch.")
    if not update_asset_name.endswith(".zip"):
        owner._verify_downloaded_update_signature(new_path)
    return new_path


# --- Merged from update_checksum_service.py ---
"""Update checksum parsing and retrieval helpers."""

import re
from typing import Any


def extract_sha256_from_text(text: Any, asset_name: Any) -> Any:
    """Extract first matching SHA-256 digest from checksum text payload."""
    if not text:
        return None
    asset_name = str(asset_name or "").strip().lower()
    single_hash = re.compile(r"^[0-9a-fA-F]{64}$")
    hash_anywhere = re.compile(r"\b[0-9a-fA-F]{64}\b")
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        candidate = line.split("#", 1)[0].strip()
        if not candidate:
            continue
        if single_hash.fullmatch(candidate):
            return candidate.lower()
        if asset_name and asset_name not in candidate.lower():
            continue
        match = hash_anywhere.search(candidate)
        if match:
            return match.group(0).lower()
    return None


def fetch_dist_asset_sha256(owner: Any, release_info: Any=None) -> Any:
    """Fetch release checksum for target asset from known checksum candidates."""
    if release_info is None:
        try:
            release_info = owner._fetch_latest_release_info()
        except RuntimeError:
            release_info = None
    candidates = [f"{owner.GITHUB_ASSET_NAME}.sha256"]
    for name in owner.DIST_ASSET_SHA256_CANDIDATES:
        if name not in candidates:
            candidates.append(name)
    for name in candidates:
        data = None
        try:
            url = owner._release_asset_download_url(release_info, name)
            if not url:
                url = owner._dist_url(name)
            data = owner._download_bytes_with_retries(url)
        except RuntimeError:
            data = None
        if data is None:
            continue
        parsed = extract_sha256_from_text(
            data.decode("utf-8", errors="replace"),
            owner.GITHUB_ASSET_NAME,
        )
        if parsed:
            return parsed
    return None


# --- Merged from update_diag_service.py ---
"""Update diagnostics logging helpers."""

from datetime import datetime
from typing import Any


def log_update_failure(owner: Any, exc: Any, auto: Any=False, pretty_error: Any="") -> Any:
    """Append normalized update-failure diagnostics entry to runtime log file."""
    try:
        path = owner._diag_log_path()
        owner._trim_text_file_for_append(path, owner.DIAG_LOG_MAX_BYTES, owner.DIAG_LOG_KEEP_BYTES)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chain = []
        for err in owner._walk_exception_chain(exc, max_depth=5):
            chain.append(f"{type(err).__name__}: {str(err).strip()}")
        details = " | ".join(part for part in chain if part) or str(exc or "").strip()
        mode = "auto" if bool(auto) else "manual"
        entry = (
            "\n---\n"
            f"time={stamp}\n"
            f"context=update_failure\n"
            f"mode={mode}\n"
            f"summary={str(pretty_error or '').strip()}\n"
            f"detail={details}\n"
        )
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except (OSError, ValueError, TypeError):
        return


# --- Merged from update_fallback_service.py ---
"""Manual-update fallback prompt/open helpers."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def offer_manual_update_fallback(owner: Any, pretty_error: Any, askyesno_fn: Any, no_value: Any, open_url_fn: Any) -> Any:
    """Prompt for manual update fallback and open release page when accepted."""
    error_text = str(pretty_error or "").strip() or "Update failed."
    prompt = (
        f"{error_text}\n\n"
        "Would you like to open the manual update download page now?"
    )
    wants_open = bool(
        askyesno_fn(
            "Update",
            prompt,
            default=no_value,
        )
    )
    if not wants_open:
        return False
    url = owner._manual_update_download_url()
    if not url:
        return False
    try:
        open_url_fn(url)
        owner._set_status("Opened manual update download page.")
        return True
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        owner._set_status("Could not open browser for manual update download.")
        return False


# --- Merged from update_headers_service.py ---
"""Update request-header helpers."""
from typing import Any


def download_headers(token_value: Any="") -> Any:
    """Build update request headers with optional bearer token."""
    headers = {"User-Agent": "sins-editor"}
    token = str(token_value or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# --- Merged from update_orchestrator_service.py ---
"""Update orchestration service.

Coordinates update UI demo and real update flow while owner supplies
runtime dependencies and editor callbacks.
"""

import sys
import threading
import time
from tkinter import messagebox as _tk_messagebox
from typing import Any
from core.exceptions import EXPECTED_ERRORS

def run_update_ui_demo(owner: Any, auto: Any=False, sleep_fn: Any=time.sleep) -> Any:
    try:
        owner._set_status("Preparing update...")
        owner._ui_call(
            owner._show_update_overlay,
            "Preparing update...\nThe app will restart automatically.",
            wait=True,
        )
        owner._ui_call(
            owner._update_update_overlay,
            "Preparing update...\nThe app will restart automatically.",
            stage="preparing",
            wait=True,
        )
        sleep_fn(0.45)

        owner._set_status("Downloading update...")
        owner._ui_call(
            owner._update_update_overlay,
            "Downloading update...\nThis may take a moment.",
            stage="downloading",
            wait=True,
        )
        for _ in range(8):
            owner._ui_call(
                owner._update_update_overlay,
                stage="downloading",
                pulse=True,
                wait=True,
            )
            sleep_fn(0.12)

        owner._set_status("Installing update...")
        owner._ui_call(
            owner._update_update_overlay,
            "Installing update...\nThe app will restart automatically.",
            stage="installing",
            wait=True,
        )
        install_hold_ms = max(0, int(getattr(owner, "_update_install_stage_hold_ms", 3000) or 3000))
        sleep_fn(float(install_hold_ms) / 1000.0)

        owner._set_status("Update installed. Restarting app...")
        owner._ui_call(
            owner._update_update_overlay,
            "Update installed.\nRestarting app...",
            stage="restarting",
            wait=True,
        )
        restart_hold_ms = max(0, int(getattr(owner, "_update_restart_notice_ms", 4200) or 4200))
        sleep_fn(float(restart_hold_ms) / 1000.0)

        if not auto:
            owner._set_status("Update UI demo complete.")
            owner._ui_call(
                owner._show_themed_update_info,
                "Update",
                "Update UI demo complete.\nNo files were downloaded or installed.",
            )
    finally:
        owner._ui_call(owner._close_update_overlay)
        if auto:
            owner._set_status("")


def check_for_updates(owner: Any, auto: Any=False, messagebox: Any=None) -> Any:
    if messagebox is None:
        messagebox = _tk_messagebox
    if owner._update_ui_demo_enabled():
        threading.Thread(target=lambda: owner._run_update_ui_demo(auto=auto), daemon=True).start()
        return
    if not getattr(sys, "frozen", False):
        owner._set_status("You already have the latest version installed.")
        if not auto:
            owner._show_themed_update_info(
                "Update",
                "You already have the latest version installed.",
                True,
            )
        return
    if owner.GITHUB_OWNER == "YOUR_GITHUB_USERNAME" or owner.GITHUB_REPO == "YOUR_REPO_NAME":
        if not auto:
            owner._show_themed_update_info(
                "Update",
                "Set GITHUB_OWNER and GITHUB_REPO in the source to enable updates.",
            )
        return

    def worker() -> Any:
        install_started = False
        try:
            owner._set_status("Checking for updates...")
            latest_version = owner._fetch_dist_version()
            if not latest_version:
                owner._set_status("")
                if not auto:
                    owner._ui_call(owner._show_themed_update_info, "Update", "No release info available.")
                return

            latest_version = owner._release_version(latest_version)
            current_version = owner._release_version(owner.APP_VERSION)
            if latest_version and current_version and latest_version < current_version:
                owner._set_status("")
                if not auto:
                    owner._ui_call(
                        owner._show_themed_update_info,
                        "Update",
                        "Release version is older than this build.\n"
                        f"Release: v{owner._format_version(latest_version)}\n"
                        f"Current: v{owner._format_version(current_version)}\n"
                        "Check dist/version.txt.",
                    )
                return
            if latest_version == current_version:
                owner._set_status("Up to date.")
                if not auto:
                    owner._ui_call(
                        owner._show_themed_update_info,
                        "Update",
                        "You're already on the latest version.",
                        True,
                    )
                return

            prompt = (
                f"Update v{owner._format_version(latest_version)} is available.\n"
                "Do you want to install it now?\n\n"
                "The app will close and restart automatically."
            )
            if not owner._ui_call(
                owner._ask_themed_update_confirm,
                "Update",
                prompt,
                True,
                wait=True,
                default=False,
            ):
                owner._set_status("")
                return

            owner._ui_call(
                owner._show_update_overlay,
                "Preparing update...\nThe app will restart automatically.",
                wait=True,
            )
            owner._ui_call(
                owner._update_update_overlay,
                "Preparing update...\nThe app will restart automatically.",
                stage="preparing",
                wait=True,
            )
            owner._set_status("Downloading update...")
            owner._ui_call(
                owner._update_update_overlay,
                "Downloading update...\nThis may take a moment.",
                stage="downloading",
                wait=True,
            )
            new_path = owner._download_dist_asset()
            owner._ui_call(
                owner._update_update_overlay,
                "Installing update...\nThe app will restart automatically.",
                stage="installing",
                wait=True,
            )
            owner._set_status("Installing update...")
            install_hold_ms = max(0, int(getattr(owner, "_update_install_stage_hold_ms", 3000) or 3000))
            if install_hold_ms > 0:
                time.sleep(float(install_hold_ms) / 1000.0)
            install_started = True
            owner._install_update(new_path)
            owner._set_status("Update installed. Restarting app...")
            owner._ui_call(
                owner._update_update_overlay,
                "Update installed.\nRestarting app...",
                stage="restarting",
                wait=True,
            )
        except EXPECTED_ERRORS as exc:
            owner._set_status("")
            pretty_error = owner._format_update_error(exc)
            owner._log_update_failure(exc, auto=auto, pretty_error=pretty_error)
            if not auto:
                owner._ui_call(messagebox.showerror, "Update", pretty_error)
                owner._ui_call(owner._offer_manual_update_fallback, pretty_error, wait=True, default=False)
        finally:
            if auto and not install_started:
                owner._set_status("")
            # Keep overlay visible on successful install path so restart messaging remains visible
            # until the app closes and relaunches.
            if not install_started:
                owner._ui_call(owner._close_update_overlay)

    threading.Thread(target=worker, daemon=True).start()


# --- Merged from update_release_info_service.py ---
"""Latest-release metadata parsing helpers."""

import json
from typing import Any
from core.exceptions import AppRuntimeError


def parse_latest_release_info(raw_bytes: Any) -> Any:
    """Parse and validate latest-release API response payload."""
    try:
        parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        raise AppRuntimeError("No release info available.") from exc
    if not isinstance(parsed, dict):
        raise AppRuntimeError("No release info available.")
    return parsed


# --- Merged from update_service.py ---
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


# --- Merged from update_signature_service.py ---
"""Downloaded update signature verification helpers."""
from typing import Any
from core.exceptions import AppRuntimeError


def verify_downloaded_update_signature(owner: Any, path: Any, subprocess_module: Any, json_module: Any, os_module: Any, sys_module: Any) -> Any:
    """Verify downloaded update signature using Authenticode on Windows."""
    if not bool(getattr(owner, "UPDATE_VERIFY_AUTHENTICODE", True)):
        return
    if sys_module.platform != "win32":
        return
    check_path = os_module.path.abspath(path)
    escaped_path = check_path.replace("'", "''")
    ps_script = (
        "$ErrorActionPreference='Stop';"
        f"$sig=Get-AuthenticodeSignature -LiteralPath '{escaped_path}';"
        "[pscustomobject]@{"
        "Status=[string]$sig.Status;"
        "StatusMessage=[string]$sig.StatusMessage;"
        "Subject=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''});"
        "Thumbprint=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Thumbprint}else{''})"
        "} | ConvertTo-Json -Compress"
    )
    strict = bool(getattr(owner, "UPDATE_REQUIRE_AUTHENTICODE", False))
    allowed_subjects = tuple(
        str(item).strip().casefold()
        for item in (getattr(owner, "UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS", ()) or ())
        if str(item).strip()
    )
    # Prefer absolute system PowerShell path to avoid PATH-hijack risk on updater signature checks.
    ps_exe = os_module.path.join(
        os_module.environ.get("WINDIR", r"C:\Windows"),
        "System32",
        "WindowsPowerShell",
        "v1.0",
        "powershell.exe",
    )
    if not os_module.path.isfile(ps_exe):
        ps_exe = "powershell.exe"
    try:
        # Trusted local signature probe using fixed executable + static args.
        probe = subprocess_module.run(  # nosec B603
            [ps_exe, "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if probe.returncode != 0:
            raise AppRuntimeError((probe.stderr or probe.stdout or "").strip() or "signature check failed")
        payload = json_module.loads((probe.stdout or "").strip() or "{}")
        status = str(payload.get("Status", "")).strip()
        subject = str(payload.get("Subject", "")).strip()
        status_msg = str(payload.get("StatusMessage", "")).strip()
    except (subprocess_module.SubprocessError, OSError, RuntimeError, ValueError, json_module.JSONDecodeError) as exc:
        if strict:
            raise AppRuntimeError(f"Downloaded update signature check failed: {exc}") from exc
        return

    is_valid = status.lower() == "valid"
    if is_valid and allowed_subjects:
        subj_norm = subject.casefold()
        is_valid = any(token in subj_norm for token in allowed_subjects)
        if strict and not is_valid:
            raise AppRuntimeError("Downloaded update signature subject is not in allow-list.")

    if strict and not is_valid:
        detail = status_msg or status or "invalid signature"
        raise AppRuntimeError(f"Downloaded update Authenticode signature check failed: {detail}")


# --- Merged from update_ui_service.py ---
import logging
from typing import Any
from core.exceptions import EXPECTED_ERRORS

UPDATE_STAGE_DEFAULT_MESSAGE = {
    "preparing": "Preparing update...\nThe app will restart automatically.",
    "downloading": "Downloading update...\nThis may take a moment.",
    "installing": "Installing update...\nThe app will restart automatically.",
    "restarting": "Update installed.\nRestarting app...",
}

UPDATE_STAGE_TARGET_PCT = {
    "preparing": 10.0,
    "downloading": 62.0,
    "installing": 88.0,
    "restarting": 100.0,
}

UPDATE_LOADER_BAR_COLORS = {
    "track_top_bg": "#081a2c",
    "track_bottom_bg": "#140f22",
    "bar_top_fill": "#1f7a8f",
    "bar_bottom_fill": "#70479a",
}
_LOG = logging.getLogger(__name__)


def _log_ignored_exception(context, exc):
    _LOG.debug("%s: %s", context, exc)

def _widget_exists(widget):
    if widget is None:
        return False
    exists_fn = getattr(widget, "winfo_exists", None)
    if callable(exists_fn):
        try:
            return bool(exists_fn())
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            return False
    return True


def _safe_after_cancel(root, after_id):
    if root is None or not after_id:
        return
    try:
        root.after_cancel(after_id)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return


def _resolve_update_message(stage, message):
    if message:
        return str(message)
    token = str(stage or "").strip().lower()
    return UPDATE_STAGE_DEFAULT_MESSAGE.get(token, "Updating...")


def _resolve_stage_percent(stage, percent):
    if percent is not None:
        try:
            value = float(percent)
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            value = 0.0
        return max(0.0, min(100.0, value))
    token = str(stage or "").strip().lower()
    mapped = UPDATE_STAGE_TARGET_PCT.get(token)
    if mapped is None:
        return None
    return float(mapped)


def _apply_update_window_chrome(owner, overlay, root):
    if owner is None or overlay is None:
        return
    try:
        icon_setter = getattr(owner, "_set_window_icon_for", None)
        if callable(icon_setter):
            icon_setter(overlay)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    siindbad_theme = {}
    try:
        palette_getter = getattr(owner, "_theme_palette_for_variant", None)
        if callable(palette_getter):
            siindbad_theme = dict(palette_getter("SIINDBAD") or {})
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        siindbad_theme = {}
    bg = siindbad_theme.get("title_bar_bg")
    fg = siindbad_theme.get("title_bar_fg")
    border = siindbad_theme.get("title_bar_border")
    if not bg or not fg:
        theme = getattr(owner, "_theme", {}) or {}
        bg = bg or theme.get("title_bar_bg")
        fg = fg or theme.get("title_bar_fg")
        border = border or theme.get("title_bar_border")
    try:
        apply_titlebar = getattr(owner, "_apply_windows_titlebar_theme", None)
        if callable(apply_titlebar):
            apply_titlebar(bg=bg, fg=fg, border=border, window_widget=overlay)
            if root is not None:
                root.after(
                    0,
                    lambda win=overlay, b=bg, f=fg, bd=border: apply_titlebar(
                        bg=b,
                        fg=f,
                        border=bd,
                        window_widget=win,
                    ),
                )
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
def _render_update_overlay_progress(owner, value):
    try:
        pct = max(0.0, min(100.0, float(value)))
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return
    owner._update_overlay_progress_pct = pct
    pct_label = getattr(owner, "_update_overlay_pct_label", None)
    if pct_label is not None:
        try:
            pct_label.config(text=f"{int(round(pct))}%")
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
    top_bar = getattr(owner, "_update_overlay_top_bar", None)
    bottom_bar = getattr(owner, "_update_overlay_bottom_bar", None)
    try:
        if top_bar is not None:
            top_bar.configure(value=pct)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        if bottom_bar is not None:
            bottom_bar.configure(value=max(0.0, min(100.0, pct - 8.0)))
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
def show_themed_update_info(
    owner: Any,
    title: Any,
    message: Any,
    tk: Any,
    messagebox: Any,
    startup_check_state: Any=None,
    on_startup_check_change: Any=None,
) -> Any:
    root = getattr(owner, "root", None)
    if root is None:
        try:
            messagebox.showinfo(title, message)
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        return

    theme = getattr(owner, "_theme", {}) or {}
    panel_bg = theme.get("panel", "#161b24")
    window_bg = theme.get("bg", "#0f131a")
    fg = theme.get("fg", "#e6e6e6")
    border = theme.get("logo_border_outer", theme.get("find_border", "#2a5a7a"))
    title_bg = theme.get("title_bar_bg", panel_bg)
    title_fg = theme.get("title_bar_fg", fg)

    dlg = tk.Toplevel(root)
    try:
        dlg.withdraw()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.title(str(title or "Update"))
    try:
        dlg.transient(root)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.configure(bg=window_bg)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.resizable(False, False)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    shell = tk.Frame(
        dlg,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(
        shell,
        bg=title_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    header.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(
        header,
        text=str(title or "Update").upper(),
        bg=title_bg,
        fg=title_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        anchor="w",
        padx=10,
        pady=6,
    ).pack(fill="x")

    body = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    body.pack(fill="both", expand=True, padx=14, pady=(2, 8))
    tk.Label(
        body,
        text=str(message or ""),
        bg=panel_bg,
        fg=fg,
        justify="left",
        anchor="w",
        wraplength=420,
        font=(owner._preferred_mono_family(), 10),
        padx=0,
        pady=0,
    ).pack(fill="x", anchor="w")

    button_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    button_row.pack(fill="x", padx=10, pady=(0, 10))

    check_var = None
    check_applied = {"done": False}
    if startup_check_state is not None:
        check_var = tk.BooleanVar(value=bool(startup_check_state))
        check_btn = tk.Checkbutton(
            button_row,
            text="Check for updates on startup",
            variable=check_var,
            bg=panel_bg,
            fg=fg,
            activebackground=panel_bg,
            activeforeground=fg,
            selectcolor=theme.get("bg", "#0f131a"),
            highlightthickness=0,
            bd=0,
            font=(owner._preferred_mono_family(), 9),
            anchor="w",
            justify="left",
            padx=0,
            pady=0,
        )
        check_btn.pack(side="left", anchor="w")

    def apply_startup_toggle() -> Any:
        if check_var is None or check_applied["done"]:
            return
        check_applied["done"] = True
        if callable(on_startup_check_change):
            try:
                on_startup_check_change(bool(check_var.get()))
            except EXPECTED_ERRORS as exc:
                _log_ignored_exception("update_ui_service", exc)
    def close_dialog(event: Any=None) -> Any:
        apply_startup_toggle()
        try:
            dlg.grab_release()
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        try:
            dlg.destroy()
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        return "break" if event is not None else None

    ok_btn = tk.Button(
        button_row,
        text="OK",
        command=close_dialog,
        bg=theme.get("accent", "#202737"),
        fg=theme.get("select_fg", "#ffffff"),
        activebackground=theme.get("button_active", theme.get("accent", "#202737")),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    ok_btn.pack(side="right")

    try:
        owner._apply_centered_toplevel_geometry(
            dlg,
            width_px=500,
            height_px=190,
            anchor_window=root,
            min_width=420,
            min_height=170,
            max_width_ratio=0.70,
            max_height_ratio=0.45,
        )
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.protocol("WM_DELETE_WINDOW", close_dialog)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.bind("<Escape>", close_dialog, add="+")
    dlg.bind("<Return>", close_dialog, add="+")

    try:
        dlg.deiconify()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        owner._apply_windows_titlebar_theme(
            bg=theme.get("title_bar_bg"),
            fg=theme.get("title_bar_fg"),
            border=theme.get("title_bar_border"),
            window_widget=dlg,
        )
        root.after(
            0,
            lambda win=dlg, th=theme: owner._apply_windows_titlebar_theme(
                bg=th.get("title_bar_bg"),
                fg=th.get("title_bar_fg"),
                border=th.get("title_bar_border"),
                window_widget=win,
            ),
        )
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.lift()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.grab_set()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        ok_btn.focus_set()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.wait_window()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
def show_themed_update_confirm(
    owner: Any,
    title: Any,
    message: Any,
    tk: Any,
    messagebox: Any,
    startup_check_state: Any=None,
    on_startup_check_change: Any=None,
) -> Any:
    # Theme-aware Yes/No modal for update confirmation prompts.
    root = getattr(owner, "root", None)
    if root is None:
        try:
            return bool(messagebox.askyesno(title, message))
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            return False

    theme = getattr(owner, "_theme", {}) or {}
    panel_bg = theme.get("panel", "#161b24")
    window_bg = theme.get("bg", "#0f131a")
    fg = theme.get("fg", "#e6e6e6")
    border = theme.get("logo_border_outer", theme.get("find_border", "#2a5a7a"))
    title_bg = theme.get("title_bar_bg", panel_bg)
    title_fg = theme.get("title_bar_fg", fg)

    dlg = tk.Toplevel(root)
    try:
        dlg.withdraw()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.title(str(title or "Update"))
    try:
        dlg.transient(root)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.configure(bg=window_bg)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.resizable(False, False)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    shell = tk.Frame(
        dlg,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(
        shell,
        bg=title_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    header.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(
        header,
        text=str(title or "Update").upper(),
        bg=title_bg,
        fg=title_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        anchor="w",
        padx=10,
        pady=6,
    ).pack(fill="x")

    body = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    body.pack(fill="both", expand=True, padx=14, pady=(2, 8))
    tk.Label(
        body,
        text=str(message or ""),
        bg=panel_bg,
        fg=fg,
        justify="left",
        anchor="w",
        wraplength=420,
        font=(owner._preferred_mono_family(), 10),
        padx=0,
        pady=0,
    ).pack(fill="x", anchor="w")

    button_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    button_row.pack(fill="x", padx=10, pady=(0, 10))

    result = {"value": False}
    check_var = None
    check_applied = {"done": False}
    if startup_check_state is not None:
        check_var = tk.BooleanVar(value=bool(startup_check_state))
        check_btn = tk.Checkbutton(
            button_row,
            text="Check for updates on startup",
            variable=check_var,
            bg=panel_bg,
            fg=fg,
            activebackground=panel_bg,
            activeforeground=fg,
            selectcolor=theme.get("bg", "#0f131a"),
            highlightthickness=0,
            bd=0,
            font=(owner._preferred_mono_family(), 9),
            anchor="w",
            justify="left",
            padx=0,
            pady=0,
        )
        check_btn.pack(side="left", anchor="w")

    def apply_startup_toggle() -> Any:
        if check_var is None or check_applied["done"]:
            return
        check_applied["done"] = True
        if callable(on_startup_check_change):
            try:
                on_startup_check_change(bool(check_var.get()))
            except EXPECTED_ERRORS as exc:
                _log_ignored_exception("update_ui_service", exc)
    def close_dialog(event: Any=None) -> Any:
        apply_startup_toggle()
        try:
            dlg.grab_release()
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        try:
            dlg.destroy()
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        return "break" if event is not None else None

    def choose_yes(event: Any=None) -> Any:
        result["value"] = True
        return close_dialog(event)

    def choose_no(event: Any=None) -> Any:
        result["value"] = False
        return close_dialog(event)

    yes_btn = tk.Button(
        button_row,
        text="Yes",
        command=choose_yes,
        bg=theme.get("accent", "#202737"),
        fg=theme.get("select_fg", "#ffffff"),
        activebackground=theme.get("button_active", theme.get("accent", "#202737")),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    yes_btn.pack(side="right")

    no_btn = tk.Button(
        button_row,
        text="No",
        command=choose_no,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    no_btn.pack(side="right", padx=(0, 8))

    try:
        owner._apply_centered_toplevel_geometry(
            dlg,
            width_px=500,
            height_px=210,
            anchor_window=root,
            min_width=420,
            min_height=180,
            max_width_ratio=0.70,
            max_height_ratio=0.46,
        )
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.protocol("WM_DELETE_WINDOW", choose_no)
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.bind("<Escape>", choose_no, add="+")
    dlg.bind("<Return>", choose_yes, add="+")

    try:
        dlg.deiconify()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        owner._apply_windows_titlebar_theme(
            bg=theme.get("title_bar_bg"),
            fg=theme.get("title_bar_fg"),
            border=theme.get("title_bar_border"),
            window_widget=dlg,
        )
        root.after(
            0,
            lambda win=dlg, th=theme: owner._apply_windows_titlebar_theme(
                bg=th.get("title_bar_bg"),
                fg=th.get("title_bar_fg"),
                border=th.get("title_bar_border"),
                window_widget=win,
            ),
        )
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.lift()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.grab_set()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        yes_btn.focus_set()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.wait_window()
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    return bool(result["value"])


def show_update_overlay(owner: Any, message: Any, tk: Any, ttk: Any) -> Any:
    # Blocking progress overlay while update download/apply is in progress.
    if getattr(owner, "_update_overlay", None):
        return
    overlay = tk.Toplevel(owner.root)
    overlay.title("Updating...")
    popup_scale = max(0.9, min(1.25, float(getattr(owner, "_display_scale", 1.0) or 1.0)))
    owner._apply_centered_toplevel_geometry(
        overlay,
        width_px=int(round(360 * popup_scale)),
        height_px=int(round(120 * popup_scale)),
        min_width=320,
        min_height=110,
        max_width_ratio=0.72,
        max_height_ratio=0.40,
    )
    overlay.resizable(False, False)
    overlay.transient(owner.root)
    overlay.grab_set()
    _apply_update_window_chrome(owner, overlay, getattr(owner, "root", None))
    frame = ttk.Frame(overlay, padding=12)
    frame.pack(fill="both", expand=True)

    header = tk.Frame(frame, bg=getattr(owner, "_theme", {}).get("panel", "#161b24"), bd=0, highlightthickness=0)
    header.pack(fill="x", pady=(0, 8))

    title_prefix = tk.Label(
        header,
        text="UPDATE SYSTEM SYNC",
        bg=getattr(owner, "_theme", {}).get("panel", "#161b24"),
        fg=getattr(owner, "_theme", {}).get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="w",
        justify="left",
    )
    title_prefix.pack(side="left")

    pct_label = tk.Label(
        header,
        text="0%",
        bg=getattr(owner, "_theme", {}).get("panel", "#161b24"),
        fg=getattr(owner, "_theme", {}).get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="e",
        justify="right",
    )
    pct_label.pack(side="right")

    label = ttk.Label(frame, text=_resolve_update_message("preparing", message))
    label.pack(anchor="w", pady=(0, 8))
    top_bar = ttk.Progressbar(frame, mode="determinate", maximum=100)
    top_bar.pack(fill="x")
    bottom_bar = ttk.Progressbar(frame, mode="determinate", maximum=100)
    bottom_bar.pack(fill="x", pady=(6, 0))

    owner._update_overlay = overlay
    owner._update_overlay_label = label
    owner._update_overlay_top_bar = top_bar
    owner._update_overlay_bottom_bar = bottom_bar
    owner._update_overlay_pct_label = pct_label
    owner._update_overlay_title_prefix_label = title_prefix
    owner._update_overlay_title_suffix_label = None
    owner._update_overlay_title_variant = "UPDATE"
    owner._update_overlay_title_after_id = None
    owner._update_overlay_progress_pct = 0.0
    owner._update_overlay_stage = "preparing"
    try:
        style = ttk.Style(overlay)
        style.configure(
            "Update.Top.Horizontal.TProgressbar",
            troughcolor=UPDATE_LOADER_BAR_COLORS["track_top_bg"],
            background=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            darkcolor=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            lightcolor=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            bordercolor=UPDATE_LOADER_BAR_COLORS["track_top_bg"],
            thickness=11,
        )
        style.configure(
            "Update.Bottom.Horizontal.TProgressbar",
            troughcolor=UPDATE_LOADER_BAR_COLORS["track_bottom_bg"],
            background=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            darkcolor=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            lightcolor=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            bordercolor=UPDATE_LOADER_BAR_COLORS["track_bottom_bg"],
            thickness=11,
        )
        top_bar.configure(style="Update.Top.Horizontal.TProgressbar")
        bottom_bar.configure(style="Update.Bottom.Horizontal.TProgressbar")
    except EXPECTED_ERRORS as exc:
        _log_ignored_exception("update_ui_service", exc)
    if getattr(owner, "_theme", None):
        theme = owner._theme
        overlay.configure(bg=theme["bg"])
        try:
            frame.configure(style="Update.TFrame")
            label.configure(background=theme["bg"], foreground=theme["fg"])
            style = ttk.Style(overlay)
            style.configure("Update.TFrame", background=theme["bg"])
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
    _render_update_overlay_progress(owner, UPDATE_STAGE_TARGET_PCT["preparing"])


def update_update_overlay(owner: Any, message: Any=None, stage: Any=None, percent: Any=None, pulse: Any=False) -> Any:
    # Update progress text + staged percentage without rebuilding overlay widgets.
    overlay = getattr(owner, "_update_overlay", None)
    label = getattr(owner, "_update_overlay_label", None)
    if overlay and label and _widget_exists(overlay):
        stage_token = str(stage or "").strip().lower()
        if stage_token:
            owner._update_overlay_stage = stage_token
        shown_message = _resolve_update_message(stage_token, message)
        try:
            label.config(text=shown_message)
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
        target_pct = _resolve_stage_percent(stage_token, percent)
        if target_pct is not None:
            _render_update_overlay_progress(owner, target_pct)
        elif bool(pulse):
            current = float(getattr(owner, "_update_overlay_progress_pct", 0.0) or 0.0)
            # Keep download stage moving subtly when byte totals are unknown.
            pulse_target = max(0.0, min(96.0, current + 1.2))
            _render_update_overlay_progress(owner, pulse_target)


def close_update_overlay(owner: Any) -> Any:
    # Remove overlay and clear cached widget references.
    root = getattr(owner, "root", None)
    _safe_after_cancel(root, getattr(owner, "_update_overlay_title_after_id", None))
    owner._update_overlay_title_after_id = None
    overlay = getattr(owner, "_update_overlay", None)
    if overlay:
        try:
            overlay.destroy()
        except EXPECTED_ERRORS as exc:
            _log_ignored_exception("update_ui_service", exc)
    owner._update_overlay = None
    owner._update_overlay_label = None
    owner._update_overlay_top_bar = None
    owner._update_overlay_bottom_bar = None
    owner._update_overlay_pct_label = None
    owner._update_overlay_title_prefix_label = None
    owner._update_overlay_title_suffix_label = None
    owner._update_overlay_title_variant = "SIINDBAD"
    owner._update_overlay_progress_pct = 0.0
    owner._update_overlay_stage = ""


# --- Merged from update_url_service.py ---
"""Update/release URL builder helpers."""
from typing import Any


def manual_update_download_url(owner: Any) -> Any:
    """Build manual update fallback URL using GitHub Releases latest asset path."""
    return (
        f"https://github.com/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}"
        f"/releases/latest/download/{owner.GITHUB_ASSET_NAME}"
    )


def dist_url(owner: Any, filename: Any) -> Any:
    """Build fallback release-asset URL for a filename."""
    return (
        f"https://github.com/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}"
        f"/releases/latest/download/{filename}"
    )


def latest_release_api_url(owner: Any) -> Any:
    """Build GitHub API URL for latest release metadata."""
    return f"https://api.github.com/repos/{owner.GITHUB_OWNER}/{owner.GITHUB_REPO}/releases/latest"


def release_asset_download_url(release_info: Any, asset_name: Any) -> Any:
    """Resolve browser_download_url for named asset from release metadata payload."""
    if not isinstance(release_info, dict):
        return ""
    want = str(asset_name or "").strip().casefold()
    if not want:
        return ""
    assets = release_info.get("assets")
    if not isinstance(assets, list):
        return ""
    for item in assets:
        if not isinstance(item, dict):
            continue
        if str(item.get("name", "")).strip().casefold() != want:
            continue
        return str(item.get("browser_download_url", "")).strip()
    return ""


# --- Merged from update_version_service.py ---
"""Update version resolution helpers."""
from typing import Any


def fetch_dist_version(owner: Any) -> Any:
    """Resolve latest dist version with release-tag preference and file fallback."""
    # Prefer immutable release metadata (tag) over mutable branch files.
    release_info = None
    try:
        release_info = owner._fetch_latest_release_info()
    except RuntimeError:
        release_info = None
    if isinstance(release_info, dict):
        tag_name = str(release_info.get("tag_name", "")).strip()
        if tag_name:
            return tag_name

    # Compatibility fallback: read version asset from latest release download URL.
    url = owner._dist_url(owner.DIST_VERSION_FILE)
    data = owner._download_bytes_with_retries(url)
    data = data.decode("utf-8", errors="replace")
    return data.strip()


# --- Compatibility dispatch for former update_download_service API ---
_update_download_bytes_with_retries_core = download_bytes_with_retries
_update_download_to_file_with_retries_core = download_to_file_with_retries


class _UpdateServiceCompatProxy:
    """Compatibility proxy used by callers that monkeypatch update_download_service.update_service."""

    download_bytes_with_retries = staticmethod(_update_download_bytes_with_retries_core)
    download_to_file_with_retries = staticmethod(_update_download_to_file_with_retries_core)
    is_retryable_download_error = staticmethod(is_retryable_download_error)
    download_backoff_delay = staticmethod(download_backoff_delay)


update_service = _UpdateServiceCompatProxy()


def _looks_like_download_owner(value: Any) -> bool:
    return value is not None and hasattr(value, "_download_headers")


def download_bytes_with_retries(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API: supports raw transport call and owner-based wrapper call."""
    if args and _looks_like_download_owner(args[0]) and "headers" not in kwargs:
        owner = args[0]
        url = kwargs.get("url", args[1] if len(args) > 1 else None)
        attempts = kwargs.get("attempts", 3)
        timeout = kwargs.get("timeout", 60)
        request_factory = kwargs.get("request_factory", None)
        urlopen_fn = kwargs.get("urlopen_fn", None)
        is_retryable_fn = kwargs.get("is_retryable_fn", None)
        backoff_fn = kwargs.get("backoff_fn", None)
        sleep_fn = kwargs.get("sleep_fn", None)

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

    return _update_download_bytes_with_retries_core(*args, **kwargs)


def download_to_file_with_retries(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API: supports raw transport call and owner-based wrapper call."""
    if args and _looks_like_download_owner(args[0]) and "headers" not in kwargs:
        owner = args[0]
        url = kwargs.get("url", args[1] if len(args) > 1 else None)
        out_path = kwargs.get("out_path", args[2] if len(args) > 2 else None)
        attempts = kwargs.get("attempts", 3)
        timeout = kwargs.get("timeout", 60)
        chunk_size = kwargs.get("chunk_size", 1024 * 1024)
        request_factory = kwargs.get("request_factory", None)
        urlopen_fn = kwargs.get("urlopen_fn", None)
        is_retryable_fn = kwargs.get("is_retryable_fn", None)
        backoff_fn = kwargs.get("backoff_fn", None)
        sleep_fn = kwargs.get("sleep_fn", None)

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

    return _update_download_to_file_with_retries_core(*args, **kwargs)
