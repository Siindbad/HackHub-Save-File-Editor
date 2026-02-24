"""Bug-report markdown context assembly helpers."""

from datetime import datetime
from typing import Any


def build_bug_report_markdown(
    *,
    summary: Any,
    details: Any,
    include_diag: Any,
    discord_contact: Any,
    crash_tail: Any,
    screenshot_url: Any,
    screenshot_filename: Any,
    screenshot_note: Any,
    app_version: Any,
    theme_variant: Any,
    selected_path: Any,
    last_json_error: Any,
    last_highlight_note: Any,
    python_version: Any,
    platform_text: Any,
    read_diag_log_tail: Any,
    bug_report_builder: Any,
) -> Any:
    """Assemble bug-report markdown payload from runtime context and callbacks."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    diag_tail = read_diag_log_tail() if include_diag else ""
    return bug_report_builder(
        summary=summary,
        details=details,
        now_text=now,
        app_version=app_version,
        theme_variant=theme_variant,
        selected_path=selected_path,
        last_json_error=last_json_error,
        last_highlight_note=last_highlight_note,
        python_version=python_version,
        platform_text=platform_text,
        include_diag=include_diag,
        diag_tail=diag_tail,
        crash_tail=crash_tail,
        discord_contact=discord_contact,
        screenshot_url=screenshot_url,
        screenshot_filename=screenshot_filename,
        screenshot_note=screenshot_note,
    )
