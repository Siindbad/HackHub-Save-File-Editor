"""Consolidated telemetry/support domain master.

Contains merged logic from bug_report_* and crash_* support modules.
"""


# --- Merged from bug_report_api_service.py ---
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from core.exceptions import EXPECTED_ERRORS
from core.exceptions import AppRuntimeError
import logging
_LOG = logging.getLogger(__name__)


def _build_multipart_form_data(parts: list[dict[str, Any]]) -> tuple[bytes, str]:
    """Build multipart/form-data payload for Discord webhook file uploads."""
    boundary = "----sins-editor-" + os.urandom(12).hex()
    chunks: list[bytes] = []
    for part in parts:
        name = str(part.get("name", "")).strip()
        if not name:
            continue
        filename = str(part.get("filename", "")).strip()
        content_type = str(part.get("content_type", "")).strip()
        data = part.get("data", b"")
        if isinstance(data, str):
            body_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            body_bytes = data
        else:
            body_bytes = str(data).encode("utf-8")

        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        disposition = f'Content-Disposition: form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        chunks.append((disposition + "\r\n").encode("utf-8"))
        if content_type:
            chunks.append((f"Content-Type: {content_type}\r\n").encode("utf-8"))
        chunks.append(b"\r\n")
        chunks.append(body_bytes)
        chunks.append(b"\r\n")

    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _assert_https_host_allowed(url_text, allowed_hosts):
    parsed = urllib.parse.urlparse(str(url_text or "").strip())
    host = (parsed.hostname or "").strip().lower()
    scheme = (parsed.scheme or "").strip().lower()
    if scheme != "https":
        raise AppRuntimeError("Refusing non-HTTPS request URL.")
    if not host:
        raise AppRuntimeError("Request URL is missing a host.")
    normalized_allowed = tuple(str(item or "").strip().lower() for item in allowed_hosts or ())
    for allowed in normalized_allowed:
        if not allowed:
            continue
        if host == allowed or host.endswith("." + allowed):
            return
    raise AppRuntimeError(f"Request host '{host}' is not allowlisted.")


def _open_https_request(req, *, timeout, allowed_hosts):
    target_url = getattr(req, "full_url", "")
    _assert_https_host_allowed(target_url, allowed_hosts)
    opener = urllib.request.build_opener()
    return opener.open(req, timeout=timeout)


def _resolve_open_https_request():
    """Allow runtime monkeypatching through bug_report_api_service shim module."""
    try:
        from core.domain_impl.support import bug_report_api_service as _api_mod

        patched = getattr(_api_mod, "_open_https_request", None)
        if callable(patched):
            return patched
    except (ImportError, AttributeError, TypeError):
        pass
    return _open_https_request


def open_bug_report_in_browser(issue_url: Any, open_new_tab_fn: Any) -> Any:
    if not open_new_tab_fn(issue_url):
        raise AppRuntimeError("Failed to open browser issue form.")
    return issue_url


def upload_bug_screenshot(
    *,
    source_path: Any,
    summary: Any,
    token_env_name: Any,
    owner: Any,
    repo: Any,
    branch: Any,
    validate_file_fn: Any,
    detect_magic_ext_fn: Any,
    build_repo_path_fn: Any,
    prepare_upload_bytes_fn: Any,
) -> Any:
    # Required for API upload path: token_env_name should point to a PAT/GitHub token env var.
    token = os.getenv(token_env_name, "").strip()
    if not token:
        raise AppRuntimeError(f"Missing {token_env_name} token in environment.")

    validated_source = validate_file_fn(source_path)
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise AppRuntimeError("Bug report repo is not configured.")
    detected_ext = detect_magic_ext_fn(validated_source)
    if not detected_ext:
        raise AppRuntimeError("Selected file is not a valid supported image.")

    source_name = os.path.splitext(os.path.basename(validated_source))[0] + detected_ext
    repo_path = build_repo_path_fn(source_name, summary=summary)
    use_branch = str(branch or "main").strip() or "main"
    url = f"https://api.github.com/repos/{use_owner}/{use_repo}/contents/{repo_path}"
    raw_bytes, _mime_type = prepare_upload_bytes_fn(validated_source, detected_ext)

    payload = {
        "message": f"chore(bug-upload): add {os.path.basename(repo_path)}",
        "content": base64.b64encode(raw_bytes).decode("ascii"),
        "branch": use_branch,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "User-Agent": "sins-editor-bug-upload",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
    try:
        with _resolve_open_https_request()(req, timeout=45, allowed_hosts=("api.github.com",)) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            detail = str(exc)
        raise AppRuntimeError(f"Screenshot upload API error ({exc.code}): {detail}") from exc
    except EXPECTED_ERRORS as exc:
        raise AppRuntimeError(f"Failed to upload screenshot: {exc}") from exc

    parsed = {}
    try:
        parsed = json.loads(raw) if raw else {}
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        parsed = {}
    content_block = parsed.get("content") if isinstance(parsed, dict) else {}
    download_url = ""
    if isinstance(content_block, dict):
        download_url = str(content_block.get("download_url", "")).strip()
    if not download_url:
        download_url = f"https://raw.githubusercontent.com/{use_owner}/{use_repo}/{use_branch}/{repo_path}"
    return {
        "repo_path": repo_path,
        "download_url": download_url,
        "filename": os.path.basename(repo_path),
    }


def submit_bug_report_issue(
    *,
    token_env_name: Any,
    owner: Any,
    repo: Any,
    labels: Any,
    title: Any,
    body_markdown: Any,
    open_browser_fn: Any,
) -> Any:
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise AppRuntimeError("Bug report repo is not configured.")

    # Optional for issue create API; when missing we fall back to browser-based report flow.
    token = os.getenv(token_env_name, "").strip()
    if not token:
        return open_browser_fn(title, body_markdown)

    url = f"https://api.github.com/repos/{use_owner}/{use_repo}/issues"
    payload = {
        "title": title,
        "body": body_markdown,
        "labels": list(labels),
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "User-Agent": "sins-editor-bug-report",
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with _resolve_open_https_request()(req, timeout=35, allowed_hosts=("api.github.com",)) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            detail = str(exc)
        try:
            return open_browser_fn(title, body_markdown)
        except EXPECTED_ERRORS as fallback_exc:
            raise AppRuntimeError(
                f"GitHub API error ({exc.code}): {detail}. "
                f"Browser fallback failed: {fallback_exc}"
            ) from exc
    except EXPECTED_ERRORS as exc:
        try:
            return open_browser_fn(title, body_markdown)
        except EXPECTED_ERRORS as fallback_exc:
            raise AppRuntimeError(
                f"Failed to submit issue: {exc}. Browser fallback failed: {fallback_exc}"
            ) from exc

    try:
        parsed = json.loads(raw) if raw else {}
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        parsed = {}
    issue_url = str(parsed.get("html_url", "")).strip()
    if not issue_url:
        raise AppRuntimeError("Issue was created but no issue URL was returned.")
    return issue_url


def parse_discord_forum_tag_ids(raw_tag_ids: Any) -> Any:
    # Forum tags can be configured as comma/space-separated numeric IDs.
    text = str(raw_tag_ids or "").strip()
    if not text:
        return []
    parts = re.split(r"[,\s]+", text)
    seen = set()
    cleaned = []
    for part in parts:
        token = str(part or "").strip()
        if not token or not token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(token)
    return cleaned


def submit_bug_report_discord_forum(
    *,
    webhook_env_name: Any,
    summary: Any,
    details: Any,
    issue_url: Any,
    app_version: Any,
    theme_variant: Any,
    selected_path: Any,
    last_json_error: Any,
    last_highlight_note: Any,
    now_text: Any="",
    python_version: Any="",
    platform_text: Any="",
    include_diag: Any=False,
    diag_tail: Any="",
    crash_tail: Any="",
    discord_contact: Any="",
    screenshot_url: Any="",
    screenshot_filename: Any="",
    screenshot_note: Any="",
    forum_tag_ids_raw: Any="",
) -> Any:
    # Optional Discord forum mirror for bug reports:
    # - when webhook env var is missing, skip silently (non-blocking);
    # - when configured, create a forum post/thread via thread_name.
    webhook = os.getenv(str(webhook_env_name or "").strip(), "").strip()
    if not webhook:
        return {"sent": False, "reason": "webhook_not_configured"}

    use_summary = str(summary or "").strip() or "Bug report"
    thread_name = f"Bug: {use_summary}"
    if len(thread_name) > 100:
        thread_name = thread_name[:97] + "..."

    details_text = str(details or "").strip() or "(no extra notes)"
    if len(details_text) > 1100:
        details_text = details_text[:1097] + "..."

    issue_link = str(issue_url or "").strip() or "N/A"
    screenshot_link = str(screenshot_url or "").strip() or "N/A"
    screenshot_name = str(screenshot_filename or "").strip() or "N/A"
    screenshot_note_text = str(screenshot_note or "").strip() or "none"
    path_text = str(selected_path or "").strip() or "(none)"
    error_text = str(last_json_error or "").strip() or "none"
    note_text = str(last_highlight_note or "").strip() or "none"
    app_ver = str(app_version or "").strip() or "unknown"
    theme_text = str(theme_variant or "").strip() or "unknown"
    timestamp_text = str(now_text or "").strip() or "unknown"
    py_text = str(python_version or "").strip() or "unknown"
    os_text = str(platform_text or "").strip() or "unknown"
    discord_text = str(discord_contact or "").strip() or "none"
    include_diag_flag = bool(include_diag)
    diag_text = str(diag_tail or "").strip()
    crash_text = str(crash_tail or "").strip()

    def _clip(value: str, limit: int) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."

    runtime_context = "\n".join(
        [
            f"Time: {_clip(timestamp_text, 100)}",
            f"App Version: {app_ver[:100]}",
            f"Theme: {theme_text[:100]}",
            f"Selected Path: {_clip(path_text, 300)}",
            f"Last JSON Error: {_clip(error_text, 300)}",
            f"Last Highlight Note: {_clip(note_text, 300)}",
            f"Python: {_clip(py_text, 100)}",
            f"Platform: {_clip(os_text, 160)}",
            f"Discord: {_clip(discord_text, 100)}",
        ]
    )

    payload = {
        "thread_name": thread_name,
        "embeds": [
            {
                "title": use_summary[:250],
                "description": "",
                "color": 757408,
                "fields": [
                    {"name": "Issue", "value": issue_link[:1024], "inline": False},
                    {"name": "Summary", "value": _clip(use_summary, 1024), "inline": False},
                    {"name": "Reporter Notes", "value": _clip(details_text, 1024), "inline": False},
                    {"name": "Runtime Context", "value": runtime_context[:1024], "inline": False},
                ],
            }
        ],
        "allowed_mentions": {"parse": []},
    }
    if screenshot_link != "N/A":
        payload["embeds"][0]["fields"].append(
            {"name": "Screenshot", "value": f"{screenshot_name[:100]}: {screenshot_link[:900]}", "inline": False}
        )
        # If screenshot upload produced a public URL, surface it as forum thumbnail.
        payload["embeds"][0]["thumbnail"] = {"url": screenshot_link}
    if screenshot_note_text != "none":
        payload["embeds"][0]["fields"].append(
            {"name": "Screenshot Note", "value": screenshot_note_text[:1024], "inline": False}
        )
    attachment_parts: list[dict[str, Any]] = []
    if include_diag_flag and diag_text:
        payload["embeds"][0]["fields"].append(
            {"name": "Diagnostics Tail", "value": "Attached: diagnostics-tail.txt", "inline": False}
        )
        attachment_parts.append(
            {
                "name": "files[0]",
                "filename": "diagnostics-tail.txt",
                "content_type": "text/plain; charset=utf-8",
                "data": diag_text,
            }
        )
    if crash_text:
        payload["embeds"][0]["fields"].append(
            {"name": "Crash Tail", "value": "Attached: crash-tail.txt", "inline": False}
        )
        attachment_parts.append(
            {
                "name": f"files[{len(attachment_parts)}]",
                "filename": "crash-tail.txt",
                "content_type": "text/plain; charset=utf-8",
                "data": crash_text,
            }
        )
    tag_ids = parse_discord_forum_tag_ids(forum_tag_ids_raw)
    if tag_ids:
        payload["applied_tags"] = tag_ids

    headers = {
        "User-Agent": "sins-editor-bug-report-discord-forum",
        "Accept": "application/json",
    }
    if attachment_parts:
        payload_json = json.dumps(payload, ensure_ascii=False)
        parts = [{"name": "payload_json", "data": payload_json}]
        parts.extend(attachment_parts)
        body, content_type = _build_multipart_form_data(
            parts
        )
        headers["Content-Type"] = content_type
    else:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        webhook,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with _resolve_open_https_request()(
            req,
            timeout=30,
            allowed_hosts=(
                "discord.com",
                "discordapp.com",
                "ptb.discord.com",
                "canary.discord.com",
            ),
        ) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = {}
            try:
                parsed = json.loads(raw) if raw else {}
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                parsed = {}
            return {
                "sent": True,
                "status": int(getattr(resp, "status", 0) or 0),
                "thread_id": str(parsed.get("id", "")).strip() if isinstance(parsed, dict) else "",
            }
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            detail = str(exc)
        raise AppRuntimeError(f"Discord forum webhook error ({exc.code}): {detail}") from exc
    except EXPECTED_ERRORS as exc:
        raise AppRuntimeError(f"Failed to send Discord forum bug report: {exc}") from exc


# --- Merged from bug_report_cooldown_service.py ---
"""Bug-report submit cooldown helper logic."""

import math
from typing import Any


def submit_cooldown_remaining(last_submit_monotonic: Any, cooldown_seconds: Any, now_monotonic: Any) -> Any:
    """Return non-negative seconds remaining before next submit is allowed."""
    cooldown = int(cooldown_seconds or 0)
    if cooldown <= 0:
        return 0
    last_submit = float(last_submit_monotonic or 0.0)
    if last_submit <= 0:
        return 0
    now_val = float(now_monotonic)
    remaining = (last_submit + float(cooldown)) - now_val
    if remaining <= 0:
        return 0
    return int(math.ceil(remaining))


def mark_submit_now(now_monotonic: Any) -> Any:
    """Return normalized submit timestamp for owner state storage."""
    return float(now_monotonic)


# --- Merged from bug_report_service.py ---
import io
import math
import os
import random
import re
from datetime import datetime, timezone
from typing import Any
from core.exceptions import EXPECTED_ERRORS
from core.exceptions import AppRuntimeError
import logging
_LOG = logging.getLogger(__name__)


def build_bug_report_markdown(
    *,
    summary: Any,
    details: Any,
    now_text: Any,
    app_version: Any,
    theme_variant: Any,
    selected_path: Any,
    last_json_error: Any,
    last_highlight_note: Any,
    python_version: Any,
    platform_text: Any,
    include_diag: Any=True,
    diag_tail: Any="",
    crash_tail: Any="",
    discord_contact: Any="",
    screenshot_url: Any="",
    screenshot_filename: Any="",
    screenshot_note: Any="",
) -> Any:
    # Assemble the final issue body used by API submission and browser fallback.
    crash_tail = str(crash_tail or "").strip()
    discord_contact = str(discord_contact or "").strip()
    parts = [
        "## In-App Bug Report",
        "",
        "### Summary",
        str(summary or "").strip(),
        "",
        "### Reporter Notes",
        str(details or "").strip() or "(no extra notes)",
        "",
        "### Runtime Context",
        f"- Time: {now_text}",
        f"- App Version: {app_version}",
        f"- Theme: {theme_variant}",
        f"- Selected Path: {selected_path}",
        f"- Last JSON Error: {last_json_error or 'none'}",
        f"- Last Highlight Note: {last_highlight_note or 'none'}",
        f"- Python: {python_version}",
        f"- Platform: {platform_text}",
    ]
    if discord_contact:
        parts.append(f"- Discord: {discord_contact}")
    if include_diag:
        parts.extend(
            [
                "",
                "### Diagnostics Tail",
                "```text",
                str(diag_tail or "").strip() or "(diagnostics log is empty)",
                "```",
            ]
        )
    if crash_tail:
        parts.extend(
            [
                "",
                "### Crash Log Tail",
                "```text",
                crash_tail,
                "```",
            ]
        )
    if screenshot_url:
        parts.extend(
            [
                "",
                "### Screenshot",
                f"![{(screenshot_filename or 'bug-screenshot').strip()}]({screenshot_url})",
                "",
                f"Direct link: {screenshot_url}",
            ]
        )
    elif screenshot_filename:
        parts.extend(
            [
                "",
                "### Screenshot",
                (
                    f"Selected file: `{screenshot_filename}` "
                    "(attach manually in browser issue form if needed)."
                ),
            ]
        )
    if screenshot_note:
        parts.extend(
            [
                "",
                "### Screenshot Upload Note",
                str(screenshot_note).strip(),
            ]
        )
    return "\n".join(parts).strip()


def sanitize_bug_screenshot_slug(value: Any) -> Any:
    # Keep screenshot path segments filesystem/URL safe.
    text = str(value or "").strip().lower()
    if not text:
        return "screenshot"
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "screenshot"
    return text[:40]


def build_bug_screenshot_repo_path(source_filename: Any, summary: Any="", uploads_dir: Any="bug-uploads") -> Any:
    # Build a collision-resistant repo path under bug-uploads/YYYY/MM/.
    base_name = os.path.basename(str(source_filename or "").strip())
    stem, ext = os.path.splitext(base_name)
    ext = str(ext or "").lower()
    if not ext:
        ext = ".png"
    slug_source = stem if stem else summary
    slug = sanitize_bug_screenshot_slug(slug_source)
    now_utc = datetime.now(timezone.utc)
    ts = now_utc.strftime("%Y%m%dT%H%M%SZ")
    short_id = f"{random.getrandbits(24):06x}"
    year = now_utc.strftime("%Y")
    month = now_utc.strftime("%m")
    use_uploads_dir = str(uploads_dir or "bug-uploads").strip("/")
    return f"{use_uploads_dir}/{year}/{month}/{ts}_{short_id}_{slug}{ext}"


def detect_bug_screenshot_magic_ext(source_path: Any) -> Any:
    # Validate file signature instead of trusting extension alone.
    try:
        with open(source_path, "rb") as fh:
            header = fh.read(16)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return ""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ".webp"
    return ""


def validate_bug_screenshot_dimensions(source_path: Any, max_dimension: Any=4096) -> Any:
    max_dim = int(max_dimension or 0)
    if max_dim <= 0:
        return
    try:
        from PIL import Image

        with Image.open(source_path) as img:
            width = int(img.width or 0)
            height = int(img.height or 0)
    except EXPECTED_ERRORS as exc:
        raise AppRuntimeError("Unable to inspect screenshot dimensions.") from exc
    if width <= 0 or height <= 0:
        raise AppRuntimeError("Selected screenshot has invalid image dimensions.")
    if width > max_dim or height > max_dim:
        raise AppRuntimeError(
            f"Screenshot dimensions exceed limit ({max_dim}px max width/height)."
        )


def validate_bug_screenshot_file(
    path: Any,
    *,
    allowed_extensions: Any=(".png", ".jpg", ".jpeg", ".webp"),
    max_bytes: Any=5 * 1024 * 1024,
    max_dimension: Any=4096,
) -> Any:
    # Enforce extension/signature/size/dimension guardrails before upload prep.
    src = str(path or "").strip()
    if not src:
        return ""
    if not os.path.isfile(src):
        raise AppRuntimeError("Selected screenshot file does not exist.")
    ext = os.path.splitext(src)[1].lower()
    allowed = {str(item).lower() for item in allowed_extensions}
    if ext not in allowed:
        raise AppRuntimeError(
            "Unsupported screenshot format. Allowed: " + ", ".join(sorted(allowed))
        )
    detected_ext = detect_bug_screenshot_magic_ext(src)
    if not detected_ext:
        raise AppRuntimeError("Selected file is not a valid supported image.")
    jpeg_exts = {".jpg", ".jpeg"}
    ext_matches = (ext == detected_ext) or ({ext, detected_ext} <= jpeg_exts)
    if not ext_matches:
        raise AppRuntimeError("Screenshot extension does not match actual file format.")
    use_max_bytes = int(max_bytes or 0)
    size_bytes = int(os.path.getsize(src))
    if use_max_bytes > 0 and size_bytes > use_max_bytes:
        raise AppRuntimeError(
            f"Screenshot exceeds size limit ({use_max_bytes // (1024 * 1024)} MB max)."
        )
    validate_bug_screenshot_dimensions(src, max_dimension=max_dimension)
    return src


def prepare_bug_screenshot_upload_bytes(source_path: Any, detected_ext: Any, max_bytes: Any=5 * 1024 * 1024) -> Any:
    # Re-encode image to strip metadata and normalize upload payload.
    from PIL import Image

    save_ext = str(detected_ext or "").lower()
    format_map = {
        ".png": ("PNG", "image/png"),
        ".jpg": ("JPEG", "image/jpeg"),
        ".jpeg": ("JPEG", "image/jpeg"),
        ".webp": ("WEBP", "image/webp"),
    }
    save_format, mime_type = format_map.get(save_ext, ("PNG", "image/png"))
    with Image.open(source_path) as img:
        working = img
        if save_format == "JPEG" and img.mode not in ("RGB", "L"):
            working = img.convert("RGB")
        out = io.BytesIO()
        save_kwargs = {}
        if save_format == "JPEG":
            save_kwargs["quality"] = 92
            save_kwargs["optimize"] = True
        if save_format == "WEBP":
            save_kwargs["quality"] = 90
            save_kwargs["method"] = 6
        working.save(out, format=save_format, **save_kwargs)
        raw_bytes = out.getvalue()
    use_max_bytes = int(max_bytes or 0)
    if use_max_bytes > 0 and len(raw_bytes) > use_max_bytes:
        raise AppRuntimeError(
            f"Processed screenshot exceeds size limit ({use_max_bytes // (1024 * 1024)} MB max)."
        )
    return raw_bytes, mime_type


def build_bug_report_new_issue_url(owner: Any, repo: Any, labels: Any, title: Any, body_markdown: Any, include_body: Any=True) -> Any:
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise AppRuntimeError("Bug report repo is not configured.")
    labels_csv = ",".join(str(label).strip() for label in labels if str(label).strip())
    from urllib import parse

    payload = {
        "title": str(title or "").strip(),
        "labels": labels_csv,
    }
    # Browser fallback privacy mode can omit body= so diagnostics/crash text is not placed in URL query.
    if include_body:
        payload["body"] = str(body_markdown or "").strip()
    query = parse.urlencode(payload)
    return f"https://github.com/{use_owner}/{use_repo}/issues/new?{query}"


def bug_report_submit_cooldown_remaining(last_submit_monotonic: Any, cooldown_seconds: Any, now_monotonic: Any) -> Any:
    # Returns seconds remaining before another submit is allowed.
    cooldown = int(cooldown_seconds or 0)
    if cooldown <= 0:
        return 0
    last_submit = float(last_submit_monotonic or 0.0)
    if last_submit <= 0:
        return 0
    now_val = float(now_monotonic)
    remaining = (last_submit + float(cooldown)) - now_val
    if remaining <= 0:
        return 0
    return int(math.ceil(remaining))


# --- Merged from bug_report_ui_service.py ---
"""Bug report dialog UI service.

Keeps the large Tk dialog builder out of `sins_editor.py` while preserving
runtime behavior through owner callbacks.
"""

import os
import threading
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


# UI-only extraction: owner provides methods/state; this module stays stateless.
def open_bug_report_dialog(
    owner: Any,
    tk: Any,
    filedialog: Any,
    messagebox: Any,
    summary_prefill: Any="",
    details_prefill: Any="",
    include_diag_default: Any=True,
    crash_tail: Any="",
    threading_module: Any=threading,
    validate_bug_screenshot_file_fn: Any=None,
    submit_cooldown_remaining_fn: Any=None,
    mark_submit_now_fn: Any=None,
    has_bug_report_token_fn: Any=None,
    upload_bug_screenshot_fn: Any=None,
    build_bug_report_markdown_fn: Any=None,
    build_bug_report_issue_url_fn: Any=None,
    submit_bug_report_discord_forum_fn: Any=None,
) -> Any:
    existing = getattr(owner, "_bug_report_dialog", None)
    if existing is not None:
        try:
            if existing.winfo_exists():
                existing.deiconify()
                existing.lift()
                existing.focus_force()
                return
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    chip_colors = owner._bug_chip_palette(variant)

    dlg = tk.Toplevel(owner.root)
    try:
        dlg.withdraw()
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass
    owner._bug_report_dialog = dlg
    dlg.title("Submit Bug Report")
    use_custom_chrome = bool(getattr(owner, "BUG_REPORT_USE_CUSTOM_CHROME", True))
    if not use_custom_chrome:
        dlg.transient(owner.root)
    dlg.configure(bg=theme.get("panel", "#161b24"))
    owner._apply_centered_toplevel_geometry(
        dlg,
        width_px=684,
        height_px=576,
        anchor_window=owner.root,
        min_width=612,
        min_height=504,
    )

    card = tk.Frame(
        dlg,
        bg=theme.get("panel", "#161b24"),
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
    )
    card.pack(fill="both", expand=True, padx=0, pady=0)
    owner._bug_report_card_frame = card

    header_bg = theme.get("title_bar_bg", chip_colors["bg"])
    header_fg = theme.get("title_bar_fg", theme.get("fg", "#e6e6e6"))
    header_border = theme.get("title_bar_border", chip_colors["border"])
    header = tk.Frame(
        card,
        bg=header_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=header_border,
        highlightcolor=header_border,
    )
    header.pack(fill="x", padx=12, pady=(10, 8))
    header_icon_photo = owner._load_bug_report_chip_icon(max_size=18, tint=header_fg)
    owner._bug_report_header_icon_photo = header_icon_photo
    icon = tk.Label(
        header,
        text="",
        image=header_icon_photo if header_icon_photo is not None else "",
        bg=header_bg,
        fg=header_fg,
        bd=0,
        highlightthickness=0,
    )
    icon.pack(side="left", padx=(8, 7), pady=4)
    title = tk.Label(
        header,
        text="SUBMIT BUG REPORT",
        bg=header_bg,
        fg=header_fg,
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="w",
    )
    title.pack(side="left", pady=2)
    close_badge = tk.Label(
        header,
        text="X",
        bg=header_bg,
        fg=header_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        cursor="hand2",
        padx=10,
        pady=4,
    )
    close_badge.pack(side="right")
    owner._bug_report_header_frame = header
    owner._bug_report_header_icon = icon
    owner._bug_report_header_title = title
    owner._bug_report_close_badge = close_badge

    form_intro = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    form_intro.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(
        form_intro,
        text="DISCORD (OPTIONAL)",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    discord_var = tk.StringVar(value="")
    discord_entry = tk.Entry(
        form_intro,
        textvariable=discord_var,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    discord_entry.pack(fill="x", pady=(4, 0), ipady=5)

    screenshot_var = tk.StringVar(value="")
    screenshot_block = tk.Frame(form_intro, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    screenshot_block.pack(fill="x", pady=(8, 0))
    tk.Label(
        screenshot_block,
        text="SCREENSHOT (OPTIONAL)",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    screenshot_row = tk.Frame(screenshot_block, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    screenshot_row.pack(fill="x", pady=(4, 0))
    screenshot_entry = tk.Entry(
        screenshot_row,
        textvariable=screenshot_var,
        state="readonly",
        readonlybackground=theme.get("bg", "#0f131a"),
        fg=theme.get("credit_label_fg", "#b5cade"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 9),
    )
    screenshot_entry.pack(side="left", fill="x", expand=True, ipady=5)

    def _pick_screenshot_file():
        file_path = filedialog.askopenfilename(
            title="Select Screenshot",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg;*.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg;*.jpeg"),
                ("WebP", "*.webp"),
            ],
        )
        if not file_path:
            return
        try:
            validate_fn = validate_bug_screenshot_file_fn or owner._validate_bug_screenshot_file
            validated = validate_fn(file_path)
        except EXPECTED_ERRORS as exc:
            messagebox.showwarning("Bug Report", str(exc))
            return
        screenshot_var.set(validated)

    def _clear_screenshot_file():
        screenshot_var.set("")

    pick_wrap = tk.Frame(
        screenshot_row,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    pick_wrap.pack(side="left", padx=(6, 0))
    pick_btn = tk.Button(
        pick_wrap,
        text="Browse",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 9, "bold"),
        padx=10,
        pady=4,
        command=_pick_screenshot_file,
    )
    pick_btn.pack(side="left", padx=1, pady=1)
    clear_wrap = tk.Frame(
        screenshot_row,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    clear_wrap.pack(side="left", padx=(6, 0))
    clear_btn = tk.Button(
        clear_wrap,
        text="Clear",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 9, "bold"),
        padx=10,
        pady=4,
        command=_clear_screenshot_file,
    )
    clear_btn.pack(side="left", padx=1, pady=1)

    form = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    form.pack(fill="both", expand=True, padx=12, pady=(2, 8))

    tk.Label(
        form,
        text="Title",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    summary_var = tk.StringVar(value=str(summary_prefill or ""))
    summary_entry = tk.Entry(
        form,
        textvariable=summary_var,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    summary_entry.pack(fill="x", pady=(4, 10), ipady=5)

    tk.Label(
        form,
        text="Details",
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 10, "bold"),
        anchor="w",
    ).pack(fill="x")
    details_text = tk.Text(
        form,
        wrap="word",
        height=9,
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        insertbackground=theme.get("fg", "#e6e6e6"),
        selectbackground=theme.get("select_bg", "#2f3a4d"),
        selectforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
        font=(owner._preferred_mono_family(), 10),
    )
    details_text.pack(fill="both", expand=True, pady=(4, 8))
    if str(details_prefill or "").strip():
        try:
            details_text.insert("1.0", str(details_prefill))
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass

    include_diag_var = tk.BooleanVar(value=bool(include_diag_default))
    diag_block = tk.Frame(form, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    diag_block.pack(fill="x", pady=(0, 0))

    include_diag = tk.Checkbutton(
        diag_block,
        text="Include diagnostics tail from local app log",
        variable=include_diag_var,
        onvalue=True,
        offvalue=False,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("panel", "#161b24"),
        activeforeground=theme.get("fg", "#e6e6e6"),
        selectcolor=theme.get("panel", "#161b24"),
        highlightthickness=0,
        bd=0,
        font=(owner._preferred_mono_family(), 9),
        anchor="w",
    )
    include_diag.pack(fill="x")
    tk.Label(
        diag_block,
        text=(
            "Privacy Notice: Submitted reports may include your notes, runtime context,\n"
            "optional diagnostics/crash logs, and optional Discord contact info."
        ),
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("credit_label_fg", "#8ca6bb"),
        font=(owner._preferred_mono_family(), 10),
        justify="left",
        anchor="w",
    ).pack(fill="x", padx=(0, 0), pady=(2, 0))

    status_var = tk.StringVar(value="")
    status_label = tk.Label(
        form,
        textvariable=status_var,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("credit_label_fg", "#b5cade"),
        font=(owner._preferred_mono_family(), 9),
        anchor="w",
    )
    status_label.pack(fill="x", pady=(8, 0))

    controls = tk.Frame(card, bg=theme.get("panel", "#161b24"), bd=0, highlightthickness=0)
    controls.pack(fill="x", padx=12, pady=(0, 12))

    submit_wrap = tk.Frame(
        controls,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    submit_wrap.pack(side="right")
    submit_btn = tk.Button(
        submit_wrap,
        text="Submit Report",
        bg=chip_colors["bg"],
        fg=chip_colors["fg"],
        activebackground=chip_colors["active_bg"],
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
        padx=14,
        pady=5,
    )
    submit_btn.pack(side="right", padx=1, pady=1)

    cancel_wrap = tk.Frame(
        controls,
        bg=chip_colors["border"],
        bd=0,
        highlightthickness=0,
    )
    cancel_wrap.pack(side="right", padx=(0, 8))
    cancel_btn = tk.Button(
        cancel_wrap,
        text="Cancel",
        bg=theme.get("bg", "#0f131a"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
        padx=14,
        pady=5,
        command=owner._close_bug_report_dialog,
    )
    cancel_btn.pack(side="right", padx=1, pady=1)

    def submit_action() -> Any:
        cooldown_fn = submit_cooldown_remaining_fn or owner._bug_report_submit_cooldown_remaining
        cooldown_remaining = int(cooldown_fn() or 0)
        if cooldown_remaining > 0:
            unit = "second" if cooldown_remaining == 1 else "seconds"
            wait_msg = f"Please wait {cooldown_remaining} {unit} before sending another report."
            owner._set_status(wait_msg)
            status_var.set(wait_msg)
            messagebox.showwarning("Bug Report", wait_msg)
            return
        summary = summary_var.get().strip()
        details = details_text.get("1.0", "end-1c").strip()
        if not summary:
            messagebox.showwarning("Bug Report", "Enter a title before submitting.")
            return
        screenshot_path = screenshot_var.get().strip()
        screenshot_file_name = os.path.basename(screenshot_path) if screenshot_path else ""
        issue_title = f"[Bug] {summary}"[:120]
        mark_submit_fn = mark_submit_now_fn or owner._mark_bug_report_submit_now
        mark_submit_fn()

        def worker() -> Any:
            try:
                owner._ui_call(status_var.set, "Submitting issue...", wait=False)
                owner._ui_call(submit_btn.configure, state="disabled", wait=False)
                screenshot_url = ""
                screenshot_note = ""
                selected_name = screenshot_file_name
                if screenshot_path:
                    try:
                        validate_fn = validate_bug_screenshot_file_fn or owner._validate_bug_screenshot_file
                        validate_fn(screenshot_path)
                        has_token_fn = has_bug_report_token_fn or owner._has_bug_report_token
                        if has_token_fn():
                            owner._ui_call(status_var.set, "Uploading screenshot...", wait=False)
                            upload_fn = upload_bug_screenshot_fn or owner._upload_bug_screenshot
                            uploaded = upload_fn(screenshot_path, summary=summary)
                            screenshot_url = str(uploaded.get("download_url", "")).strip()
                            selected_name = str(uploaded.get("filename", "")).strip() or selected_name
                        else:
                            screenshot_note = (
                                "Screenshot selected locally, but token is unavailable. "
                                "Attach image manually in browser issue form."
                            )
                    except EXPECTED_ERRORS as upload_exc:
                        screenshot_note = str(upload_exc)
                build_markdown_fn = build_bug_report_markdown_fn or owner._build_bug_report_markdown
                body = build_markdown_fn(
                    summary=summary,
                    details=details,
                    include_diag=bool(include_diag_var.get()),
                    discord_contact=(
                        discord_var.get().strip()
                    ),
                    crash_tail=str(crash_tail or ""),
                    screenshot_url=screenshot_url,
                    screenshot_filename=selected_name,
                    screenshot_note=screenshot_note,
                )
                owner._ui_call(status_var.set, "Submitting report...", wait=False)
                # Discord-only bug report policy:
                # build a clean GitHub issue-form URL for reference, but do not create GitHub issues from app submits.
                build_issue_url_fn = build_bug_report_issue_url_fn or owner._bug_report_new_issue_url
                issue_url = build_issue_url_fn(
                    issue_title,
                    body,
                    include_body=False,
                )
                discord_mirror_note = ""
                try:
                    submit_discord_forum_fn = submit_bug_report_discord_forum_fn or owner._submit_bug_report_discord_forum
                    mirror_result = submit_discord_forum_fn(
                        summary=summary,
                        details=details,
                        issue_url=issue_url,
                        include_diag=bool(include_diag_var.get()),
                        diag_tail=(
                            owner._read_diag_log_tail(max_chars=12000)
                            if bool(include_diag_var.get())
                            else ""
                        ),
                        crash_tail=str(crash_tail or ""),
                        discord_contact=discord_var.get().strip(),
                        screenshot_url=screenshot_url,
                        screenshot_filename=selected_name,
                        screenshot_note=screenshot_note,
                    )
                    if isinstance(mirror_result, dict):
                        if mirror_result.get("sent"):
                            discord_mirror_note = " Discord forum mirror sent."
                        elif mirror_result.get("reason") == "webhook_not_configured":
                            discord_mirror_note = " Discord forum mirror skipped (webhook not configured)."
                except EXPECTED_ERRORS as exc:
                    _LOG.debug('expected_error', exc_info=exc)
                    # Discord forum mirror is optional and must not block bug submissions.
                    discord_mirror_note = " Discord forum mirror failed."
                owner._set_status(f"Bug report submitted.{discord_mirror_note}")
                owner._ui_call(status_var.set, f"Submitted successfully.{discord_mirror_note}", wait=False)
                # Release modal grab and close dialog first.
                owner._ui_call(owner._close_bug_report_dialog, wait=True)
                owner._ui_call(
                    owner._show_bug_submit_splash,
                    "BUG REPORT SUBMITTED",
                    wait=False,
                )
            except EXPECTED_ERRORS as exc:
                owner._set_status("")
                owner._ui_call(status_var.set, "Submit failed.", wait=False)
                owner._ui_call(messagebox.showerror, "Bug Report", str(exc), wait=False)
            finally:
                owner._ui_call(submit_btn.configure, state="normal", wait=False)

        threading_module.Thread(target=worker, daemon=True).start()

    submit_btn.configure(command=submit_action)
    if use_custom_chrome:
        chrome_ok = owner._activate_bug_report_custom_chrome(
            dlg,
            header=header,
            drag_widgets=(header, icon, title),
            close_widget=close_badge,
        )
        if not chrome_ok:
            owner._set_window_icon_for(dlg)
            owner._apply_windows_titlebar_theme(dlg)
            try:
                close_badge.pack_forget()
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
    else:
        owner._set_window_icon_for(dlg)
        owner._apply_windows_titlebar_theme(dlg)
        try:
            close_badge.pack_forget()
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    try:
        dlg.deiconify()
        dlg.lift()
        dlg.focus_force()
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        pass
    owner._arm_bug_report_follow_root(dlg)
    dlg.bind("<Escape>", lambda _e: owner._close_bug_report_dialog())
    dlg.protocol("WM_DELETE_WINDOW", owner._close_bug_report_dialog)
    summary_entry.focus_set()
    owner._start_bug_report_header_pulse()

    def clear_ref(_evt: Any=None) -> Any:
        owner._stop_bug_report_header_pulse()
        owner._bug_report_card_frame = None
        owner._bug_report_header_frame = None
        owner._bug_report_header_icon = None
        owner._bug_report_header_icon_photo = None
        owner._bug_report_header_title = None
        owner._bug_report_close_badge = None
        owner._bug_report_dialog = None
        owner._bug_report_follow_root = False
        owner._bug_report_is_dragging = False

    dlg.bind("<Destroy>", clear_ref, add="+")


# --- Merged from crash_logging_service.py ---
"""Crash logging and user-notice helpers."""

from datetime import datetime
import os
import platform
import threading
import traceback
from typing import Any


_MAX_FIELD_NAME_LEN = 48
_MAX_FIELD_VALUE_LEN = 256
_MAX_EXCEPTION_CHAIN_DEPTH = 3


def _safe_field_name(name: Any) -> str:
    raw = str(name or "").strip().lower()
    if not raw:
        return "unknown"
    kept = []
    for ch in raw:
        if ch.isalnum() or ch in ("_", "-", "."):
            kept.append(ch)
    token = "".join(kept).strip("._-")
    if not token:
        token = "unknown"
    return token[:_MAX_FIELD_NAME_LEN]


def _safe_field_value(value: Any) -> str:
    # Keep crash meta one-line and short to avoid leaking raw user payloads.
    cleaned = str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
    if len(cleaned) > _MAX_FIELD_VALUE_LEN:
        return f"{cleaned[:_MAX_FIELD_VALUE_LEN]}..."
    return cleaned


def _safe_field(name: Any, value: Any) -> str:
    key = _safe_field_name(name)
    cleaned = _safe_field_value(value)
    return f"{key}={cleaned}\n"


def _exception_chain_summary(exc_value: Any, max_depth: int=_MAX_EXCEPTION_CHAIN_DEPTH) -> str:
    chain = []
    current = exc_value
    seen_ids = set()
    depth = 0
    while current is not None and depth < max(1, int(max_depth)):
        ident = id(current)
        if ident in seen_ids:
            break
        seen_ids.add(ident)
        etype = type(current).__name__
        msg = _safe_field_value(current)
        chain.append(f"{etype}:{msg}" if msg else etype)
        next_exc = getattr(current, "__cause__", None)
        if next_exc is None:
            next_exc = getattr(current, "__context__", None)
        current = next_exc
        depth += 1
    return " <= ".join(chain)


def append_crash_log(
    path: Any,
    trim_text_file_for_append: Any,
    max_bytes: Any,
    keep_bytes: Any,
    app_version: Any,
    context: Any,
    exc_type: Any,
    exc_value: Any,
    exc_tb: Any,
    expected_errors: Any,
    extra_fields: Any=None,
) -> Any:
    """Append structured crash context and traceback details to crash log."""
    try:
        trim_text_file_for_append(path, max_bytes, keep_bytes)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"\n---\n"
            f"time={stamp}\n"
            f"context={context}\n"
            f"version={app_version}\n"
        )
        fields = {
            "pid": os.getpid(),
            "thread_name": threading.current_thread().name,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "exception_type": getattr(exc_type, "__name__", type(exc_value).__name__),
            "exception_message": str(exc_value or ""),
            "exception_chain": _exception_chain_summary(exc_value),
        }
        if isinstance(extra_fields, dict):
            for key, value in extra_fields.items():
                fields[str(key)] = value
        meta = "".join(_safe_field(name, value) for name, value in fields.items())
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(header)
            fh.write(meta)
            fh.write(detail.rstrip())
            fh.write("\n")
    except expected_errors:
        return


def show_crash_notice_once(crash_notice_shown: Any, crash_path: Any, ui_call: Any, showerror_func: Any) -> Any:
    """Show one-time crash-log notice and return updated shown flag."""
    if crash_notice_shown:
        return True
    msg = (
        "An unexpected error occurred.\n"
        "A crash log was written to:\n"
        f"{crash_path}"
    )
    ui_call(showerror_func, "Unexpected Error", msg, wait=False)
    return True


# --- Merged from crash_offer_service.py ---
"""Crash report offer scheduling and prompt helpers."""
import os
from typing import Any

_process_crash_offer_prompted = False


def schedule_crash_report_offer(root: Any, existing_after_id: Any, delay_ms: Any, callback: Any, expected_errors: Any) -> Any:
    """Schedule crash report offer callback and return new after-id or None."""
    if root is None:
        return None
    if existing_after_id:
        try:
            root.after_cancel(existing_after_id)
        except expected_errors:
            pass
    try:
        return root.after(max(1, int(delay_ms)), callback)
    except expected_errors:
        return None


def offer_crash_report_if_available(
    payload: Any,
    ui_call: Any,
    askyesno_func: Any,
    write_crash_prompt_state: Any,
    open_bug_report_dialog: Any,
) -> Any:
    """Prompt for crash report and open prefilled bug dialog on acceptance."""
    if not payload:
        return
    crash_hash = payload["hash"]
    crash_tail = payload["tail"]
    prompt = (
        "A crash from the previous session was detected.\n\n"
        "Would you like to open the bug report form with the crash log attached?\n"
        "No report is sent unless you submit manually."
    )
    wants_report = bool(
        ui_call(
            askyesno_func,
            "Crash Detected",
            prompt,
            wait=True,
            default=False,
        )
    )
    write_crash_prompt_state(crash_hash)
    if not wants_report:
        return
    open_bug_report_dialog(
        summary_prefill="Crash on previous session",
        details_prefill=(
            "The app crashed in my previous session.\n"
            "Please review the attached crash log tail.\n\n"
            "What I was doing before crash:\n"
        ),
        include_diag_default=True,
        crash_tail=crash_tail,
    )


def should_offer_crash_report_for_process(env: Any = None) -> bool:
    """Return True only when crash-report prompt is allowed for this process."""
    source = env if env is not None else os.environ
    raw = str(source.get("HACKHUB_DISABLE_CRASH_REPORT_PROMPT", "")).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return False
    return not bool(_process_crash_offer_prompted)


def mark_crash_report_prompted_for_process() -> None:
    """Mark startup crash-report prompt as shown for this process."""
    global _process_crash_offer_prompted
    _process_crash_offer_prompted = True


def reset_crash_report_prompt_guard_for_tests() -> None:
    """Test helper: reset per-process crash-report prompt guard."""
    global _process_crash_offer_prompted
    _process_crash_offer_prompted = False


# --- Merged from crash_report_service.py ---
"""Crash-report state and payload helpers."""

import hashlib
import json
import os
from datetime import datetime
from typing import Any


def _normalized_limit(default_limit: Any, max_chars: Any) -> int:
    if max_chars is None:
        return int(default_limit)
    return max(0, int(max_chars))


def _is_non_actionable_crash_tail(crash_tail: str) -> bool:
    """Ignore manual-interrupt entries so startup prompts only target real crashes."""
    lowered = crash_tail.casefold()
    return "exception_type=keyboardinterrupt" in lowered


def build_crash_log_path(runtime_dir: Any, crash_log_filename: Any) -> Any:
    """Build crash log path under runtime data directory."""
    return os.path.join(runtime_dir, crash_log_filename)


def build_crash_state_path(runtime_dir: Any, crash_state_filename: Any) -> Any:
    """Build crash state path under runtime data directory."""
    return os.path.join(runtime_dir, crash_state_filename)


def read_crash_log_tail(path: Any, default_limit: Any, max_chars: Any, read_text_file_tail: Any) -> Any:
    """Read trailing crash log text using the configured default cap."""
    limit = _normalized_limit(default_limit, max_chars)
    return read_text_file_tail(path, limit)


def read_latest_crash_block(
    read_crash_log_tail_func: Any,
    default_limit: Any,
    max_chars: Any,
    read_latest_block: Any,
    marker: Any="\n---\n",
) -> Any:
    """Read and trim the most recent crash entry block from the log tail."""
    text = read_crash_log_tail_func(max_chars=0)
    limit = _normalized_limit(default_limit, max_chars)
    return read_latest_block(text, max_chars=limit, marker=marker)


def read_crash_prompt_state(path: Any, expected_errors: Any) -> Any:
    """Load persisted crash prompt state dictionary when available."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            parsed = json.load(fh)
        if isinstance(parsed, dict):
            return parsed
    except expected_errors:
        pass
    return {}


def write_crash_prompt_state(path: Any, crash_hash: Any, write_text_file_atomic: Any, expected_errors: Any) -> Any:
    """Persist crash prompt state hash and update timestamp."""
    payload = json.dumps(
        {
            "last_seen_hash": str(crash_hash or ""),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        write_text_file_atomic(path, payload, encoding="utf-8")
    except expected_errors:
        return


def pending_crash_report_payload(
    log_path: Any,
    read_latest_crash_block_func: Any,
    read_crash_prompt_state_func: Any,
    expected_errors: Any,
) -> Any:
    """Build pending crash report payload unless already acknowledged."""
    if not os.path.isfile(log_path):
        return None
    try:
        if os.path.getsize(log_path) <= 0:
            return None
    except expected_errors:
        return None
    crash_tail = read_latest_crash_block_func()
    crash_tail_text = str(crash_tail or "")
    if not crash_tail_text.strip():
        return None
    if _is_non_actionable_crash_tail(crash_tail_text):
        return None
    crash_hash = hashlib.sha256(crash_tail_text.encode("utf-8", errors="replace")).hexdigest().lower()
    state = read_crash_prompt_state_func()
    if str(state.get("last_seen_hash", "")).strip().lower() == crash_hash:
        return None
    return {"hash": crash_hash, "tail": crash_tail_text}


# --- Compatibility dispatch for former split telemetry modules ---
_bug_report_markdown_builder = build_bug_report_markdown
_bug_report_open_browser_api = open_bug_report_in_browser
_bug_report_upload_api = upload_bug_screenshot
_bug_report_submit_discord_api = submit_bug_report_discord_forum


def build_bug_report_markdown(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API for bug_report_service and bug_report_context_service."""
    if "bug_report_builder" in kwargs:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        include_diag = kwargs.get("include_diag")
        diag_tail = kwargs["read_diag_log_tail"]() if include_diag else ""
        builder = kwargs["bug_report_builder"]
        return builder(
            summary=kwargs.get("summary"),
            details=kwargs.get("details"),
            now_text=now,
            app_version=kwargs.get("app_version"),
            theme_variant=kwargs.get("theme_variant"),
            selected_path=kwargs.get("selected_path"),
            last_json_error=kwargs.get("last_json_error"),
            last_highlight_note=kwargs.get("last_highlight_note"),
            python_version=kwargs.get("python_version"),
            platform_text=kwargs.get("platform_text"),
            include_diag=include_diag,
            diag_tail=diag_tail,
            crash_tail=kwargs.get("crash_tail"),
            discord_contact=kwargs.get("discord_contact"),
            screenshot_url=kwargs.get("screenshot_url"),
            screenshot_filename=kwargs.get("screenshot_filename"),
            screenshot_note=kwargs.get("screenshot_note"),
        )

    return _bug_report_markdown_builder(*args, **kwargs)


def open_bug_report_in_browser(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API for bug_report_api_service and bug_report_browser_service."""
    if "copy_to_clipboard_fn" in kwargs or len(args) >= 4:
        title = kwargs.get("title", args[0] if len(args) > 0 else "")
        body_markdown = kwargs.get("body_markdown", args[1] if len(args) > 1 else "")
        copy_to_clipboard_fn = kwargs.get("copy_to_clipboard_fn", args[2] if len(args) > 2 else None)
        build_issue_url_fn = kwargs.get("build_issue_url_fn", args[3] if len(args) > 3 else None)
        open_bug_report_browser_fn = kwargs.get("open_bug_report_browser_fn", args[4] if len(args) > 4 else None)
        open_new_tab_fn = kwargs.get("open_new_tab_fn", args[5] if len(args) > 5 else None)

        copy_to_clipboard_fn(body_markdown)
        issue_url = build_issue_url_fn(title, body_markdown, include_body=False)
        return open_bug_report_browser_fn(issue_url=issue_url, open_new_tab_fn=open_new_tab_fn)

    return _bug_report_open_browser_api(*args, **kwargs)


def upload_bug_screenshot(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API for bug_report_api_service and bug_report_submission_service."""
    if "bug_report_api_service" in kwargs:
        api_service = kwargs["bug_report_api_service"]
        return api_service.upload_bug_screenshot(
            source_path=kwargs.get("source_path"),
            summary=kwargs.get("summary"),
            token_env_name=kwargs.get("token_env_name"),
            owner=kwargs.get("owner"),
            repo=kwargs.get("repo"),
            branch=kwargs.get("branch"),
            validate_file_fn=kwargs.get("validate_file_fn"),
            detect_magic_ext_fn=kwargs.get("detect_magic_ext_fn"),
            build_repo_path_fn=lambda source_name, *, summary="": kwargs["build_repo_path_fn"](source_name, str(summary)),
            prepare_upload_bytes_fn=kwargs.get("prepare_upload_bytes_fn"),
        )

    return _bug_report_upload_api(*args, **kwargs)


def submit_bug_report_discord_forum(*args: Any, **kwargs: Any) -> Any:
    """Compatibility API for bug_report_api_service and bug_report_submission_service."""
    if "bug_report_api_service" in kwargs:
        api_service = kwargs["bug_report_api_service"]
        return api_service.submit_bug_report_discord_forum(
            webhook_env_name=kwargs.get("webhook_env_name"),
            summary=kwargs.get("summary"),
            details=kwargs.get("details"),
            issue_url=kwargs.get("issue_url"),
            app_version=kwargs.get("app_version"),
            theme_variant=kwargs.get("theme_variant"),
            selected_path=kwargs.get("selected_path"),
            last_json_error=kwargs.get("last_json_error"),
            last_highlight_note=kwargs.get("last_highlight_note"),
            now_text=kwargs.get("now_text"),
            python_version=kwargs.get("python_version"),
            platform_text=kwargs.get("platform_text"),
            include_diag=kwargs.get("include_diag"),
            diag_tail=kwargs.get("diag_tail"),
            crash_tail=kwargs.get("crash_tail"),
            discord_contact=kwargs.get("discord_contact"),
            screenshot_url=kwargs.get("screenshot_url"),
            screenshot_filename=kwargs.get("screenshot_filename"),
            screenshot_note=kwargs.get("screenshot_note"),
            forum_tag_ids_raw=kwargs.get("forum_tag_ids_raw"),
        )

    return _bug_report_submit_discord_api(*args, **kwargs)
