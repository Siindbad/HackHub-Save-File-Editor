import base64
import json
import os
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
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"Screenshot upload API error ({exc.code}): {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to upload screenshot: {exc}") from exc

    parsed = {}
    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
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
        except Exception:
            detail = str(exc)
        try:
            return open_browser_fn(title, body_markdown)
        except Exception as fallback_exc:
            raise RuntimeError(
                f"GitHub API error ({exc.code}): {detail}. "
                f"Browser fallback failed: {fallback_exc}"
            ) from exc
    except Exception as exc:
        try:
            return open_browser_fn(title, body_markdown)
        except Exception as fallback_exc:
            raise RuntimeError(
                f"Failed to submit issue: {exc}. Browser fallback failed: {fallback_exc}"
            ) from exc

    try:
        parsed = json.loads(raw) if raw else {}
    except Exception:
        parsed = {}
    issue_url = str(parsed.get("html_url", "")).strip()
    if not issue_url:
        raise RuntimeError("Issue was created but no issue URL was returned.")
    return issue_url
