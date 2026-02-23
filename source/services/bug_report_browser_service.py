"""Bug-report browser fallback orchestration helpers."""
from typing import Any


def open_bug_report_in_browser(
    title: Any,
    body_markdown: Any,
    copy_to_clipboard_fn: Any,
    build_issue_url_fn: Any,
    open_bug_report_browser_fn: Any,
    open_new_tab_fn: Any,
) -> Any:
    """Open clean issue form while copying full report body into clipboard."""
    copy_to_clipboard_fn(body_markdown)
    issue_url = build_issue_url_fn(title, body_markdown, include_body=False)
    return open_bug_report_browser_fn(
        issue_url=issue_url,
        open_new_tab_fn=open_new_tab_fn,
    )
