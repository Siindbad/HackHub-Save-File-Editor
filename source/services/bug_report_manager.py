"""Bug report and crash domain module."""

from core.domain_impl.support import bug_report_api_service
from core.domain_impl.support import bug_report_browser_service
from core.domain_impl.support import bug_report_context_service
from core.domain_impl.support import bug_report_cooldown_service
from core.domain_impl.support import bug_report_service
from core.domain_impl.support import bug_report_ui_service
from core.domain_impl.support import clipboard_service
from core.domain_impl.support import crash_logging_service
from core.domain_impl.support import crash_offer_service
from core.domain_impl.support import crash_report_service
from core.domain_impl.support import diag_log_housekeeping_service
from core.domain_impl.support import error_hook_service
from core.domain_impl.support import error_overlay_service
from core.domain_impl.support import error_service


class BugReportManager:
    bug_report_api_service = bug_report_api_service
    bug_report_browser_service = bug_report_browser_service
    bug_report_context_service = bug_report_context_service
    bug_report_cooldown_service = bug_report_cooldown_service
    bug_report_service = bug_report_service
    bug_report_ui_service = bug_report_ui_service
    clipboard_service = clipboard_service
    crash_logging_service = crash_logging_service
    crash_offer_service = crash_offer_service
    crash_report_service = crash_report_service
    diag_log_housekeeping_service = diag_log_housekeeping_service
    error_hook_service = error_hook_service
    error_overlay_service = error_overlay_service
    error_service = error_service


BUG_REPORT = BugReportManager()
