"""Crash report offer scheduling and prompt helpers."""
from typing import Any


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
