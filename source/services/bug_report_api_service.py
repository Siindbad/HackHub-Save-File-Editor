import base64
import json
import os
import re
import urllib.error
import urllib.request


def open_bug_report_in_browser(issue_url, open_new_tab_fn):
    if not open_new_tab_fn(issue_url):
        raise RuntimeError("Failed to open browser issue form.")
    return issue_url


def upload_bug_screenshot(
    *,
    source_path,
    summary,
    token_env_name,
    owner,
    repo,
    branch,
    validate_file_fn,
    detect_magic_ext_fn,
    build_repo_path_fn,
    prepare_upload_bytes_fn,
):
    # Required for API upload path: token_env_name should point to a PAT/GitHub token env var.
    token = os.getenv(token_env_name, "").strip()
    if not token:
        raise RuntimeError(f"Missing {token_env_name} token in environment.")

    validated_source = validate_file_fn(source_path)
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise RuntimeError("Bug report repo is not configured.")
    detected_ext = detect_magic_ext_fn(validated_source)
    if not detected_ext:
        raise RuntimeError("Selected file is not a valid supported image.")

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
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            detail = str(exc)
        raise RuntimeError(f"Screenshot upload API error ({exc.code}): {detail}") from exc
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        raise RuntimeError(f"Failed to upload screenshot: {exc}") from exc

    parsed = {}
    try:
        parsed = json.loads(raw) if raw else {}
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
    token_env_name,
    owner,
    repo,
    labels,
    title,
    body_markdown,
    open_browser_fn,
):
    use_owner = str(owner or "").strip()
    use_repo = str(repo or "").strip()
    if not use_owner or not use_repo:
        raise RuntimeError("Bug report repo is not configured.")

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
        with urllib.request.urlopen(req, timeout=35) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            detail = str(exc)
        try:
            return open_browser_fn(title, body_markdown)
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as fallback_exc:
            raise RuntimeError(
                f"GitHub API error ({exc.code}): {detail}. "
                f"Browser fallback failed: {fallback_exc}"
            ) from exc
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        try:
            return open_browser_fn(title, body_markdown)
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as fallback_exc:
            raise RuntimeError(
                f"Failed to submit issue: {exc}. Browser fallback failed: {fallback_exc}"
            ) from exc

    try:
        parsed = json.loads(raw) if raw else {}
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        parsed = {}
    issue_url = str(parsed.get("html_url", "")).strip()
    if not issue_url:
        raise RuntimeError("Issue was created but no issue URL was returned.")
    return issue_url


def parse_discord_forum_tag_ids(raw_tag_ids):
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
    webhook_env_name,
    summary,
    details,
    issue_url,
    app_version,
    theme_variant,
    selected_path,
    last_json_error,
    last_highlight_note,
    screenshot_url="",
    screenshot_filename="",
    screenshot_note="",
    forum_tag_ids_raw="",
):
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

    payload = {
        "thread_name": thread_name,
        "embeds": [
            {
                "title": use_summary[:250],
                "description": details_text,
                "color": 757408,
                "fields": [
                    {"name": "Issue", "value": issue_link[:1024], "inline": False},
                    {"name": "Version", "value": app_ver[:100], "inline": True},
                    {"name": "Theme", "value": theme_text[:100], "inline": True},
                    {"name": "Path", "value": path_text[:1024], "inline": False},
                    {"name": "Last JSON Error", "value": error_text[:1024], "inline": False},
                    {"name": "Last Highlight Note", "value": note_text[:1024], "inline": False},
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

    tag_ids = parse_discord_forum_tag_ids(forum_tag_ids_raw)
    if tag_ids:
        payload["applied_tags"] = tag_ids

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={
            "User-Agent": "sins-editor-bug-report-discord-forum",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = {}
            try:
                parsed = json.loads(raw) if raw else {}
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
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
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            detail = str(exc)
        raise RuntimeError(f"Discord forum webhook error ({exc.code}): {detail}") from exc
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        raise RuntimeError(f"Failed to send Discord forum bug report: {exc}") from exc
