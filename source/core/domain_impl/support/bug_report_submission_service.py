"""Bug report submission orchestration helpers.

Owns screenshot upload and Discord forum mirror orchestration so UI code stays
focused on presentation and user interactions.
"""

from __future__ import annotations

from typing import Any, Callable


def upload_bug_screenshot(
    *,
    source_path: str,
    summary: str,
    token_env_name: str,
    owner: str,
    repo: str,
    branch: str,
    validate_file_fn: Callable[[str], str],
    detect_magic_ext_fn: Callable[[str], str],
    build_repo_path_fn: Callable[[str, str], str],
    prepare_upload_bytes_fn: Callable[[str, str], tuple[bytes, str]],
    bug_report_api_service: Any,
) -> dict[str, Any]:
    """Upload screenshot via bug-report API service and return upload metadata."""
    return bug_report_api_service.upload_bug_screenshot(
        source_path=source_path,
        summary=summary,
        token_env_name=token_env_name,
        owner=owner,
        repo=repo,
        branch=branch,
        validate_file_fn=validate_file_fn,
        detect_magic_ext_fn=detect_magic_ext_fn,
        build_repo_path_fn=lambda source_name, *, summary="": build_repo_path_fn(source_name, str(summary)),
        prepare_upload_bytes_fn=prepare_upload_bytes_fn,
    )


def submit_bug_report_discord_forum(
    *,
    webhook_env_name: str,
    summary: str,
    details: str,
    issue_url: str,
    app_version: str,
    theme_variant: str,
    selected_path: str,
    last_json_error: str,
    last_highlight_note: str,
    now_text: str,
    python_version: str,
    platform_text: str,
    include_diag: bool,
    diag_tail: str,
    crash_tail: str,
    discord_contact: str,
    screenshot_url: str,
    screenshot_filename: str,
    screenshot_note: str,
    forum_tag_ids_raw: str,
    bug_report_api_service: Any,
) -> dict[str, Any]:
    """Submit optional Discord forum mirror payload for a bug report."""
    return bug_report_api_service.submit_bug_report_discord_forum(
        webhook_env_name=webhook_env_name,
        summary=summary,
        details=details,
        issue_url=issue_url,
        app_version=app_version,
        theme_variant=theme_variant,
        selected_path=selected_path,
        last_json_error=last_json_error,
        last_highlight_note=last_highlight_note,
        now_text=now_text,
        python_version=python_version,
        platform_text=platform_text,
        include_diag=include_diag,
        diag_tail=diag_tail,
        crash_tail=crash_tail,
        discord_contact=discord_contact,
        screenshot_url=screenshot_url,
        screenshot_filename=screenshot_filename,
        screenshot_note=screenshot_note,
        forum_tag_ids_raw=forum_tag_ids_raw,
    )

