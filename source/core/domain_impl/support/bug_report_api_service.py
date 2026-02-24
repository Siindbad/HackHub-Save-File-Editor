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
        with _open_https_request(req, timeout=45, allowed_hosts=("api.github.com",)) as resp:
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
        with _open_https_request(req, timeout=35, allowed_hosts=("api.github.com",)) as resp:
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
        with _open_https_request(
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
