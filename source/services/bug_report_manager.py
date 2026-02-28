"""Bug report and crash domain module."""

from __future__ import annotations

from typing import Any

from core.domain_impl.infra import token_env_service
from core.domain_impl.support import bug_report_api_service
from core.domain_impl.support import telemetry_core as bug_report_browser_service
from core.domain_impl.support import telemetry_core as bug_report_context_service
from core.domain_impl.support import telemetry_core as bug_report_cooldown_service
from core.domain_impl.support import telemetry_core as bug_report_service
from core.domain_impl.support import telemetry_core as bug_report_submission_service
from core.domain_impl.support import telemetry_core as bug_report_ui_service
from core.domain_impl.support import clipboard_service
from core.domain_impl.support import telemetry_core as crash_logging_service
from core.domain_impl.support import telemetry_core as crash_offer_service
from core.domain_impl.support import telemetry_core as crash_report_service
from core.domain_impl.support import diag_log_housekeeping_service
from core.domain_impl.support import error_hook_service
from core.domain_impl.support import error_overlay_service
from core.domain_impl.support import error_service


def build_bug_report_markdown(
    owner: Any,
    *,
    summary: str,
    details: str,
    include_diag: bool = True,
    discord_contact: str = "",
    crash_tail: str = "",
    screenshot_url: str = "",
    screenshot_filename: str = "",
    screenshot_note: str = "",
    platform_module: Any,
) -> str:
    """Build markdown payload for bug report submissions."""
    return bug_report_context_service.build_bug_report_markdown(
        summary=summary,
        details=details,
        include_diag=include_diag,
        discord_contact=discord_contact,
        crash_tail=crash_tail,
        screenshot_url=screenshot_url,
        screenshot_filename=screenshot_filename,
        screenshot_note=screenshot_note,
        app_version=getattr(owner, "APP_VERSION", ""),
        theme_variant=str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper(),
        selected_path=owner._selected_tree_path_text(),
        last_json_error=str(getattr(owner, "_last_json_error_msg", "") or ""),
        last_highlight_note=str(getattr(owner, "_last_error_highlight_note", "") or ""),
        python_version=platform_module.python_version(),
        platform_text=platform_module.platform(),
        read_diag_log_tail=owner._read_diag_log_tail,
        bug_report_builder=bug_report_service.build_bug_report_markdown,
    )


def sanitize_bug_screenshot_slug(value: Any) -> str:
    """Normalize screenshot slug text for upload path safety."""
    return str(bug_report_service.sanitize_bug_screenshot_slug(value))


def build_bug_screenshot_repo_path(owner: Any, source_filename: str, *, summary: str = "") -> str:
    """Build bug screenshot repository upload path."""
    return str(
        bug_report_service.build_bug_screenshot_repo_path(
            source_filename,
            summary=summary,
            uploads_dir=getattr(owner, "BUG_REPORT_UPLOADS_DIR", "bug-uploads"),
        )
    )


def validate_bug_screenshot_file(owner: Any, path: str) -> str:
    """Validate screenshot extension/magic/size/dimensions for bug report uploads."""
    return str(
        bug_report_service.validate_bug_screenshot_file(
            path,
            allowed_extensions=getattr(owner, "BUG_REPORT_SCREENSHOT_ALLOWED_EXTENSIONS", ()),
            max_bytes=getattr(owner, "BUG_REPORT_SCREENSHOT_MAX_BYTES", 5 * 1024 * 1024),
            max_dimension=getattr(owner, "BUG_REPORT_SCREENSHOT_MAX_DIMENSION", 4096),
        )
    )


def detect_bug_screenshot_magic_ext(source_path: str) -> str:
    """Detect screenshot extension from file signature bytes."""
    return str(bug_report_service.detect_bug_screenshot_magic_ext(source_path))


def validate_bug_screenshot_dimensions(owner: Any, source_path: str) -> None:
    """Validate screenshot dimensions against configured bug-report limits."""
    bug_report_service.validate_bug_screenshot_dimensions(
        source_path,
        max_dimension=getattr(owner, "BUG_REPORT_SCREENSHOT_MAX_DIMENSION", 4096),
    )


def prepare_bug_screenshot_upload_bytes(owner: Any, source_path: str, detected_ext: str) -> tuple[bytes, str]:
    """Normalize screenshot bytes for upload to bug-report backend targets."""
    prepared = bug_report_service.prepare_bug_screenshot_upload_bytes(
        source_path,
        detected_ext,
        max_bytes=getattr(owner, "BUG_REPORT_SCREENSHOT_MAX_BYTES", 5 * 1024 * 1024),
    )
    return prepared[0], str(prepared[1])


def bug_report_new_issue_url(owner: Any, title: str, body_markdown: str, *, include_body: bool = True) -> str:
    """Build browser issue-form URL for bug-report fallback flow."""
    return str(
        bug_report_service.build_bug_report_new_issue_url(
            owner=getattr(owner, "BUG_REPORT_GITHUB_OWNER", ""),
            repo=getattr(owner, "BUG_REPORT_GITHUB_REPO", ""),
            labels=getattr(owner, "BUG_REPORT_LABELS", ()),
            title=title,
            body_markdown=body_markdown,
            include_body=include_body,
        )
    )


def copy_bug_report_body_to_clipboard(owner: Any, body_markdown: str, *, expected_errors: tuple[type[BaseException], ...]) -> bool:
    """Copy report body text to clipboard for browser-fallback privacy flow."""
    return bool(
        clipboard_service.copy_text_to_clipboard(
            payload=body_markdown,
            root=getattr(owner, "root", None),
            expected_errors=expected_errors,
        )
    )


def open_bug_report_in_browser(
    owner: Any,
    title: str,
    body_markdown: str,
    *,
    webbrowser_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> Any:
    """Open clean browser issue form and copy full body text to clipboard."""
    return bug_report_browser_service.open_bug_report_in_browser(
        title=title,
        body_markdown=body_markdown,
        copy_to_clipboard_fn=lambda body: copy_bug_report_body_to_clipboard(
            owner,
            body,
            expected_errors=expected_errors,
        ),
        build_issue_url_fn=lambda issue_title, issue_body, include_body=False: bug_report_new_issue_url(
            owner,
            issue_title,
            issue_body,
            include_body=include_body,
        ),
        open_bug_report_browser_fn=bug_report_api_service.open_bug_report_in_browser,
        open_new_tab_fn=webbrowser_module.open_new_tab,
    )


def has_bug_report_token(owner: Any, *, os_module: Any) -> bool:
    """Return whether bug-report API token is available in the environment."""
    return bool(token_env_service.has_bug_report_token(owner))


def submit_cooldown_remaining(owner: Any, *, now_monotonic: float | None = None, time_module: Any) -> int:
    """Return remaining bug-report submit cooldown seconds."""
    now_val = float(time_module.monotonic()) if now_monotonic is None else float(now_monotonic)
    return int(
        bug_report_cooldown_service.submit_cooldown_remaining(
            getattr(owner, "_last_bug_report_submit_monotonic", 0.0),
            getattr(owner, "BUG_REPORT_SUBMIT_COOLDOWN_SECONDS", 45),
            now_val,
        )
    )


def mark_submit_now(owner: Any, *, now_monotonic: float | None = None, time_module: Any) -> float:
    """Persist current submit timestamp used by bug-report cooldown checks."""
    now_val = float(time_module.monotonic()) if now_monotonic is None else float(now_monotonic)
    marked = float(bug_report_cooldown_service.mark_submit_now(now_val))
    owner._last_bug_report_submit_monotonic = marked
    return marked


def upload_bug_screenshot(owner: Any, source_path: str, *, summary: str) -> dict[str, Any]:
    """Upload screenshot for bug report and return upload metadata."""
    return bug_report_submission_service.upload_bug_screenshot(
        source_path=source_path,
        summary=summary,
        token_env_name=str(token_env_service.bug_report_token_env_name(owner)),
        owner=str(getattr(owner, "BUG_REPORT_GITHUB_OWNER", "")),
        repo=str(getattr(owner, "BUG_REPORT_GITHUB_REPO", "")),
        branch=str(getattr(owner, "BUG_REPORT_UPLOAD_BRANCH", "main")),
        validate_file_fn=lambda path: validate_bug_screenshot_file(owner, path),
        detect_magic_ext_fn=detect_bug_screenshot_magic_ext,
        build_repo_path_fn=lambda source_name, summary_text: build_bug_screenshot_repo_path(
            owner,
            source_name,
            summary=summary_text,
        ),
        prepare_upload_bytes_fn=lambda source, detected_ext: prepare_bug_screenshot_upload_bytes(
            owner,
            source,
            detected_ext,
        ),
        bug_report_api_service=bug_report_api_service,
    )


def submit_bug_report_discord_forum(
    owner: Any,
    *,
    summary: str,
    details: str,
    issue_url: str,
    include_diag: bool = False,
    diag_tail: str = "",
    crash_tail: str = "",
    discord_contact: str = "",
    screenshot_url: str = "",
    screenshot_filename: str = "",
    screenshot_note: str = "",
    time_module: Any,
    platform_module: Any,
    os_module: Any,
) -> dict[str, Any]:
    """Submit optional Discord forum mirror payload for bug reports."""
    return bug_report_submission_service.submit_bug_report_discord_forum(
        webhook_env_name=str(getattr(owner, "BUG_REPORT_DISCORD_WEBHOOK_ENV", "DISCORD_BUGREPORT_WEBHOOK")),
        summary=summary,
        details=details,
        issue_url=issue_url,
        app_version=str(getattr(owner, "APP_VERSION", "") or ""),
        theme_variant=str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper(),
        selected_path=str(owner._selected_tree_path_text()),
        last_json_error=str(getattr(owner, "_last_json_error_msg", "") or ""),
        last_highlight_note=str(getattr(owner, "_last_error_highlight_note", "") or ""),
        now_text=time_module.strftime("%Y-%m-%d %H:%M:%S"),
        python_version=platform_module.python_version(),
        platform_text=platform_module.platform(),
        include_diag=bool(include_diag),
        diag_tail=str(diag_tail or ""),
        crash_tail=str(crash_tail or ""),
        discord_contact=str(discord_contact or ""),
        screenshot_url=screenshot_url,
        screenshot_filename=screenshot_filename,
        screenshot_note=screenshot_note,
        forum_tag_ids_raw=os_module.getenv(
            str(getattr(owner, "BUG_REPORT_DISCORD_FORUM_TAG_IDS_ENV", "") or ""),
            "",
        ),
        bug_report_api_service=bug_report_api_service,
    )


def trigger_report_flow(
    owner: Any,
    *,
    tk: Any,
    filedialog: Any,
    messagebox: Any,
    threading_module: Any,
    time_module: Any,
    platform_module: Any,
    os_module: Any,
    summary_prefill: str = "",
    details_prefill: str = "",
    include_diag_default: bool = True,
    crash_tail: str = "",
) -> Any:
    """Launch the bug-report dialog with service-layer submission callbacks."""
    return bug_report_ui_service.open_bug_report_dialog(
        owner,
        tk=tk,
        filedialog=filedialog,
        messagebox=messagebox,
        summary_prefill=summary_prefill,
        details_prefill=details_prefill,
        include_diag_default=include_diag_default,
        crash_tail=crash_tail,
        threading_module=threading_module,
        validate_bug_screenshot_file_fn=lambda path: validate_bug_screenshot_file(owner, path),
        submit_cooldown_remaining_fn=lambda: submit_cooldown_remaining(owner, time_module=time_module),
        mark_submit_now_fn=lambda: mark_submit_now(owner, time_module=time_module),
        has_bug_report_token_fn=lambda: has_bug_report_token(owner, os_module=os_module),
        upload_bug_screenshot_fn=lambda source_path, summary: upload_bug_screenshot(
            owner,
            source_path,
            summary=summary,
        ),
        build_bug_report_markdown_fn=lambda **kwargs: build_bug_report_markdown(
            owner,
            platform_module=platform_module,
            **kwargs,
        ),
        build_bug_report_issue_url_fn=lambda title, body_markdown, include_body=False: bug_report_new_issue_url(
            owner,
            title,
            body_markdown,
            include_body=include_body,
        ),
        submit_bug_report_discord_forum_fn=lambda **kwargs: submit_bug_report_discord_forum(
            owner,
            time_module=time_module,
            platform_module=platform_module,
            os_module=os_module,
            **kwargs,
        ),
    )


class BugReportManager:
    bug_report_api_service = bug_report_api_service
    bug_report_browser_service = bug_report_browser_service
    bug_report_context_service = bug_report_context_service
    bug_report_cooldown_service = bug_report_cooldown_service
    bug_report_service = bug_report_service
    bug_report_submission_service = bug_report_submission_service
    bug_report_ui_service = bug_report_ui_service
    clipboard_service = clipboard_service
    crash_logging_service = crash_logging_service
    crash_offer_service = crash_offer_service
    crash_report_service = crash_report_service
    diag_log_housekeeping_service = diag_log_housekeeping_service
    error_hook_service = error_hook_service
    error_overlay_service = error_overlay_service
    error_service = error_service
    build_bug_report_markdown = staticmethod(build_bug_report_markdown)
    sanitize_bug_screenshot_slug = staticmethod(sanitize_bug_screenshot_slug)
    build_bug_screenshot_repo_path = staticmethod(build_bug_screenshot_repo_path)
    validate_bug_screenshot_file = staticmethod(validate_bug_screenshot_file)
    detect_bug_screenshot_magic_ext = staticmethod(detect_bug_screenshot_magic_ext)
    validate_bug_screenshot_dimensions = staticmethod(validate_bug_screenshot_dimensions)
    prepare_bug_screenshot_upload_bytes = staticmethod(prepare_bug_screenshot_upload_bytes)
    bug_report_new_issue_url = staticmethod(bug_report_new_issue_url)
    copy_bug_report_body_to_clipboard = staticmethod(copy_bug_report_body_to_clipboard)
    open_bug_report_in_browser = staticmethod(open_bug_report_in_browser)
    has_bug_report_token = staticmethod(has_bug_report_token)
    submit_cooldown_remaining = staticmethod(submit_cooldown_remaining)
    mark_submit_now = staticmethod(mark_submit_now)
    upload_bug_screenshot = staticmethod(upload_bug_screenshot)
    submit_bug_report_discord_forum = staticmethod(submit_bug_report_discord_forum)
    trigger_report_flow = staticmethod(trigger_report_flow)


BUG_REPORT = BugReportManager()
