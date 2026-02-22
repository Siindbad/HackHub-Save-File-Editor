#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VT_API_BASE = "https://www.virustotal.com/api/v3"
DEFAULT_TARGET = ROOT / "dist" / "sins_editor.exe"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run VirusTotal release evidence gate (hash lookup first, optional upload fallback)."
        )
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_TARGET),
        help="Path to file artifact to check in VirusTotal.",
    )
    parser.add_argument(
        "--allow-upload",
        action="store_true",
        help="Upload file to VirusTotal when hash lookup has no report.",
    )
    parser.add_argument(
        "--require-key",
        action="store_true",
        help="Fail when VirusTotal API key is missing.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on malicious hits and API execution errors.",
    )
    parser.add_argument(
        "--fail-on-suspicious",
        action="store_true",
        help="Treat suspicious detections as blocking in strict mode.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=60,
        help="Max seconds to wait for uploaded analysis completion.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=5.0,
        help="Polling interval for uploaded analysis checks.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=45,
        help="HTTP timeout for VirusTotal API requests.",
    )
    return parser.parse_args()


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _strict_enabled(cli_strict: bool) -> bool:
    if cli_strict:
        return True
    # VirusTotal strict mode toggle:
    # - HACKHUB_VT_STRICT=1 => fail on malicious/suspicious(policy) and API execution errors
    # - HACKHUB_VT_STRICT=0 => report result details but keep release flow non-blocking
    return _truthy(os.getenv("HACKHUB_VT_STRICT", ""))


def _require_key_enabled(cli_required: bool) -> bool:
    if cli_required:
        return True
    # API key requirement toggle:
    # - HACKHUB_VT_REQUIRE_KEY=1 => missing key fails
    # - HACKHUB_VT_REQUIRE_KEY=0 => missing key reports SKIPPED and continues
    return _truthy(os.getenv("HACKHUB_VT_REQUIRE_KEY", ""))


def _upload_enabled(cli_allow_upload: bool) -> bool:
    if cli_allow_upload:
        return True
    # Upload toggle:
    # - HACKHUB_VT_ALLOW_UPLOAD=1 => upload when hash has no report
    # - HACKHUB_VT_ALLOW_UPLOAD=0 => hash lookup only (default)
    return _truthy(os.getenv("HACKHUB_VT_ALLOW_UPLOAD", ""))


def _fail_on_suspicious_enabled(cli_value: bool) -> bool:
    if cli_value:
        return True
    # Suspicious threshold toggle:
    # - HACKHUB_VT_FAIL_ON_SUSPICIOUS=1 => suspicious detections can block in strict mode
    # - HACKHUB_VT_FAIL_ON_SUSPICIOUS=0 => only malicious detections can block
    return _truthy(os.getenv("HACKHUB_VT_FAIL_ON_SUSPICIOUS", ""))


def _api_key() -> str:
    key = str(os.getenv("VIRUSTOTAL_API_KEY", "")).strip()
    if key:
        return key
    return str(os.getenv("VT_API_KEY", "")).strip()


def _http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    timeout_seconds: int,
    payload: bytes | None = None,
) -> tuple[int, dict[str, Any] | None, str]:
    request = urllib.request.Request(url=url, data=payload, method=method)
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                data = None
            return int(getattr(response, "status", 200)), data if isinstance(data, dict) else None, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            data = None
        return int(exc.code), data if isinstance(data, dict) else None, raw
    except urllib.error.URLError as exc:
        return 0, None, str(exc.reason)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_stats(payload: dict[str, Any] | None) -> dict[str, int]:
    stats = {}
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            attrs = data.get("attributes")
            if isinstance(attrs, dict):
                candidate = attrs.get("last_analysis_stats") or attrs.get("stats")
                if isinstance(candidate, dict):
                    stats = candidate
    return {
        "malicious": int(stats.get("malicious", 0) or 0),
        "suspicious": int(stats.get("suspicious", 0) or 0),
        "harmless": int(stats.get("harmless", 0) or 0),
        "undetected": int(stats.get("undetected", 0) or 0),
    }


def _extract_analysis_id(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("id", "")).strip()


def _extract_analysis_status(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    if not isinstance(data, dict):
        return ""
    attrs = data.get("attributes")
    if not isinstance(attrs, dict):
        return ""
    return str(attrs.get("status", "")).strip().lower()


def _extract_analysis_sha256(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    meta = payload.get("meta")
    if isinstance(meta, dict):
        file_info = meta.get("file_info")
        if isinstance(file_info, dict):
            value = str(file_info.get("sha256", "")).strip()
            if value:
                return value
    data = payload.get("data")
    if isinstance(data, dict):
        attrs = data.get("attributes")
        if isinstance(attrs, dict):
            meta_obj = attrs.get("meta")
            if isinstance(meta_obj, dict):
                file_info = meta_obj.get("file_info")
                if isinstance(file_info, dict):
                    return str(file_info.get("sha256", "")).strip()
    return ""


def _multipart_file_payload(path: Path, *, boundary: str) -> bytes:
    filename = path.name
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return head + path.read_bytes() + tail


def _get_upload_url(*, headers: dict[str, str], timeout_seconds: int) -> str:
    status, payload, _ = _http_json(
        "GET",
        f"{VT_API_BASE}/files/upload_url",
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    if status != 200 or not isinstance(payload, dict):
        return ""
    data = payload.get("data")
    return str(data).strip() if data else ""


def _upload_file(
    path: Path,
    *,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[int, dict[str, Any] | None, str]:
    upload_url = f"{VT_API_BASE}/files"
    if path.stat().st_size > 32 * 1024 * 1024:
        large_url = _get_upload_url(headers=headers, timeout_seconds=timeout_seconds)
        if not large_url:
            return 0, None, "Failed to resolve VirusTotal large-file upload URL."
        upload_url = large_url

    boundary = f"----HackHubBoundary{int(time.time() * 1000)}"
    body = _multipart_file_payload(path, boundary=boundary)
    upload_headers = dict(headers)
    upload_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    return _http_json(
        "POST",
        upload_url,
        headers=upload_headers,
        timeout_seconds=timeout_seconds,
        payload=body,
    )


def _analysis_url(analysis_id: str) -> str:
    clean = urllib.parse.quote(str(analysis_id).strip(), safe="")
    return f"{VT_API_BASE}/analyses/{clean}"


def _file_url(sha256: str) -> str:
    clean = urllib.parse.quote(str(sha256).strip(), safe="")
    return f"{VT_API_BASE}/files/{clean}"


def _permalink(sha256: str) -> str:
    clean = str(sha256 or "").strip().lower()
    if not clean:
        return ""
    return f"https://www.virustotal.com/gui/file/{clean}/detection"


def main() -> int:
    args = _parse_args()
    strict = _strict_enabled(args.strict)
    require_key = _require_key_enabled(args.require_key)
    allow_upload = _upload_enabled(args.allow_upload)
    fail_on_suspicious = _fail_on_suspicious_enabled(args.fail_on_suspicious)
    wait_seconds = max(0, int(args.wait_seconds))
    poll_interval_seconds = max(1.0, float(args.poll_interval_seconds))
    timeout_seconds = max(5, int(args.timeout_seconds))

    target_path = Path(args.file)
    if not target_path.is_absolute():
        target_path = ROOT / target_path
    if not target_path.exists():
        print(f"VirusTotal gate failed: target file not found: {target_path}")
        return 1

    key = _api_key()
    if not key:
        print("VirusTotal API key not configured (VIRUSTOTAL_API_KEY or VT_API_KEY).")
        print(
            "VirusTotal summary: "
            "status=SKIPPED, source=no_api_key, sha256=none, "
            "malicious=0, suspicious=0, harmless=0, undetected=0, timeout=false"
        )
        if require_key:
            print("VirusTotal gate failed: API key required but missing.")
            return 1
        return 0

    headers = {
        "x-apikey": key,
        "accept": "application/json",
        "user-agent": "hackhub-release-vt-gate/1.0",
    }

    file_sha256 = _sha256_file(target_path)
    stats = {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0}
    status_label = "PASS"
    source_label = "hash_lookup"
    timeout_reached = False

    lookup_status, lookup_payload, lookup_text = _http_json(
        "GET",
        _file_url(file_sha256),
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    if lookup_status == 200:
        stats = _extract_stats(lookup_payload)
    elif lookup_status == 404:
        source_label = "hash_miss"
        if allow_upload:
            upload_status, upload_payload, upload_text = _upload_file(
                target_path,
                headers=headers,
                timeout_seconds=timeout_seconds,
            )
            if upload_status not in (200, 201) or not isinstance(upload_payload, dict):
                status_label = "ERROR"
                source_label = "upload_error"
                print(f"VirusTotal upload failed: status={upload_status} details={upload_text.strip()}")
            else:
                source_label = "uploaded"
                analysis_id = _extract_analysis_id(upload_payload)
                if not analysis_id:
                    status_label = "ERROR"
                    source_label = "upload_no_analysis_id"
                    print("VirusTotal upload failed: missing analysis id.")
                elif wait_seconds <= 0:
                    status_label = "PENDING"
                else:
                    deadline = time.time() + wait_seconds
                    last_payload = None
                    while time.time() <= deadline:
                        analysis_status, analysis_payload, analysis_text = _http_json(
                            "GET",
                            _analysis_url(analysis_id),
                            headers=headers,
                            timeout_seconds=timeout_seconds,
                        )
                        if analysis_status != 200:
                            status_label = "ERROR"
                            source_label = "analysis_error"
                            print(
                                "VirusTotal analysis polling failed: "
                                f"status={analysis_status} details={analysis_text.strip()}"
                            )
                            break
                        last_payload = analysis_payload
                        state = _extract_analysis_status(analysis_payload)
                        if state == "completed":
                            analysis_sha = _extract_analysis_sha256(analysis_payload) or file_sha256
                            file_status, file_payload, _ = _http_json(
                                "GET",
                                _file_url(analysis_sha),
                                headers=headers,
                                timeout_seconds=timeout_seconds,
                            )
                            if file_status == 200:
                                stats = _extract_stats(file_payload)
                                source_label = "uploaded_report"
                            else:
                                stats = _extract_stats(analysis_payload)
                                source_label = "uploaded_analysis"
                            break
                        time.sleep(poll_interval_seconds)
                    else:
                        timeout_reached = True
                        status_label = "PENDING"
                    if (
                        last_payload is not None
                        and status_label not in {"ERROR", "PENDING"}
                        and stats == {"malicious": 0, "suspicious": 0, "harmless": 0, "undetected": 0}
                    ):
                        stats = _extract_stats(last_payload)
        else:
            status_label = "SKIPPED"
            print("VirusTotal hash not found and upload fallback disabled.")
    else:
        status_label = "ERROR"
        source_label = "lookup_error"
        print(f"VirusTotal lookup failed: status={lookup_status} details={lookup_text.strip()}")

    malicious = int(stats["malicious"])
    suspicious = int(stats["suspicious"])
    harmless = int(stats["harmless"])
    undetected = int(stats["undetected"])

    if status_label == "PASS":
        if malicious > 0:
            status_label = "DETECTED"
        elif suspicious > 0 and fail_on_suspicious:
            status_label = "SUSPICIOUS"

    permalink = _permalink(file_sha256)
    print(
        "VirusTotal summary: "
        f"status={status_label}, "
        f"source={source_label}, "
        f"sha256={file_sha256}, "
        f"malicious={malicious}, "
        f"suspicious={suspicious}, "
        f"harmless={harmless}, "
        f"undetected={undetected}, "
        f"timeout={'true' if timeout_reached else 'false'}"
    )
    if permalink:
        print(f"VirusTotal permalink: {permalink}")

    should_block = False
    if strict:
        if status_label in {"ERROR", "DETECTED"}:
            should_block = True
        if fail_on_suspicious and status_label == "SUSPICIOUS":
            should_block = True
    if require_key and not key:
        should_block = True
    if should_block:
        print("VirusTotal gate failed in strict mode.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
