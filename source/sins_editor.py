import hashlib
import importlib
import json
import logging
import os
import platform
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import uuid
import urllib.error
import urllib.request
import webbrowser
from collections import deque
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from services import bug_report_manager
from services import document_service
from services import editor_ui_core
from services import input_mode_manager
from services import json_engine
from services import json_view_manager
from services import runtime_service
from services import text_context_manager
from services import theme_manager
from services import tree_manager
from services import update_orchestrator
from services import validation_engine
from core import constants as app_constants
from core import display_profile as display_profile_core
from core.editor_state import EditorState
from core import json_diagnostics as json_diag_core
from core import json_error_diagnostics_core
from core import json_error_highlight_core
from core import layout_topbar as layout_topbar_core
from core import startup_loader as startup_loader_core
from core.domain_impl.infra.editor_lifecycle_service import LIFECYCLE
from core.domain_impl.ui.visual_asset_service import VISUALS

# Domain compatibility aliases keep existing call sites stable while imports are consolidated.
bug_report_api_service = bug_report_manager.BUG_REPORT.bug_report_api_service
bug_report_browser_service = bug_report_manager.BUG_REPORT.bug_report_browser_service
bug_report_context_service = bug_report_manager.BUG_REPORT.bug_report_context_service
bug_report_cooldown_service = bug_report_manager.BUG_REPORT.bug_report_cooldown_service
bug_report_service = bug_report_manager.BUG_REPORT.bug_report_service
bug_report_ui_service = bug_report_manager.BUG_REPORT.bug_report_ui_service
clipboard_service = bug_report_manager.BUG_REPORT.clipboard_service
crash_logging_service = bug_report_manager.BUG_REPORT.crash_logging_service
crash_offer_service = bug_report_manager.BUG_REPORT.crash_offer_service
crash_report_service = bug_report_manager.BUG_REPORT.crash_report_service
diag_log_housekeeping_service = bug_report_manager.BUG_REPORT.diag_log_housekeeping_service
error_hook_service = bug_report_manager.BUG_REPORT.error_hook_service
error_overlay_service = bug_report_manager.BUG_REPORT.error_overlay_service
error_service = bug_report_manager.BUG_REPORT.error_service
document_io_service = document_service.DOCUMENT.document_io_service
editor_mode_switch_service = document_service.DOCUMENT.editor_mode_switch_service
editor_purge_service = document_service.DOCUMENT.editor_purge_service
asset_image_service = editor_ui_core.EDITOR_UI.asset_image_service
footer_service = editor_ui_core.EDITOR_UI.footer_service
input_mode_paned_lock_service = editor_ui_core.EDITOR_UI.input_mode_paned_lock_service
loader_service = editor_ui_core.EDITOR_UI.loader_service
startup_loader_lifecycle_service = editor_ui_core.EDITOR_UI.startup_loader_lifecycle_service
startup_loader_ui_service = editor_ui_core.EDITOR_UI.startup_loader_ui_service
toolbar_service = editor_ui_core.EDITOR_UI.toolbar_service
ui_build_service = editor_ui_core.EDITOR_UI.ui_build_service
ui_dispatch_service = editor_ui_core.EDITOR_UI.ui_dispatch_service
ui_factory_service = editor_ui_core.EDITOR_UI.ui_factory_service
ui_timer_service = editor_ui_core.EDITOR_UI.ui_timer_service
UI_FACTORY = ui_factory_service
input_mode_diag_service = input_mode_manager.INPUT_MODE.input_mode_diag_service
input_mode_find_service = input_mode_manager.INPUT_MODE.input_mode_find_service
input_mode_render_dispatch_service = input_mode_manager.INPUT_MODE.input_mode_render_dispatch_service
input_mode_service = input_mode_manager.INPUT_MODE.input_mode_service
json_apply_commit_service = json_engine.JSON_ENGINE.json_apply_commit_service
json_closer_symbol_service = json_engine.JSON_ENGINE.json_closer_symbol_service
json_colon_comma_service = json_engine.JSON_ENGINE.json_colon_comma_service
json_diagnostics_service = json_engine.JSON_ENGINE.json_diagnostics_service
json_edit_flow_service = json_engine.JSON_ENGINE.json_edit_flow_service
json_error_diag_service = json_engine.JSON_ENGINE.json_error_diag_service
json_error_highlight_render_service = json_engine.JSON_ENGINE.json_error_highlight_render_service
json_nearby_line_service = json_engine.JSON_ENGINE.json_nearby_line_service
json_open_symbol_service = json_engine.JSON_ENGINE.json_open_symbol_service
json_parse_feedback_service = json_engine.JSON_ENGINE.json_parse_feedback_service
json_path_service = json_engine.JSON_ENGINE.json_path_service
json_property_key_rule_service = json_engine.JSON_ENGINE.json_property_key_rule_service
json_quoted_item_tail_service = json_engine.JSON_ENGINE.json_quoted_item_tail_service
json_repair_service = json_engine.JSON_ENGINE.json_repair_service
json_scalar_tail_service = json_engine.JSON_ENGINE.json_scalar_tail_service
json_top_level_close_service = json_engine.JSON_ENGINE.json_top_level_close_service
json_validation_feedback_service = json_engine.JSON_ENGINE.json_validation_feedback_service
json_repair_dispatch_service = json_engine.JSON_ENGINE.repair_dispatch
json_find_nav_service = json_view_manager.JSON_VIEW.json_find_nav_service
json_find_service = json_view_manager.JSON_VIEW.json_find_service
json_text_find_service = json_view_manager.JSON_VIEW.json_text_find_service
json_view_render_service = json_view_manager.JSON_VIEW.json_view_render_service
json_view_service = json_view_manager.JSON_VIEW.json_view_service
runtime_log_service = runtime_service.RUNTIME.runtime_log_service
runtime_paths_service = runtime_service.RUNTIME.runtime_paths_service
token_env_service = runtime_service.RUNTIME.token_env_service
user_settings_service = runtime_service.RUNTIME.user_settings_service
windows_runtime_service = runtime_service.RUNTIME.windows_runtime_service
text_context_action_service = text_context_manager.TEXT_CONTEXT.text_context_action_service
text_context_pointer_service = text_context_manager.TEXT_CONTEXT.text_context_pointer_service
text_context_state_service = text_context_manager.TEXT_CONTEXT.text_context_state_service
text_context_widget_service = text_context_manager.TEXT_CONTEXT.text_context_widget_service
input_bank_style_service = input_mode_manager.INPUT_WORKFLOW.input_bank_style_service
input_database_bcc_style_service = input_mode_manager.INPUT_WORKFLOW.input_database_bcc_style_service
input_database_style_service = input_mode_manager.INPUT_WORKFLOW.input_database_style_service
input_network_firewall_style_service = input_mode_manager.INPUT_WORKFLOW.input_network_firewall_style_service
input_network_device_bcc_style_service = input_mode_manager.INPUT_WORKFLOW.input_network_device_bcc_style_service
input_network_device_geoip_style_service = input_mode_manager.INPUT_WORKFLOW.input_network_device_geoip_style_service
input_network_router_style_service = input_mode_manager.INPUT_WORKFLOW.input_network_router_style_service
input_suspicion_phone_style_service = input_mode_manager.INPUT_WORKFLOW.input_suspicion_phone_style_service
theme_asset_service = theme_manager.THEME.theme_asset_service
color_utility_service = theme_manager.THEME.color_utility_service
theme_service = theme_manager.THEME.theme_service
tree_engine_service = tree_manager.TREE.tree_engine_service
tree_mode_service = tree_manager.TREE.tree_mode_service
tree_navigation_service = tree_manager.TREE.tree_navigation_service
tree_policy_service = tree_manager.TREE.tree_policy_service
tree_view_service = tree_manager.TREE.tree_view_service
update_asset_service = update_orchestrator.UPDATE.update_asset_service
update_checksum_service = update_orchestrator.UPDATE.update_checksum_service
update_diag_service = update_orchestrator.UPDATE.update_diag_service
update_download_service = update_orchestrator.UPDATE.update_download_service
update_fallback_service = update_orchestrator.UPDATE.update_fallback_service
update_headers_service = update_orchestrator.UPDATE.update_headers_service
update_orchestrator_service = update_orchestrator.UPDATE.update_orchestrator_service
update_release_info_service = update_orchestrator.UPDATE.update_release_info_service
update_service = update_orchestrator.UPDATE.update_service
update_signature_service = update_orchestrator.UPDATE.update_signature_service
update_ui_service = update_orchestrator.UPDATE.update_ui_service
update_url_service = update_orchestrator.UPDATE.update_url_service
update_version_service = update_orchestrator.UPDATE.update_version_service
highlight_label_service = validation_engine.VALIDATION.highlight_label_service
label_format_service = validation_engine.VALIDATION.label_format_service
validation_service = validation_engine.VALIDATION.validation_service
version_format_service = validation_engine.VALIDATION.version_format_service

_LOG = logging.getLogger(__name__)

# Keep explicit import references for compatibility/regression contracts.
_IMPORT_COMPAT_TOUCH = (
    document_io_service,
    json_apply_commit_service,
    json_error_highlight_render_service,
    json_nearby_line_service,
    json_parse_feedback_service,
    json_quoted_item_tail_service,
    json_validation_feedback_service,
    json_view_service,
    tree_mode_service,
    update_release_info_service,
    json_error_highlight_core,
)

_EXPECTED_APP_ERRORS = (
    tk.TclError,
    RuntimeError,
    OSError,
    ValueError,
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    ImportError,
    json.JSONDecodeError,
    UnicodeDecodeError,
    subprocess.SubprocessError,
    urllib.error.URLError,
    urllib.error.HTTPError,
)

try:
    import winreg
except ImportError:
    winreg = None

# Backward-compatible module alias for older tests/integrations.
edit_guard_service = highlight_label_service


def _strip_invalid_trailing_chars(value_str):
    """Module-level helper to remove invalid trailing characters.

    Kept top-level so test helpers that bind class methods to SimpleNamespace
    can still call the trimming logic via the module name.
    """
    if not value_str:
        return value_str
    valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.@\t \n\r")
    while value_str and value_str[-1] not in valid_chars:
        value_str = value_str[:-1]
    return value_str.rstrip()


def _module_resource_base_dir():
    meipass_dir = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and isinstance(meipass_dir, str) and meipass_dir:
        return meipass_dir
    return os.path.dirname(os.path.abspath(__file__))


def _enable_windows_dpi_awareness():
    """Delegate Windows DPI awareness setup to runtime service."""
    return windows_runtime_service.enable_windows_dpi_awareness()


class JsonEditor:
    APP_VERSION = app_constants.APP_VERSION
    GITHUB_OWNER = app_constants.GITHUB_OWNER
    GITHUB_REPO = app_constants.GITHUB_REPO
    GITHUB_ASSET_NAME = app_constants.GITHUB_ASSET_NAME
    DIST_BRANCH = app_constants.DIST_BRANCH
    DIST_VERSION_FILE = app_constants.DIST_VERSION_FILE
    GITHUB_TOKEN_ENV = app_constants.GITHUB_TOKEN_ENV
    UPDATE_TOKEN_ENV = app_constants.UPDATE_TOKEN_ENV
    BUG_REPORT_TOKEN_ENV = app_constants.BUG_REPORT_TOKEN_ENV
    BUG_REPORT_GITHUB_OWNER = app_constants.BUG_REPORT_GITHUB_OWNER
    BUG_REPORT_GITHUB_REPO = app_constants.BUG_REPORT_GITHUB_REPO
    BUG_REPORT_LABELS = app_constants.BUG_REPORT_LABELS
    BUG_REPORT_USE_CUSTOM_CHROME = app_constants.BUG_REPORT_USE_CUSTOM_CHROME
    BUG_REPORT_UPLOAD_BRANCH = app_constants.BUG_REPORT_UPLOAD_BRANCH
    BUG_REPORT_UPLOADS_DIR = app_constants.BUG_REPORT_UPLOADS_DIR
    BUG_REPORT_SCREENSHOT_ALLOWED_EXTENSIONS = app_constants.BUG_REPORT_SCREENSHOT_ALLOWED_EXTENSIONS
    BUG_REPORT_SCREENSHOT_MAX_BYTES = app_constants.BUG_REPORT_SCREENSHOT_MAX_BYTES
    BUG_REPORT_SCREENSHOT_MAX_DIMENSION = app_constants.BUG_REPORT_SCREENSHOT_MAX_DIMENSION
    BUG_REPORT_SCREENSHOT_RETENTION_DAYS = app_constants.BUG_REPORT_SCREENSHOT_RETENTION_DAYS
    BUG_REPORT_SUBMIT_COOLDOWN_SECONDS = app_constants.BUG_REPORT_SUBMIT_COOLDOWN_SECONDS
    BUG_REPORT_DISCORD_WEBHOOK_ENV = app_constants.BUG_REPORT_DISCORD_WEBHOOK_ENV
    BUG_REPORT_DISCORD_FORUM_TAG_IDS_ENV = app_constants.BUG_REPORT_DISCORD_FORUM_TAG_IDS_ENV
    PHONE_FIELD_PATTERN = re.compile(r'"phone"\s*:\s*"([^"]*)"')
    EMAIL_FIELD_PATTERN = re.compile(r'"(email|from|to)"\s*:\s*"([^"]*)"')
    DIAG_LOG_MAX_BYTES = app_constants.DIAG_LOG_MAX_BYTES
    DIAG_LOG_KEEP_BYTES = app_constants.DIAG_LOG_KEEP_BYTES
    DIAG_LOG_KEEP_DAYS = 2
    DIAG_LOG_FILENAME = app_constants.DIAG_LOG_FILENAME
    LEGACY_DIAG_LOG_FILENAMES = app_constants.LEGACY_DIAG_LOG_FILENAMES
    LEGACY_SETTINGS_FILENAME = app_constants.LEGACY_SETTINGS_FILENAME
    RUNTIME_DIR_NAME = app_constants.RUNTIME_DIR_NAME
    SETTINGS_FILENAME = app_constants.SETTINGS_FILENAME
    CRASH_LOG_FILENAME = app_constants.CRASH_LOG_FILENAME
    CRASH_STATE_FILENAME = app_constants.CRASH_STATE_FILENAME
    CRASH_LOG_TAIL_MAX_CHARS = app_constants.CRASH_LOG_TAIL_MAX_CHARS
    LIVE_FEEDBACK_DELAY_MS_DEFAULT = app_constants.LIVE_FEEDBACK_DELAY_MS_DEFAULT
    STATUS_LOADED = app_constants.STATUS_LOADED
    STATUS_SAVED = app_constants.STATUS_SAVED
    STATUS_EXPORTED_HHSAV = app_constants.STATUS_EXPORTED_HHSAV
    EXPORT_HHSAV_DIALOG_TITLE = app_constants.EXPORT_HHSAV_DIALOG_TITLE
    DIST_ASSET_SHA256_CANDIDATES = app_constants.DIST_ASSET_SHA256_CANDIDATES
    UPDATE_REQUIRE_SHA256 = app_constants.UPDATE_REQUIRE_SHA256
    # Authenticode trust gate for updater payloads:
    # - verification always runs on Windows when enabled
    # - strict mode hard-fails updates when signature is invalid/missing
    UPDATE_VERIFY_AUTHENTICODE = app_constants.UPDATE_VERIFY_AUTHENTICODE
    UPDATE_REQUIRE_AUTHENTICODE = app_constants.UPDATE_REQUIRE_AUTHENTICODE
    UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS = app_constants.UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS
    # Known-domain allowlist validation is retired; keep empty compatibility fields.
    KNOWN_EMAIL_DOMAINS: set[str] = set()
    KNOWN_EMAIL_DOMAIN_ROOTS: set[str] = set()
    HIDDEN_ROOT_TREE_CATEGORIES_JSON = app_constants.HIDDEN_ROOT_TREE_CATEGORIES
    HIDDEN_ROOT_TREE_CATEGORIES_INPUT = app_constants.HIDDEN_ROOT_TREE_CATEGORIES_INPUT
    HIDDEN_ROOT_TREE_KEYS_JSON = app_constants.HIDDEN_ROOT_TREE_KEYS_JSON
    HIDDEN_ROOT_TREE_KEYS_INPUT = app_constants.HIDDEN_ROOT_TREE_KEYS_INPUT
    TREE_B_SAFE_DISPLAY_LABELS = dict(app_constants.TREE_B_SAFE_DISPLAY_LABELS)
    # Snapshot for re-installing header A/B controls later with exact previous values.
    HEADER_VARIANT_RESTORE_SPEC = dict(app_constants.HEADER_VARIANT_RESTORE_SPEC)
    TREE_MAIN_MARKER_FILES = dict(app_constants.TREE_MAIN_MARKER_FILES)
    TREE_MAIN_MARKER_SHA256 = dict(app_constants.TREE_MAIN_MARKER_SHA256)
    TREE_B2_MARKER_SHA256 = dict(app_constants.TREE_B2_MARKER_SHA256)
    INPUT_MODE_DISABLED_ROOT_CATEGORIES = app_constants.INPUT_MODE_DISABLED_ROOT_CATEGORIES
    INPUT_MODE_DISABLED_ROOT_KEYS = app_constants.INPUT_MODE_DISABLED_ROOT_KEYS
    INPUT_MODE_NO_EXPAND_ROOT_CATEGORIES = app_constants.INPUT_MODE_NO_EXPAND_ROOT_CATEGORIES
    INPUT_MODE_NO_EXPAND_ROOT_KEYS = app_constants.INPUT_MODE_NO_EXPAND_ROOT_KEYS
    INPUT_MODE_NETWORK_NO_EXPAND_GROUPS = app_constants.INPUT_MODE_NETWORK_NO_EXPAND_GROUPS
    INPUT_MODE_NETWORK_NO_EXPAND_GROUP_KEYS = app_constants.INPUT_MODE_NETWORK_NO_EXPAND_GROUP_KEYS
    INPUT_MODE_NETWORK_HIDDEN_GROUPS = app_constants.INPUT_MODE_NETWORK_HIDDEN_GROUPS
    INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS = app_constants.INPUT_MODE_NETWORK_HIDDEN_GROUP_KEYS
    INPUT_MODE_RED_ARROW_ROOT_CATEGORIES = app_constants.INPUT_MODE_RED_ARROW_ROOT_CATEGORIES
    INPUT_MODE_RED_ARROW_ROOT_KEYS = app_constants.INPUT_MODE_RED_ARROW_ROOT_KEYS
    INPUT_MODE_RED_ARROW_NETWORK_GROUPS = app_constants.INPUT_MODE_RED_ARROW_NETWORK_GROUPS
    INPUT_MODE_RED_ARROW_NETWORK_GROUP_KEYS = app_constants.INPUT_MODE_RED_ARROW_NETWORK_GROUP_KEYS
    INPUT_MODE_DISABLED_CATEGORY_MESSAGE = (
        "Category Is Still Under Developement"
    )
    # Update orchestration helpers keep these message templates visible in editor source.
    UPDATE_PREPARING_OVERLAY_MESSAGE = "Preparing update...\nThe app will restart automatically."
    UPDATE_DOWNLOADING_OVERLAY_MESSAGE = "Downloading update...\nThis may take a moment."
    UPDATE_RESTART_STATUS_MESSAGE = "Update installed. Restarting app..."
    UPDATE_AVAILABLE_PROMPT_TEMPLATE = "Update v{self._format_version(latest_version)} is available."
    UPDATE_CONFIRM_INSTALL_QUESTION = "Do you want to install it now?"
    UPDATE_CONFIRM_WIRING_CONTRACT = """self._ui_call(
self._ask_themed_update_confirm,
"Update",
prompt,
True,
wait=True,
default=False,
)
if not install_started:
"""
    # Parse-error marker contract: keep these note tokens visible in editor source for regression checks.
    PARSE_NOTE_APPLY_EMERGENCY = "overlay_parse_apply_emergency"
    PARSE_NOTE_LIVE_EMERGENCY = "overlay_parse_live_emergency"
    APPLY_FEEDBACK_RESET_CONTRACT = """# Successful Apply Edit ends any prior live-error feedback cycle
self._auto_apply_pending = False
self._auto_apply_in_progress = False
"""
    UPDATE_RELEASES_LATEST_DOWNLOAD_SEGMENT = "/releases/latest/download/"
    UPDATE_ASSET_CONTRACT = """url = self._release_asset_download_url(release_info, self.GITHUB_ASSET_NAME)
if update_asset_name.endswith(".zip"):
raise RuntimeError("Downloaded update is not a valid ZIP package.")
"""
    JSON_DIAGNOSTIC_DELEGATION_CONTRACT = """
json_quoted_item_tail_service.quoted_item_invalid_tail_span(
json_nearby_line_service.find_nearby_line(
json_error_highlight_core.highlight_json_error(
str(note or "") == "missing_list_close_before_object_end"
malformed_missing_close_quote
focus_col_no == 0 and not focus_line_text.strip()
json_bool_true
json_bool_false
self.text.index(f"{focus_line_no}.0 lineend")
json_value_green
Keep startup functional when Pillow is unavailable
if button._siindbad_base_image is None:
"""

    def __setattr__(self, name, value):
        if name == "state":
            object.__setattr__(self, name, value)
            return
        state = self.__dict__.get("state")
        if state is not None and (str(name).startswith("_") or str(name) in {"data", "path", "item_to_path"}):
            state.set_flag(name, value)
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        state = self.__dict__.get("state")
        if state is not None and str(name).startswith("_") and state.has_flag(name):
            return state.get_flag(name)
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def __init__(self, root, path):
        object.__setattr__(self, "state", EditorState())
        self.root = root
        self.root.title(f"SIINDBAD's HackHub Editor - v{self.APP_VERSION}")
        self.data = None
        self.path = None
        self.item_to_path = {}
        self._init_runtime_services()

        self._install_global_error_hooks()

        # Load saved user settings (font size, etc.) before building UI
        try:
            self._load_user_settings()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

        self._configure_root_display_profile()
        self._build_ui()
        # Keep only recent diagnostics day files at startup.
        self._purge_diag_logs_for_new_session()
        try:
            self.root.bind("<Destroy>", self._on_root_destroy, add="+")
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if path:
            self.load_file(path)
        else:
            self._maybe_warn_windows_long_paths_disabled()

    def _init_runtime_services(self):
        """Initialize grouped runtime state buckets through service-oriented clusters."""
        LIFECYCLE.bootstrap(self)

    @staticmethod
    def _is_windows_long_paths_enabled():
        if sys.platform != "win32":
            return True
        if winreg is None:
            return False
        try:
            key_path = r"SYSTEM\CurrentControlSet\Control\FileSystem"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _kind = winreg.QueryValueEx(key, "LongPathsEnabled")
            return int(value) == 1
        except (OSError, ValueError, TypeError):
            return False

    def _maybe_warn_windows_long_paths_disabled(self):
        if sys.platform != "win32":
            return
        if self._is_windows_long_paths_enabled():
            return
        try:
            self.set_status("Tip: Enable Windows long paths for better deep-folder compatibility.")
        except (tk.TclError, RuntimeError, AttributeError):
            pass

    @staticmethod
    def _compute_window_layout_for_screen(
        screen_width,
        screen_height,
        display_scale=1.0,
        base_width=1000,
        base_height=700,
    ):
        return display_profile_core.compute_window_layout_for_screen(
            screen_width,
            screen_height,
            display_scale=display_scale,
            base_width=base_width,
            base_height=base_height,
        )

    def _screen_size(self):
        root = getattr(self, "root", None)
        if root is None:
            return 1280, 720
        try:
            width = int(root.winfo_screenwidth() or 1280)
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            width = 1280
        try:
            height = int(root.winfo_screenheight() or 720)
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            height = 720
        return max(640, width), max(480, height)

    def _detect_display_scale(self):
        root = getattr(self, "root", None)
        if root is None:
            return 1.0
        candidates = []
        try:
            dpi = float(root.winfo_fpixels("1i"))
            if dpi > 40.0:
                candidates.append(dpi / 96.0)
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            pass
        try:
            tk_scaling = float(root.tk.call("tk", "scaling"))
            if tk_scaling > 0.2:
                candidates.append((tk_scaling * 72.0) / 96.0)
        except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
            pass
        return display_profile_core.detect_display_scale_from_candidates(candidates)

    @staticmethod
    def _auto_display_profile_for_screen(screen_width, screen_height, display_scale): return display_profile_core.auto_display_profile_for_screen(
            screen_width,
            screen_height,
            display_scale,
        )

    def _configure_root_display_profile(self):
        root = getattr(self, "root", None)
        if root is None:
            return
        detected_scale = self._detect_display_scale()
        screen_width, screen_height = self._screen_size()
        profile = self._auto_display_profile_for_screen(
            screen_width,
            screen_height,
            detected_scale,
        )
        self._auto_display_profile_name = str(profile.get("name", "default"))
        scale_boost = max(1.0, min(1.20, float(profile.get("scale_boost", 1.0) or 1.0)))
        window_boost = max(1.0, min(1.20, float(profile.get("window_boost", 1.0) or 1.0)))
        display_scale = display_profile_core.clamp_display_scale(float(detected_scale) * scale_boost)
        self._display_scale = display_scale
        try:
            target_scaling = display_profile_core.tk_scaling_from_display_scale(display_scale)
            current_scaling = float(root.tk.call("tk", "scaling"))
            if abs(current_scaling - target_scaling) >= 0.03:
                root.tk.call("tk", "scaling", target_scaling)
        except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
            pass

        base_width = int(round(1000 * window_boost))
        base_height = int(round(700 * window_boost))
        layout = self._compute_window_layout_for_screen(
            screen_width,
            screen_height,
            display_scale=display_scale,
            base_width=base_width,
            base_height=base_height,
        )
        self._window_layout = layout
        try:
            root.minsize(int(layout["min_width"]), int(layout["min_height"]))
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            pass
        try:
            root.geometry(
                f"{int(layout['width'])}x{int(layout['height'])}"
                f"+{int(layout['x'])}+{int(layout['y'])}"
            )
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            try:
                root.geometry(f"{int(layout['width'])}x{int(layout['height'])}")
            except (tk.TclError, RuntimeError, TypeError, ValueError):
                pass

    def _apply_centered_toplevel_geometry(
        self,
        window,
        width_px,
        height_px,
        anchor_window=None,
        min_width=260,
        min_height=160,
        max_width_ratio=0.92,
        max_height_ratio=0.90,
    ):
        if window is None:
            return
        screen_width, screen_height = self._screen_size()
        anchor_rect = None
        virtual_root_rect = None
        if anchor_window is not None:
            try:
                anchor_window.update_idletasks()
                anchor_rect = (
                    int(anchor_window.winfo_x()),
                    int(anchor_window.winfo_y()),
                    max(1, int(anchor_window.winfo_width())),
                    max(1, int(anchor_window.winfo_height())),
                )
                virtual_root_rect = (
                    int(anchor_window.winfo_vrootx()),
                    int(anchor_window.winfo_vrooty()),
                    max(1, int(anchor_window.winfo_vrootwidth())),
                    max(1, int(anchor_window.winfo_vrootheight())),
                )
            except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
                anchor_rect = None
                virtual_root_rect = None

        geom = display_profile_core.compute_centered_toplevel_geometry(
            screen_width,
            screen_height,
            width_px,
            height_px,
            min_width=min_width,
            min_height=min_height,
            max_width_ratio=max_width_ratio,
            max_height_ratio=max_height_ratio,
            anchor_rect=anchor_rect,
            virtual_root_rect=virtual_root_rect,
        )
        try:
            window.minsize(int(geom["min_width"]), int(geom["min_height"]))
        except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
            pass
        try:
            window.geometry(
                f"{int(geom['width'])}x{int(geom['height'])}"
                f"+{int(geom['x'])}+{int(geom['y'])}"
            )
        except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
            pass

    def _build_ui(self): return ui_build_service.build_ui(self, tk=tk, ttk=ttk)

    def _safe_edit_undo(self, event=None):
        try:
            if getattr(self, "text", None):
                self.text.edit_undo()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        return "break"

    def _safe_edit_redo(self, event=None):
        try:
            if getattr(self, "text", None):
                self.text.edit_redo()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        return "break"

    def _build_editor_mode_toggle(self, parent): return ui_build_service.build_editor_mode_toggle(self, parent, tk=tk)

    def _build_input_mode_panel(self, parent, scroll_style):
        result = ui_build_service.build_input_mode_panel(self, parent, scroll_style, tk=tk, ttk=ttk)
        self._bind_input_mode_mousewheel()
        self._input_mode_panel_render_result = result
        return result

    def _bind_input_mode_mousewheel(self):
        # INPUT canvas should respond to wheel scrolling like JSON text view.
        if bool(getattr(self, "_input_mode_mousewheel_bound", False)):
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.bind_all("<MouseWheel>", self._on_input_mode_mousewheel, add="+")
            root.bind_all("<Button-4>", self._on_input_mode_mousewheel_linux_up, add="+")
            root.bind_all("<Button-5>", self._on_input_mode_mousewheel_linux_down, add="+")
            self._input_mode_mousewheel_bound = True
        except (tk.TclError, RuntimeError, AttributeError):
            self._input_mode_mousewheel_bound = False

    @staticmethod
    def _is_descendant_widget(widget, ancestor):
        current = widget
        while current is not None:
            if current == ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def _can_scroll_input_mode_canvas_for_event(self):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return False
        root = getattr(self, "root", None)
        canvas = getattr(self, "_input_mode_canvas", None)
        if root is None or canvas is None:
            return False
        try:
            if not canvas.winfo_exists():
                return False
            px, py = root.winfo_pointerxy()
            target = root.winfo_containing(px, py)
        except (tk.TclError, RuntimeError, TypeError, ValueError, AttributeError):
            return False
        if target is None:
            return False
        return self._is_descendant_widget(target, canvas)

    def _on_input_mode_mousewheel(self, event):
        if not self._can_scroll_input_mode_canvas_for_event():
            return
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is None:
            return
        try:
            delta = int(getattr(event, "delta", 0))
            if delta == 0:
                return "break"
            units = -1 if delta > 0 else 1
            canvas.yview_scroll(units, "units")
            self._maybe_render_more_router_rows(force_prefetch=True, origin="wheel")
            return "break"
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            return

    def _on_input_mode_mousewheel_linux_up(self, _event):
        if not self._can_scroll_input_mode_canvas_for_event():
            return
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_scroll(-1, "units")
            self._maybe_render_more_router_rows(force_prefetch=True, origin="wheel")
            return "break"
        except (tk.TclError, RuntimeError):
            return

    def _on_input_mode_mousewheel_linux_down(self, _event):
        if not self._can_scroll_input_mode_canvas_for_event():
            return
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview_scroll(1, "units")
            self._maybe_render_more_router_rows(force_prefetch=True, origin="wheel")
            return "break"
        except (tk.TclError, RuntimeError):
            return

    def _on_input_mode_canvas_scrollbar(self, *args):
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is None:
            return
        try:
            canvas.yview(*args)
        except (tk.TclError, RuntimeError, TypeError, ValueError):
            return
        return

    def _on_input_mode_scrollbar_release(self, _event=None):
        self._clear_input_mode_scroll_drag_active()
        self._schedule_router_settle_barrier(delay_ms=30)

    def _cancel_pending_input_mode_scroll_drag_clear(self):
        return ui_timer_service._cancel_pending_input_mode_scroll_drag_clear(**locals())

    def _clear_input_mode_scroll_drag_active(self):
        self._cancel_pending_input_mode_scroll_drag_clear()
        self._input_mode_scroll_drag_active = False

    def _mark_input_mode_scroll_drag_active(self):
        return ui_timer_service._mark_input_mode_scroll_drag_active(**locals())

    @staticmethod
    def _is_input_scalar(value): return input_mode_service.is_input_scalar(value)

    def _format_input_path_label(self, rel_path): return input_mode_service.format_input_path_label(rel_path)

    def _collect_input_field_specs(self, value, base_path, max_fields=24): return input_mode_service.collect_input_field_specs(
            value,
            base_path,
            max_fields=max_fields,
        )

    def _input_mode_font_size(self, base_size, min_size=7, max_size=18):
        # Keep INPUT rows synced with editor FONT +/- without breaking compact layouts.
        try:
            base = int(base_size)
        except (TypeError, ValueError):
            base = 9
        editor_size = max(6, min(32, int(round(float(getattr(self, "_font_size", 10) or 10)))))
        delta = editor_size - 10
        scaled = base + delta
        return max(int(min_size), min(int(max_size), int(scaled)))

    def _is_bank_input_style_path(self, path):
        return input_mode_service._is_bank_input_style_path(**locals())

    def _collect_bank_input_rows(self, value, max_rows=40): return input_bank_style_service.collect_bank_input_rows(value, max_rows=max_rows)

    def _render_bank_input_style_rows(self, host, normalized_path, row_defs):
        return input_mode_service._render_bank_input_style_rows(**locals())

    @staticmethod
    def _is_database_input_style_path(path): return input_mode_render_dispatch_service.is_database_input_style_path(path)

    def _database_root_entry_label(self, idx, item): return label_format_service.database_root_entry_label(
            idx,
            item,
            tree_style_variant=getattr(self, "_tree_style_variant", "B"),
            editor_mode=getattr(self, "_editor_mode", "JSON"),
        )

    def _collect_database_grades_matrix(self, value, max_rows=40): return input_mode_service.collect_database_grades_matrix(
            value,
            max_rows=max_rows,
            input_database_style_service=input_database_style_service,
        )

    def _render_database_grades_input_matrix(self, host, normalized_path, matrix_payload):
        return input_mode_service._render_database_grades_input_matrix(**locals())

    def _collect_database_bcc_payload(self, value, max_rows=200): return input_mode_service.collect_database_bcc_payload(
            value,
            max_rows=max_rows,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )

    def _render_database_bcc_table(self, host, normalized_path, payload):
        return input_mode_service._render_database_bcc_table(**locals())

    def _collect_database_interpol_payload(self, value, max_rows=200): return input_mode_service.collect_database_interpol_payload(
            value,
            max_rows=max_rows,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )

    def _render_database_interpol_table(self, host, normalized_path, payload):
        return input_mode_service._render_database_interpol_table(**locals())

    def _database_grades_matrix_for_input_path(self, path, value): return input_mode_service.database_grades_matrix_for_input_path(
            path,
            value,
            input_database_style_service=input_database_style_service,
        )

    def _database_bcc_payload_for_input_path(self, path, value): return input_mode_service.database_bcc_payload_for_input_path(
            path,
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )

    def _database_interpol_payload_for_input_path(self, path, value): return input_mode_service.database_interpol_payload_for_input_path(
            path,
            value,
            input_database_bcc_style_service=input_database_bcc_style_service,
        )

    def _is_network_router_input_style_payload(self, path, value): return input_mode_service.is_network_router_input_style_payload(
            self,
            path,
            value,
            input_network_router_style_service=input_network_router_style_service,
        )

    def _is_suspicion_input_style_path(self, path): return input_suspicion_phone_style_service.is_suspicion_input_path(self, path)

    def _is_phone_input_style_path(self, path): return input_suspicion_phone_style_service.is_phone_input_path(self, path)

    def _is_skypersky_input_style_path(self, path): return input_suspicion_phone_style_service.is_skypersky_input_path(self, path)

    def _render_suspicion_phone_input(self, host, normalized_path, value): return input_suspicion_phone_style_service.render_suspicion_phone_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _render_phone_preview_input(self, host, normalized_path, value): return input_suspicion_phone_style_service.render_phone_preview_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _render_skypersky_input(self, host, normalized_path, value): return input_suspicion_phone_style_service.render_skypersky_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _is_network_device_input_style_payload(self, path, value): return input_mode_service.is_network_device_input_style_payload(self, path, value)

    def _is_network_firewall_input_style_payload(self, path, value): return input_mode_service.is_network_firewall_input_style_payload(
            self,
            path,
            value,
            input_network_firewall_style_service=input_network_firewall_style_service,
        )

    def _is_network_geoip_input_style_payload(self, path, value):
        # GEO IP concept applies only to first Network DEVICE row.
        return input_mode_service.is_network_geoip_input_style_payload(
            self,
            path,
            value,
            input_network_device_geoip_style_service=input_network_device_geoip_style_service,
        )

    def _is_network_bcc_domains_input_style_payload(self, path, value):
        # BCC DOMAINS concept applies only to the locked bcc.com row.
        return input_mode_service.is_network_bcc_domains_input_style_payload(
            self,
            path,
            value,
            input_network_device_bcc_style_service=input_network_device_bcc_style_service,
        )

    def _collect_network_bcc_domains_payload(self, normalized_path, value): return input_network_device_bcc_style_service.collect_bcc_domains_payload(self, normalized_path, value)

    def _render_network_bcc_domains_input(self, host, normalized_path, payload):
        return input_mode_service._render_network_bcc_domains_input(**locals())

    def _is_network_blue_table_input_style_payload(self, path, value):
        # BLUE TABLE concept applies to the locked thebluetable.com anchor row.
        return input_mode_service.is_network_blue_table_input_style_payload(
            self,
            path,
            value,
            input_network_device_bcc_style_service=input_network_device_bcc_style_service,
        )

    def _collect_network_blue_table_payload(self, normalized_path, value): return input_network_device_bcc_style_service.collect_blue_table_payload(self, normalized_path, value)

    def _render_network_blue_table_input(self, host, normalized_path, payload):
        return input_mode_service._render_network_blue_table_input(**locals())

    def _is_network_interpol_input_style_payload(self, path, value):
        # INTERPOL concept applies to the locked row directly under BLUE TABLE.
        return input_mode_service.is_network_interpol_input_style_payload(
            self,
            path,
            value,
            input_network_device_bcc_style_service=input_network_device_bcc_style_service,
        )

    def _collect_network_interpol_payload(self, normalized_path, value): return input_network_device_bcc_style_service.collect_interpol_payload(self, normalized_path, value)

    def _render_network_interpol_input(self, host, normalized_path, payload):
        return input_mode_service._render_network_interpol_input(**locals())

    def _collect_network_geoip_payload(self, normalized_path, value): return input_network_device_geoip_style_service.collect_geoip_payload(self, normalized_path, value)

    def _render_network_geoip_input(self, host, normalized_path, payload):
        return input_mode_service._render_network_geoip_input(**locals())

    def _collect_network_firewall_input_rows(self, normalized_path, firewalls, max_rows=40): return input_network_firewall_style_service.collect_firewall_input_rows(
            self,
            normalized_path,
            firewalls,
            max_rows=max_rows,
        )

    def _render_network_firewall_input_rows(self, host, normalized_path, row_defs):
        return input_mode_service._render_network_firewall_input_rows(**locals())

    def _collect_network_router_input_rows(self, normalized_path, routers, max_rows=60): return input_network_router_style_service.collect_router_input_rows(
            self,
            normalized_path,
            routers,
            max_rows=max_rows,
        )

    def _render_network_router_input_rows(
        self,
        host,
        normalized_path,
        row_defs,
        *,
        start_index=0,
        finalize=False,
        total_rows=None,
    ):
        return input_mode_service._render_network_router_input_rows(**locals())

    def _prewarm_input_mode_assets(self):
        try:
            input_network_router_style_service.prewarm_router_assets(self)
            input_suspicion_phone_style_service.prewarm_preview_assets(self)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return

    def _refresh_input_mode_fields(self, path, value): return input_mode_render_dispatch_service.refresh_input_mode_fields(
            self,
            path,
            value,
            tk_module=tk,
            input_database_style_service=input_database_style_service,
            input_mode_service=input_mode_service,
            input_network_router_style_service=input_network_router_style_service,
        )

    def _input_mode_path_key(self, path):
        if isinstance(path, list):
            return tuple(self._input_mode_path_key(token) for token in path)
        if isinstance(path, tuple):
            return tuple(self._input_mode_path_key(token) for token in path)
        return path

    def _refresh_input_mode_bool_widget_colors(self):
        # Keep INPUT boolean visuals deterministic across renderer/type variations.
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        palette = theme_service.input_bool_value_palette(variant)
        bool_true_fg = palette["true_fg"]
        bool_false_fg = palette["false_fg"]
        specs = list(getattr(self, "_input_mode_field_specs", []) or [])
        for spec in specs:
            widget = spec.get("widget")
            var = spec.get("var")
            if widget is None or var is None:
                continue
            try:
                token = str(var.get() or "").strip().lower()
            except (tk.TclError, RuntimeError, TypeError, ValueError):
                continue
            if token not in ("true", "false"):
                continue
            value_fg = bool_true_fg if token == "true" else bool_false_fg
            try:
                widget.configure(fg=value_fg, insertbackground=value_fg)
            except (tk.TclError, RuntimeError, AttributeError):
                continue

    def _can_skip_input_mode_refresh(self, item_id, target_path): return editor_mode_switch_service.can_skip_input_mode_refresh(self, item_id, target_path)

    def _cancel_pending_input_mode_refresh(self):
        return ui_timer_service._cancel_pending_input_mode_refresh(**locals())

    def _cancel_pending_input_mode_layout_finalize(self):
        return ui_timer_service._cancel_pending_input_mode_layout_finalize(**locals())

    def _run_input_mode_layout_finalize(self):
        return ui_timer_service._run_input_mode_layout_finalize(**locals())

    def _schedule_input_mode_layout_finalize(self, reset_scroll=False):
        return ui_timer_service._schedule_input_mode_layout_finalize(**locals())

    def _cancel_pending_router_input_batches(self):
        return ui_timer_service._cancel_pending_router_input_batches(**locals())

    def _cancel_pending_router_input_prewarm(self):
        return ui_timer_service._cancel_pending_router_input_prewarm(**locals())

    def _run_router_input_prewarm(self):
        return input_mode_service._run_router_input_prewarm(**locals())

    def _schedule_router_input_prewarm(self):
        return input_mode_service._schedule_router_input_prewarm(**locals())

    def _cancel_pending_router_virtual_check(self):
        return ui_timer_service._cancel_pending_router_virtual_check(**locals())

    def _clear_router_virtual_state(self):
        self._cancel_pending_router_virtual_check()
        self._cancel_pending_router_settle_barrier()
        self._clear_input_mode_scroll_drag_active()
        self._input_mode_router_virtual_rows = []
        self._input_mode_router_virtual_next_index = 0
        self._input_mode_router_virtual_total_rows = 0

    def _schedule_router_virtual_check(self, delay_ms=30):
        return ui_timer_service._schedule_router_virtual_check(**locals())

    def _cancel_pending_router_settle_barrier(self):
        return ui_timer_service._cancel_pending_router_settle_barrier(**locals())

    def _schedule_router_settle_barrier(self, delay_ms=24):
        return ui_timer_service._schedule_router_settle_barrier(**locals())

    def _run_router_settle_barrier(self):
        return input_mode_service._run_router_settle_barrier(**locals())

    def _router_virtual_backlog(self):
        next_index = int(getattr(self, "_input_mode_router_virtual_next_index", 0) or 0)
        total_rows = int(getattr(self, "_input_mode_router_virtual_total_rows", 0) or 0)
        return max(0, total_rows - next_index)

    def _router_virtual_prefetch_threshold(self, force_prefetch=False):
        if bool(force_prefetch) or bool(getattr(self, "_input_mode_scroll_drag_active", False)):
            return 0.45
        return 0.72

    def _router_virtual_chunk_size(self, backlog):
        pending = max(0, int(backlog or 0))
        if bool(getattr(self, "_input_mode_scroll_drag_active", False)):
            if pending > 24:
                return 14
            return 10
        if pending > 32:
            return 14
        if pending > 16:
            return 10
        return 8

    def _maybe_render_more_router_rows(self, force_prefetch=False, origin="idle"):
        return input_mode_service._maybe_render_more_router_rows(**locals())

    def _schedule_router_input_render_batches(
        self,
        host,
        normalized_path,
        pending_rows,
        render_token,
        chunk_size=10,
        start_index=0,
        total_rows=None,
    ):
        return input_mode_service._schedule_router_input_render_batches(**locals())

    def _resolve_input_mode_selection_payload(self, item_id):
        if not item_id:
            return [], {}, ""
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            _, list_path, group = path
            value = self._get_value(list_path)
            group_items = input_mode_service.collect_group_items_for_selection(self, list_path, value, group)
            return list_path, group_items, f"group {group} ({len(group_items)})"
        try:
            value = self._get_value(path)
        except (KeyError, IndexError, TypeError, ValueError):
            value = {}
        return path, value, self._describe(value)

    def _run_pending_input_mode_refresh(self):
        return ui_timer_service._run_pending_input_mode_refresh(**locals())

    def _schedule_input_mode_refresh(self, item_id=None, immediate=False):
        return ui_timer_service._schedule_input_mode_refresh(**locals())

    def _mark_tree_interaction_active(self): return ui_timer_service.mark_tree_interaction_active(self)

    def _refresh_editor_mode_view(self):
        # Regression contract marker: self._enforce_input_tree_expand_locks()
        return input_mode_service._refresh_editor_mode_view(**locals())

    def _sync_input_mode_paned_sash_lock(self, mode=None): return input_mode_paned_lock_service.sync_input_mode_paned_sash_lock(
            self,
            mode=mode,
            tk_module=tk,
        )

    def _repair_input_mode_tree_pane_mapping(self): return input_mode_paned_lock_service.repair_input_mode_tree_pane_mapping(
            self,
            tk_module=tk,
        )

    def _cancel_input_mode_paned_lock_recheck(self): return input_mode_paned_lock_service.cancel_input_mode_paned_lock_recheck(
            self,
            tk_module=tk,
        )

    def _schedule_input_mode_paned_lock_recheck(self, delay_ms=72): return input_mode_paned_lock_service.schedule_input_mode_paned_lock_recheck(
            self,
            delay_ms=delay_ms,
            tk_module=tk,
        )

    def _apply_tree_mode_style(self, mode=None): return editor_purge_service._apply_tree_mode_style(self, mode)

    def _show_json_no_file_message(self): return editor_purge_service._show_json_no_file_message(self)

    @staticmethod
    def _set_nested_value(container, rel_path, new_value): return input_mode_service.set_nested_value(container, rel_path, new_value)

    def _clear_input_group_selection_cache(self): return input_mode_service.clear_group_selection_cache(self)

    @staticmethod
    def _strip_input_display_prefix(raw): return input_mode_service.strip_input_display_prefix(raw)

    def _coerce_input_field_value(self, spec): return input_mode_service.coerce_input_field_value(spec)

    def _apply_input_edit(self): return editor_purge_service._apply_input_edit(self)

    def _input_mode_root_key_for_path(self, path):
        normalized = list(path or [])
        if not normalized:
            return ""
        root = normalized[0]
        return self._normalize_root_tree_key(root)

    def _hidden_root_tree_keys_for_mode(self, mode=None): return tree_policy_service.hidden_root_keys_for_mode(self, mode)

    def _is_input_mode_category_disabled(self, path): return tree_policy_service.is_input_mode_root_disabled(self, path)

    def _is_input_tree_expand_blocked(self, item_id):
        # INPUT-only gate: keep configured root categories collapsed in tree mode.
        return tree_policy_service.is_input_mode_tree_expand_blocked(self, item_id)

    def _editor_mode_tab_photo(self, active=False):
        return ui_factory_service.editor_mode_tab_photo(
            self,
            active=active,
            importlib_module=importlib,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _set_editor_mode(self, mode):
        mode = str(mode).upper()
        if mode not in ("INPUT", "JSON"):
            return
        previous_mode = str(getattr(self, "_editor_mode", "JSON")).upper()
        self._editor_mode = mode
        if mode == "INPUT":
            self._input_mode_force_refresh = True
        if mode != previous_mode and self._mode_switch_requires_tree_rebuild(previous_mode, mode):
            self._rebuild_tree_for_mode_change()
        self._update_editor_mode_controls()
        self._update_find_controls_for_mode()
        self._refresh_editor_mode_view()
        if mode == "JSON":
            try:
                self.on_select(None)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass

    def _update_find_controls_for_mode(self):
        # Keep find field visual style unchanged across modes; behavior gating
        # is enforced in find_next() and context checks.
        entry = getattr(self, "find_entry", None)
        if entry is not None:
            try:
                if entry.winfo_exists():
                    entry.configure(state="normal")
            except (tk.TclError, RuntimeError, AttributeError):
                pass

    def _update_editor_mode_controls(self):
        return ui_factory_service.update_editor_mode_controls(
            self,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _mode_switch_requires_tree_rebuild(self, previous_mode, next_mode): return editor_mode_switch_service.mode_switch_requires_tree_rebuild(self, previous_mode, next_mode)

    def _refresh_input_mode_theme_widgets(self):
        # Regression contract marker: _resolve_input_mode_selection_payload(item_id)
        return VISUALS._refresh_input_mode_theme_widgets(**locals())

    def _reset_toolbar_runtime_refs(self):
        self._toolbar_buttons = {}
        self._toolbar_button_text = {}
        self._font_stepper_label = None
        self._font_size_value_label = None
        self._font_control_host = None
        self._toolbar_center_frame = None
        self._toolbar_layout_mode = None
        self._find_host_default_padx = None
        self._find_button_default_padx = None
        self._find_entry_width_override = None
        self._find_entry_host = None
        self._find_entry_slot = None
        self._find_entry_edge_line = None
        self._find_entry_inner_edge_line = None
        self.find_entry = None
        self.font_size_combo = None
        self.font_size_var = None

    def _rebuild_toolbar(self, preserve_find_text=True):
        host = getattr(self, "_toolbar_host", None)
        if host is None or not host.winfo_exists():
            return
        find_query = ""
        if preserve_find_text and self.find_entry and self.find_entry.winfo_exists():
            try:
                find_query = self.find_entry.get()
            except (tk.TclError, RuntimeError, AttributeError):
                find_query = ""

        for child in host.winfo_children():
            child.destroy()
        self._reset_toolbar_runtime_refs()
        theme = getattr(self, "_theme", {}) or {}
        center_frame = tk.Frame(
            host,
            bg=theme.get("bg", "#0f131a"),
            bd=0,
            highlightthickness=0,
        )
        center_frame.pack(anchor="center")
        self._toolbar_center_frame = center_frame

        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        style = self._siindbad_effective_style()
        if variant == "KAMUE":
            if style == "A":
                self._load_toolbar_button_images()
            else:
                self._toolbar_button_images = {}
            self._build_kamue_toolbar(center_frame)
        else:
            self._toolbar_button_images = {}
            self._build_siindbad_toolbar(center_frame)

        if find_query and self.find_entry and self.find_entry.winfo_exists():
            try:
                self.find_entry.insert(0, find_query)
                self.find_entry.icursor("end")
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        self._update_find_controls_for_mode()
        self._update_find_entry_layout()
        self._schedule_topbar_alignment(delay_ms=0)

    def _build_siindbad_toolbar(self, top):
        self._build_toolbar_structure(top, inter_button_pad=2)

    def _build_kamue_toolbar(self, top):
        style = self._siindbad_effective_style()
        self._build_toolbar_structure(top, inter_button_pad=(3 if style == "A" else 2))

    def _build_toolbar_structure(self, top, inter_button_pad): return toolbar_service._build_toolbar_structure(self, top, inter_button_pad)

    @staticmethod
    def _pack_toolbar_control(control, **pack_kwargs):
        host = getattr(control, "_siindbad_frame_host", control)
        host.pack(**pack_kwargs)

    def check_for_updates_auto(self):
        self._check_for_updates(auto=True)

    def _run_check_for_updates_auto(self):
        return ui_timer_service._run_check_for_updates_auto(**locals())

    def _schedule_auto_update_check(self, delay_ms=500):
        return ui_timer_service._schedule_auto_update_check(**locals())

    def _auto_update_startup_enabled(self):
        # Startup auto-update toggle:
        # - env override HACKHUB_AUTO_UPDATE_STARTUP=0/1 always wins
        # - otherwise use saved dialog preference (default off)
        raw = str(os.environ.get("HACKHUB_AUTO_UPDATE_STARTUP", "")).strip().lower()
        if raw in ("1", "true", "yes", "on"):
            return True
        if raw in ("0", "false", "no", "off"):
            return False
        return bool(getattr(self, "_startup_update_check_enabled", False))

    def check_for_updates_manual(self):
        self._check_for_updates(auto=False)

    def _cancel_scheduled_after_callbacks(self):
        return ui_timer_service._cancel_scheduled_after_callbacks(**locals())

    def _on_root_destroy(self, event):
        if getattr(self, "_shutdown_cleanup_done", False):
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        if getattr(event, "widget", None) is not root:
            return
        self._shutdown_cleanup_done = True
        self._close_bug_report_dialog()
        self._destroy_text_context_menu()
        self._destroy_input_context_menu()
        self._cancel_scheduled_after_callbacks()
        self._active_document_load_request_id = 0
        self._document_load_depth = 0
        self._document_load_in_progress = False
        self._document_load_async_result = None
        # Enforce diagnostics day-file retention on app shutdown.
        self._purge_diag_logs_for_new_session()

    def _show_themed_update_info(self, title, message, include_startup_toggle=False): return editor_purge_service._show_themed_update_info(self, title, message, include_startup_toggle)

    def _ask_themed_update_confirm(self, title, message, include_startup_toggle=False):
        startup_state = None
        startup_callback = None
        if bool(include_startup_toggle):
            startup_state = bool(getattr(self, "_startup_update_check_enabled", False))
            startup_callback = self._set_startup_update_check_enabled
        return update_ui_service.show_themed_update_confirm(
            self,
            title,
            message,
            tk=tk,
            messagebox=messagebox,
            startup_check_state=startup_state,
            on_startup_check_change=startup_callback,
        )

    def _update_ui_demo_enabled(self):
        # Update UI demo toggle: set HACKHUB_UPDATE_UI_DEMO=1 to preview staged updater UX with no install.
        raw = str(os.environ.get("HACKHUB_UPDATE_UI_DEMO", "0")).strip().lower()
        return raw in ("1", "true", "yes", "on")

    def _set_startup_update_check_enabled(self, enabled):
        self._startup_update_check_enabled = bool(enabled)
        try:
            self._save_user_settings()
        except _EXPECTED_APP_ERRORS:
            self._set_status("Could not save startup update preference.")

    def _run_update_ui_demo(self, auto=False, sleep_fn=time.sleep): return update_orchestrator_service.run_update_ui_demo(
            self,
            auto=auto,
            sleep_fn=sleep_fn,
        )

    def _check_for_updates(self, auto=False): return update_orchestrator_service.check_for_updates(
            self,
            auto=auto,
            messagebox=messagebox,
        )

    def _ui_call(self, callback, *args, wait=False, default=None, timeout=15.0, **kwargs): return ui_dispatch_service.ui_call(
            self,
            callback,
            *args,
            wait=wait,
            default=default,
            timeout=timeout,
            expected_errors=_EXPECTED_APP_ERRORS,
            **kwargs,
        )

    @staticmethod
    def _walk_exception_chain(exc, max_depth=8):
        yield from update_service.walk_exception_chain(exc, max_depth=max_depth)

    def _format_update_error(self, exc): return update_service.format_update_error(exc)

    def _manual_update_download_url(self):
        # Manual fallback should use public GitHub Releases, not raw dist branch files.
        return update_url_service.manual_update_download_url(self)

    def _offer_manual_update_fallback(self, pretty_error): return update_fallback_service.offer_manual_update_fallback(
            self,
            pretty_error,
            askyesno_fn=messagebox.askyesno,
            no_value=messagebox.NO,
            open_url_fn=webbrowser.open,
        )

    def _log_update_failure(self, exc, auto=False, pretty_error=""):
        update_diag_service.log_update_failure(
            self,
            exc,
            auto=auto,
            pretty_error=pretty_error,
        )

    def _fetch_dist_version(self): return update_version_service.fetch_dist_version(self)

    def _download_dist_asset(self): return update_asset_service.download_dist_asset(self)

    @staticmethod
    def _parse_retry_after_seconds(value): return update_service.parse_retry_after_seconds(value)

    @staticmethod
    def _is_retryable_download_error(exc): return update_service.is_retryable_download_error(exc)

    @staticmethod
    def _download_backoff_delay(exc, attempt_index, base_delay=0.45, max_delay=12.0): return update_service.download_backoff_delay(
            exc,
            attempt_index,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    def _verify_downloaded_update_signature(self, path): return update_signature_service.verify_downloaded_update_signature(
            self,
            path,
            subprocess_module=subprocess,
            json_module=json,
            os_module=os,
            sys_module=sys,
        )

    @staticmethod
    def _extract_sha256_from_text(text, asset_name): return update_checksum_service.extract_sha256_from_text(text, asset_name)

    def _fetch_dist_asset_sha256(self, release_info=None): return update_checksum_service.fetch_dist_asset_sha256(self, release_info=release_info)

    def _latest_release_api_url(self): return update_url_service.latest_release_api_url(self)

    def _fetch_latest_release_info(self): return editor_purge_service._fetch_latest_release_info(self)

    @staticmethod
    def _release_asset_download_url(release_info, asset_name): return update_url_service.release_asset_download_url(release_info, asset_name)

    def _download_bytes_with_retries(self, url, attempts=3, timeout=60): return update_download_service.download_bytes_with_retries(
            self,
            url=url,
            attempts=attempts,
            timeout=timeout,
        )

    def _download_to_file_with_retries(
        self,
        url,
        out_path,
        attempts=3,
        timeout=60,
        chunk_size=1024 * 1024,
    ):
        return update_download_service.download_to_file_with_retries(
            self,
            url=url,
            out_path=out_path,
            attempts=attempts,
            timeout=timeout,
            chunk_size=chunk_size,
        )

    def _ps_escape(self, value): return windows_runtime_service.ps_escape(value)

    @staticmethod
    def _is_retryable_file_write_error(exc): return windows_runtime_service.is_retryable_file_write_error(exc, platform_name=sys.platform)

    def _write_text_file_atomic(
        self,
        path,
        text,
        encoding="utf-8",
        retries=5,
        base_delay=0.08,
    ):
        return windows_runtime_service.write_text_file_atomic(
            path=path,
            text=text,
            encoding=encoding,
            retries=retries,
            base_delay=base_delay,
            is_retryable_fn=self._is_retryable_file_write_error,
            sleep_fn=time.sleep,
        )

    def _read_json_file(self, path, encoding="utf-8"): return windows_runtime_service.read_json_file(path=path, encoding=encoding)

    def _commit_file_to_destination_with_retries(
        self,
        source_path,
        target_path,
        retries=5,
        base_delay=0.08,
    ):
        return windows_runtime_service.commit_file_to_destination_with_retries(
            source_path=source_path,
            target_path=target_path,
            retries=retries,
            base_delay=base_delay,
            is_retryable_fn=self._is_retryable_file_write_error,
            sleep_fn=time.sleep,
        )

    def _start_hidden_process(self, args): return windows_runtime_service.start_hidden_process(args, subprocess_module=subprocess)

    def _install_update(self, new_path): return editor_purge_service._install_update(self, new_path)

    def _show_update_overlay(self, message):
        update_ui_service.show_update_overlay(self, message, tk=tk, ttk=ttk)

    def _update_update_overlay(self, message=None, stage=None, percent=None, pulse=False):
        return ui_timer_service._update_update_overlay(**locals())

    def _close_update_overlay(self):
        update_ui_service.close_update_overlay(self)

    def _release_version(self, version): return version_format_service.release_version(version)

    def _format_version(self, version_tuple): return version_format_service.format_version(version_tuple)

    def _dist_url(self, filename):
        # Use latest GitHub release assets to avoid mutable branch dist trust.
        return update_url_service.dist_url(self, filename)

    @staticmethod
    def _resolve_token_from_env_names(*env_names): return token_env_service.resolve_token_from_env_names(*env_names)

    def _update_token_value(self): return token_env_service.update_token_value(self)

    def _bug_report_token_env_name(self): return token_env_service.bug_report_token_env_name(self)

    def _has_bug_report_token(self): return token_env_service.has_bug_report_token(self)

    def _download_headers(self):
        token = JsonEditor._update_token_value(self)
        return update_headers_service.download_headers(token)

    def _set_status(self, text):
        return ui_timer_service._set_status(**locals())

    def _selected_tree_path_text(self): return editor_purge_service._selected_tree_path_text(self)

    def _diag_log_path(self):
        if not bool(getattr(self, "DIAG_LOG_ENABLED", True)):
            return ""
        return diag_log_housekeeping_service.build_dated_diag_log_path(
            runtime_dir=self._runtime_data_dir(create=True),
            diag_log_filename=self.DIAG_LOG_FILENAME,
        )

    def _purge_diag_logs_for_new_session(self):
        if not bool(getattr(self, "DIAG_LOG_ENABLED", True)):
            return
        diag_log_housekeeping_service.purge_diag_logs_for_new_session(
            runtime_dir=self._runtime_data_dir(create=True),
            diag_log_filename=self.DIAG_LOG_FILENAME,
            legacy_diag_log_filenames=self.LEGACY_DIAG_LOG_FILENAMES,
            keep_days=getattr(self, "DIAG_LOG_KEEP_DAYS", 2),
            temp_dir=tempfile.gettempdir(),
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _runtime_data_dir(self, create=False): return runtime_paths_service.runtime_data_dir(
            runtime_dir_name=self.RUNTIME_DIR_NAME,
            create=create,
            platform_name=sys.platform,
            env=os.environ,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _crash_log_path(self): return crash_report_service.build_crash_log_path(
            runtime_dir=self._runtime_data_dir(create=True),
            crash_log_filename=self.CRASH_LOG_FILENAME,
        )

    def _crash_state_path(self): return crash_report_service.build_crash_state_path(
            runtime_dir=self._runtime_data_dir(create=True),
            crash_state_filename=self.CRASH_STATE_FILENAME,
        )

    def _read_crash_log_tail(self, max_chars=None): return crash_report_service.read_crash_log_tail(
            path=self._crash_log_path(),
            default_limit=self.CRASH_LOG_TAIL_MAX_CHARS,
            max_chars=max_chars,
            read_text_file_tail=runtime_log_service.read_text_file_tail,
        )

    def _read_latest_crash_block(self, max_chars=None): return crash_report_service.read_latest_crash_block(
            read_crash_log_tail_func=self._read_crash_log_tail,
            default_limit=self.CRASH_LOG_TAIL_MAX_CHARS,
            max_chars=max_chars,
            read_latest_block=runtime_log_service.read_latest_block,
            marker="\n---\n",
        )

    def _read_crash_prompt_state(self): return crash_report_service.read_crash_prompt_state(
            path=self._crash_state_path(),
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _write_crash_prompt_state(self, crash_hash):
        crash_report_service.write_crash_prompt_state(
            path=self._crash_state_path(),
            crash_hash=crash_hash,
            write_text_file_atomic=self._write_text_file_atomic,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _pending_crash_report_payload(self): return crash_report_service.pending_crash_report_payload(
            log_path=self._crash_log_path(),
            read_latest_crash_block_func=self._read_latest_crash_block,
            read_crash_prompt_state_func=self._read_crash_prompt_state,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _schedule_crash_report_offer(self, delay_ms=450):
        # Regression contract marker: crash_offer_service.schedule_crash_report_offer(
        return ui_timer_service._schedule_crash_report_offer(**locals())

    def _offer_crash_report_if_available(self): return editor_purge_service._offer_crash_report_if_available(self)

    def _startup_phase_for_crash_log(self):
        return ui_timer_service._startup_phase_for_crash_log(**locals())

    def _crash_input_context_fields(self):
        selected_path = ""
        try:
            selected_path = self._selected_tree_path_text()
        except _EXPECTED_APP_ERRORS:
            selected_path = ""
        selected_path = str(selected_path or "").strip()
        selected_hash = ""
        selected_depth = 0
        if selected_path:
            selected_hash = hashlib.sha256(selected_path.encode("utf-8", errors="replace")).hexdigest()[:16]
            selected_depth = max(1, selected_path.count(".") + selected_path.count("[") + 1)

        focus_widget = ""
        root = getattr(self, "root", None)
        if root is not None:
            try:
                focused = root.focus_get()
                if focused is not None:
                    focus_widget = str(focused.winfo_class() or "")
            except _EXPECTED_APP_ERRORS:
                focus_widget = ""

        text_len = 0
        text_widget = getattr(self, "text", None)
        if text_widget is not None:
            try:
                text_len = len(str(text_widget.get("1.0", "end-1c") or ""))
            except _EXPECTED_APP_ERRORS:
                text_len = 0

        return {
            "selected_path_hash": selected_hash,
            "selected_path_depth": selected_depth,
            "focused_widget": focus_widget,
            "input_field_specs_count": len(list(getattr(self, "_input_mode_field_specs", []) or [])),
            "json_text_len": int(text_len),
        }

    def _crash_log_extra_fields(self, context):
        started = float(getattr(self, "_session_started_monotonic", 0.0) or 0.0)
        uptime_ms = 0
        if started > 0:
            uptime_ms = max(0, int((time.monotonic() - started) * 1000.0))
        callback_origin = str(context or getattr(self, "_last_callback_origin", "")).strip()
        return {
            "crash_id": f"{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}",
            "session_id": str(getattr(self, "_session_id", "")),
            "uptime_ms": uptime_ms,
            "startup_phase": self._startup_phase_for_crash_log(),
            "callback_origin": callback_origin,
            "diag_action": str(getattr(self, "_diag_action", "")),
            "editor_mode": str(getattr(self, "_editor_mode", "")),
            "theme_variant": str(getattr(self, "_app_theme_variant", "")),
            "error_note": str(getattr(self, "_last_error_highlight_note", "")),
            "last_error_msg_len": len(str(getattr(self, "_last_json_error_msg", "") or "")),
            **self._crash_input_context_fields(),
        }

    def _append_crash_log(self, context, exc_type, exc_value, exc_tb):
        crash_logging_service.append_crash_log(
            path=self._crash_log_path(),
            trim_text_file_for_append=self._trim_text_file_for_append,
            max_bytes=self.DIAG_LOG_MAX_BYTES,
            keep_bytes=self.DIAG_LOG_KEEP_BYTES,
            app_version=self.APP_VERSION,
            context=context,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            expected_errors=_EXPECTED_APP_ERRORS,
            extra_fields=self._crash_log_extra_fields(context),
        )

    def _show_crash_notice_once(self):
        self._crash_notice_shown = crash_logging_service.show_crash_notice_once(
            crash_notice_shown=self._crash_notice_shown,
            crash_path=self._crash_log_path(),
            ui_call=self._ui_call,
            showerror_func=messagebox.showerror,
        )

    def _handle_unhandled_exception(self, context, exc_type, exc_value, exc_tb):
        error_hook_service.handle_unhandled_exception(
            append_crash_log_fn=self._append_crash_log,
            show_crash_notice_once_fn=self._show_crash_notice_once,
            context=context,
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
        )

    def _handle_sys_excepthook(self, exc_type, exc_value, exc_tb):
        self._last_callback_origin = "sys.excepthook"
        return editor_purge_service._handle_sys_excepthook(self, exc_type, exc_value, exc_tb)

    def _handle_threading_excepthook(self, args):
        self._last_callback_origin = "threading.excepthook"
        return editor_purge_service._handle_threading_excepthook(self, args)

    def _handle_tk_callback_exception(self, exc_type, exc_value, exc_tb):
        self._last_callback_origin = "tk.report_callback_exception"
        self._handle_unhandled_exception("tk.report_callback_exception", exc_type, exc_value, exc_tb)

    def _install_global_error_hooks(self):
        error_hook_service.install_global_error_hooks(
            owner=self,
            sys_module=sys,
            threading_module=threading,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _read_diag_log_tail(self, max_chars=8000): return editor_purge_service._read_diag_log_tail(self, max_chars)

    def _open_bug_report_dialog(
        self,
        summary_prefill="",
        details_prefill="",
        include_diag_default=True,
        crash_tail="",
    ):
        return bug_report_manager.trigger_report_flow(
            self,
            tk=tk,
            filedialog=filedialog,
            messagebox=messagebox,
            threading_module=threading,
            time_module=time,
            platform_module=platform,
            os_module=os,
            summary_prefill=summary_prefill,
            details_prefill=details_prefill,
            include_diag_default=include_diag_default,
            crash_tail=crash_tail,
        )

    def _close_bug_report_dialog(self):
        dlg = getattr(self, "_bug_report_dialog", None)
        self._bug_report_follow_root = False
        self._bug_report_is_dragging = False
        root = getattr(self, "root", None)
        if dlg is not None:
            try:
                if dlg.winfo_exists():
                    try:
                        dlg.grab_release()
                    except _EXPECTED_APP_ERRORS:
                        pass
                    try:
                        dlg.destroy()
                    except _EXPECTED_APP_ERRORS:
                        pass
            except _EXPECTED_APP_ERRORS:
                pass
        if root is not None:
            try:
                current = root.grab_current()
            except _EXPECTED_APP_ERRORS:
                current = None
            if current is not None:
                try:
                    current.grab_release()
                except _EXPECTED_APP_ERRORS:
                    pass

    def _hide_bug_submit_splash(self):
        return ui_timer_service._hide_bug_submit_splash(**locals())

    def _show_bug_submit_splash(self, message="BUG REPORT SUBMITTED", duration_ms=1600):
        ui_factory_service.show_bug_submit_splash(
            self,
            message=message,
            duration_ms=duration_ms,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _bug_report_header_pulse_palette(self):
        return ui_timer_service._bug_report_header_pulse_palette(**locals())

    def _start_bug_report_header_pulse(self):
        return ui_timer_service._start_bug_report_header_pulse(**locals())

    def _stop_bug_report_header_pulse(self):
        return ui_timer_service._stop_bug_report_header_pulse(**locals())

    def _tick_bug_report_header_pulse(self):
        return ui_timer_service._tick_bug_report_header_pulse(**locals())

    def _activate_bug_report_custom_chrome(self, dialog, header=None, drag_widgets=(), close_widget=None):
        return ui_timer_service._activate_bug_report_custom_chrome(**locals())

    def _trim_text_file_for_append(self, path, max_bytes, keep_bytes):
        if not os.path.isfile(path):
            return
        if max_bytes <= 0 or keep_bytes <= 0:
            return
        try:
            size = os.path.getsize(path)
        except _EXPECTED_APP_ERRORS:
            return
        if size <= max_bytes:
            return
        keep_bytes = min(int(keep_bytes), int(size))
        try:
            with open(path, "rb") as src:
                src.seek(size - keep_bytes)
                tail = src.read()
            with open(path, "wb") as dst:
                dst.write(b"\n--- log truncated ---\n")
                dst.write(tail)
        except _EXPECTED_APP_ERRORS:
            return

    @staticmethod
    def _theme_palette_for_variant(variant): return theme_service.theme_palette_for_variant(variant)

    def _apply_dark_theme(self): return theme_service._apply_dark_theme(self)

    def _tree_font_profile(self):
        """Scale tree font with editor font while preserving icon alignment."""
        is_variant_b = str(getattr(self, "_tree_style_variant", "B")).upper() == "B"
        editor_size = max(6, min(32, int(round(float(getattr(self, "_font_size", 10) or 10)))))
        if is_variant_b:
            main_size = max(10, min(14, editor_size))
            sub_size = max(9, main_size - 1)
            # Keep a floor so tree sprite markers stay vertically centered.
            row_height = max(23, min(30, main_size + 14))
            main_weight = "bold"
            sub_weight = "normal"
        else:
            main_size = max(11, min(15, editor_size + 1))
            sub_size = max(10, main_size - 1)
            row_height = max(22, min(30, main_size + 12))
            main_weight = "normal"
            sub_weight = "normal"
        return {
            "is_variant_b": bool(is_variant_b),
            "main_size": int(main_size),
            "sub_size": int(sub_size),
            "row_height": int(row_height),
            "main_weight": str(main_weight),
            "sub_weight": str(sub_weight),
        }

    def _tree_font_family(self, is_variant_b): return self._resolve_font_family(
            (
                ["Tektur SBold", "Tektur SemiBold", "Tektur Med", "Tektur"]
                if is_variant_b
                else [
                    "Tektur SemiBold",
                    "Tektur",
                    "Oxanium",
                    "Rajdhani",
                    "Segoe UI Semibold",
                    "Segoe UI",
                ]
            ),
            self._preferred_mono_family(),
        )

    def _tree_sub_font_family(self):
        # Prioritize clear numeric glyphs for deep/sub tree paths.
        return self._resolve_font_family(
            [
                "Cascadia Code",
                "Consolas",
                "JetBrains Mono",
                "Segoe UI",
            ],
            self._preferred_mono_family(),
        )

    def _apply_tree_style(self, style=None, panel=None, tree_fg=None, select_bg=None, select_fg=None):
        tree_widget = getattr(self, "tree", None)
        return UI_FACTORY.apply_styles(
            self,
            tree_widget,
            ttk_module=ttk,
            expected_errors=_EXPECTED_APP_ERRORS,
            style=style,
            panel=panel,
            tree_fg=tree_fg,
            select_bg=select_bg,
            select_fg=select_fg,
        )

    @staticmethod
    def _hex_to_colorref(hex_color): return UI_FACTORY.hex_to_colorref(hex_color)

    def _apply_windows_titlebar_theme(self, bg=None, fg=None, border=None, window_widget=None): return theme_service._apply_windows_titlebar_theme(self, bg, fg, border, window_widget)

    def _style_text_widget(self):
        theme = getattr(self, "_theme", None)
        if not theme:
            return
        mono = (self._preferred_mono_family(), self._font_size)
        self.text.configure(
            font=mono,
            bg=theme["panel"],
            fg=theme["fg"],
            insertbackground=theme["fg"],
            selectbackground=theme["select_bg"],
            selectforeground=theme["select_fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme["panel"],
            highlightcolor=theme["panel"],
        )
        try:
            # Keep selection visuals explicit so drag-select remains visible
            # against custom error tint/highlight tags.
            self.text.tag_config("sel", background=theme["select_bg"], foreground=theme["select_fg"])
            self.text.tag_raise("sel")
        except _EXPECTED_APP_ERRORS:
            pass
        self._configure_json_lock_tags()
        self._style_text_context_menu()

    def _build_text_context_menu(self): return text_context_manager.TEXT_CONTEXT.text_context_menu_service.build_text_context_menu(
            self,
            tk=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _text_context_menu_palette(self):
        return ui_timer_service._text_context_menu_palette(**locals())

    @staticmethod
    def _text_context_menu_scale():
        # Keep menu compact while preserving readability and click targets.
        return 0.8

    def _style_text_context_menu(self): return text_context_manager.TEXT_CONTEXT.text_context_menu_service.style_text_context_menu(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _style_text_context_menu_rows(
        self,
        palette=None,
        font_family=None,
        shortcut_font_family=None,
        title_size=None,
        small_size=None,
        apply_fonts=False,
    ):
        cached = getattr(self, "_text_context_menu_row_style", None)
        if palette is None and isinstance(cached, dict):
            palette = cached.get("palette")
        if font_family is None and isinstance(cached, dict):
            font_family = cached.get("font_family")
        if shortcut_font_family is None and isinstance(cached, dict):
            shortcut_font_family = cached.get("shortcut_font_family")
        if title_size is None and isinstance(cached, dict):
            title_size = cached.get("title_size")
        if small_size is None and isinstance(cached, dict):
            small_size = cached.get("small_size")
        if palette is None:
            palette = self._text_context_menu_palette()
        if font_family is None:
            font_family = self._preferred_mono_family()
        if shortcut_font_family is None:
            shortcut_font_family = self._preferred_mono_family()
        scale = self._text_context_menu_scale()
        if title_size is None:
            title_size = max(8, int(round(11 * scale)))
        if small_size is None:
            small_size = max(7, int(round(9 * scale)))

        for action in ("undo", "redo", "copy", "paste", "autofix"):
            self._style_text_context_menu_row(
                action,
                palette=palette,
                font_family=font_family,
                shortcut_font_family=shortcut_font_family,
                title_size=title_size,
                small_size=small_size,
                apply_fonts=apply_fonts,
            )

    def _style_text_context_menu_row(
        self,
        action,
        palette=None,
        font_family=None,
        shortcut_font_family=None,
        title_size=None,
        small_size=None,
        apply_fonts=False,
    ):
        return text_context_manager.TEXT_CONTEXT.text_context_menu_service.style_text_context_menu_row(
            self,
            action,
            palette=palette,
            font_family=font_family,
            shortcut_font_family=shortcut_font_family,
            title_size=title_size,
            small_size=small_size,
            apply_fonts=apply_fonts,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _has_text_selection(self): return text_context_state_service.has_text_selection(self.text, _EXPECTED_APP_ERRORS)

    def _clipboard_has_text(self): return text_context_state_service.clipboard_has_text(self.root, _EXPECTED_APP_ERRORS)

    def _text_can_undo(self): return text_context_state_service.text_can_undo(self.text, _EXPECTED_APP_ERRORS)

    def _text_can_redo(self): return text_context_state_service.text_can_redo(self.text, _EXPECTED_APP_ERRORS)

    def _destroy_text_context_menu(self):
        return ui_timer_service._destroy_text_context_menu(**locals())

    def _set_text_context_menu_item_state(self, action, enabled):
        states = getattr(self, "_text_context_menu_item_states", None)
        if not isinstance(states, dict):
            return
        states[action] = bool(enabled)

    def _first_enabled_text_context_action(self): return text_context_action_service.first_enabled_action(
            states=getattr(self, "_text_context_menu_item_states", {}) or {},
            ordered_actions=("undo", "redo", "copy", "paste", "autofix"),
        )

    def _set_text_context_menu_hover_action(self, action):
        states = getattr(self, "_text_context_menu_item_states", {}) or {}
        next_action = action if states.get(action) else None
        previous_action = getattr(self, "_text_context_menu_hover_action", None)
        if next_action == previous_action:
            return
        self._text_context_menu_hover_action = next_action
        if previous_action:
            self._style_text_context_menu_row(previous_action)
        if next_action:
            self._style_text_context_menu_row(next_action)

    def _on_text_context_menu_hover(self, action):
        self._set_text_context_menu_hover_action(action)
        return "break"

    def _text_context_menu_action_for_widget(self, widget): return text_context_pointer_service.action_for_widget(
            widget=widget,
            widget_actions=getattr(self, "_text_context_menu_widget_actions", {}) or {},
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _text_context_menu_action_for_pointer(self): return text_context_pointer_service.action_for_pointer(
            popup=getattr(self, "_text_context_menu", None),
            root=getattr(self, "root", None),
            widget_actions=getattr(self, "_text_context_menu_widget_actions", {}) or {},
            widget_is_popup_child=self._widget_is_popup_child,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _on_text_context_menu_motion(self, event=None):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return "break"
        action, inside = self._text_context_menu_action_for_pointer()
        if action is None and inside:
            return "break"
        self._set_text_context_menu_hover_action(action if inside else None)
        return "break"

    def _on_text_context_menu_popup_leave(self, event=None):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return "break"
        root = getattr(self, "root", None)
        if root is None:
            return "break"
        try:
            under_pointer = root.winfo_containing(root.winfo_pointerx(), root.winfo_pointery())
        except _EXPECTED_APP_ERRORS:
            under_pointer = None
        if self._widget_is_popup_child(under_pointer, popup):
            return "break"
        if getattr(self, "_text_context_menu_hover_action", None) is None:
            return "break"
        self._set_text_context_menu_hover_action(None)
        return "break"

    def _on_text_context_menu_click(self, action): return text_context_action_service.dispatch_click_action(
            action=action,
            states=getattr(self, "_text_context_menu_item_states", {}) or {},
            hide_menu_fn=self._hide_text_context_menu,
            handlers={
                "undo": self._on_context_undo,
                "redo": self._on_context_redo,
                "copy": self._on_context_copy,
                "paste": self._on_context_paste,
                "autofix": self._on_context_autofix,
            },
        )

    def _on_text_context_menu_escape(self, event=None):
        self._hide_text_context_menu()
        return "break"

    @staticmethod
    def _widget_is_popup_child(widget, popup): return text_context_widget_service.is_popup_child(widget, popup)

    def _bind_text_context_menu_global_dismiss(self):
        root = getattr(self, "root", None)
        if root is None:
            return
        self._unbind_text_context_menu_global_dismiss()
        bindings = []
        for sequence in ("<Button-1>", "<Button-2>", "<Button-3>", "<MouseWheel>", "<Escape>"):
            try:
                bind_id = root.bind(sequence, self._on_text_context_menu_global_dismiss, add="+")
            except _EXPECTED_APP_ERRORS:
                bind_id = None
            if bind_id:
                bindings.append((sequence, bind_id))
        self._text_context_menu_global_bindings = bindings

    def _unbind_text_context_menu_global_dismiss(self):
        root = getattr(self, "root", None)
        if root is None:
            self._text_context_menu_global_bindings = []
            return
        for sequence, bind_id in list(getattr(self, "_text_context_menu_global_bindings", [])):
            try:
                root.unbind(sequence, bind_id)
            except _EXPECTED_APP_ERRORS:
                pass
        self._text_context_menu_global_bindings = []

    def _on_text_context_menu_global_dismiss(self, event=None):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except _EXPECTED_APP_ERRORS:
            return
        widget = getattr(event, "widget", None)
        if self._widget_is_popup_child(widget, popup):
            return
        self._hide_text_context_menu()

    def _on_root_focus_out(self, event=None):
        return ui_timer_service._on_root_focus_out(**locals())

    def _on_root_focus_in(self, event=None):
        return ui_timer_service._on_root_focus_in(**locals())

    def _ensure_bug_report_dialog_visible(self):
        dlg = getattr(self, "_bug_report_dialog", None)
        if dlg is None:
            return
        try:
            if not dlg.winfo_exists():
                return
            if not dlg.winfo_ismapped():
                dlg.deiconify()
            dlg.lift()
            try:
                dlg.focus_force()
            except _EXPECTED_APP_ERRORS:
                pass
        except _EXPECTED_APP_ERRORS:
            return

    def _arm_bug_report_follow_root(self, dialog=None):
        if not bool(getattr(self, "BUG_REPORT_USE_CUSTOM_CHROME", True)):
            self._bug_report_follow_root = False
            return
        root = getattr(self, "root", None)
        dlg = dialog if dialog is not None else getattr(self, "_bug_report_dialog", None)
        if root is None or dlg is None:
            self._bug_report_follow_root = False
            return
        try:
            if not dlg.winfo_exists():
                self._bug_report_follow_root = False
                return
            root.update_idletasks()
            dlg.update_idletasks()
            self._bug_report_offset_x = int(dlg.winfo_x()) - int(root.winfo_x())
            self._bug_report_offset_y = int(dlg.winfo_y()) - int(root.winfo_y())
            self._bug_report_follow_root = True
            self._bug_report_is_dragging = False
        except _EXPECTED_APP_ERRORS:
            self._bug_report_follow_root = False

    def _on_root_configure(self, event=None):
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT" or bool(
            getattr(self, "_input_mode_paned_lock_active", False)
        ):
            self._sync_input_mode_paned_sash_lock()
        self._schedule_topbar_alignment(delay_ms=35)
        if not bool(getattr(self, "BUG_REPORT_USE_CUSTOM_CHROME", True)):
            return
        if not bool(getattr(self, "_bug_report_follow_root", False)):
            return
        if bool(getattr(self, "_bug_report_is_dragging", False)):
            return
        root = getattr(self, "root", None)
        dlg = getattr(self, "_bug_report_dialog", None)
        if root is None or dlg is None:
            return
        try:
            if not dlg.winfo_exists():
                return
            if not dlg.winfo_ismapped():
                return
            target_x = int(root.winfo_x()) + int(getattr(self, "_bug_report_offset_x", 0))
            target_y = int(root.winfo_y()) + int(getattr(self, "_bug_report_offset_y", 0))
            vroot_x = int(root.winfo_vrootx())
            vroot_y = int(root.winfo_vrooty())
            screen_w = int(root.winfo_vrootwidth())
            screen_h = int(root.winfo_vrootheight())
            dlg_w = max(1, int(dlg.winfo_width()))
            dlg_h = max(1, int(dlg.winfo_height()))
            max_x = max(vroot_x, (vroot_x + screen_w) - dlg_w)
            max_y = max(vroot_y, (vroot_y + screen_h) - dlg_h)
            target_x = max(vroot_x, min(max_x, target_x))
            target_y = max(vroot_y, min(max_y, target_y))
            if target_x != int(dlg.winfo_x()) or target_y != int(dlg.winfo_y()):
                dlg.geometry(f"+{target_x}+{target_y}")
        except _EXPECTED_APP_ERRORS:
            return

    def _hide_text_context_menu_if_app_inactive(self):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except _EXPECTED_APP_ERRORS:
            return
        root = getattr(self, "root", None)
        if root is None:
            self._hide_text_context_menu()
            return
        try:
            focused = root.focus_displayof()
        except _EXPECTED_APP_ERRORS:
            focused = None
        if focused is None:
            self._hide_text_context_menu()

    @staticmethod
    def _blend_hex_color(color_a, color_b, ratio): return color_utility_service.blend_hex_color(
            color_a,
            color_b,
            ratio,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _start_text_context_menu_pulse(self):
        return ui_timer_service._start_text_context_menu_pulse(**locals())

    def _stop_text_context_menu_pulse(self):
        return ui_timer_service._stop_text_context_menu_pulse(**locals())

    def _tick_text_context_menu_pulse(self):
        return ui_timer_service._tick_text_context_menu_pulse(**locals())

    def _hide_text_context_menu(self):
        return ui_timer_service._hide_text_context_menu(**locals())

    def _show_text_context_menu_popup(self, popup_x, popup_y):
        return ui_timer_service._show_text_context_menu_popup(**locals())

    def _show_text_context_menu(self, event=None): return text_context_manager.TEXT_CONTEXT.text_context_menu_service.show_text_context_menu(
            self,
            event,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _on_context_copy(self):
        target_widget = getattr(self, "_input_context_target_widget", None)
        if target_widget is not None and target_widget is not getattr(self, "text", None):
            self._on_input_context_copy()
            return
        if not self._has_text_selection():
            return
        try:
            text = self.text.get("sel.first", "sel.last")
        except _EXPECTED_APP_ERRORS:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except _EXPECTED_APP_ERRORS:
            return

    def _on_context_undo(self):
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            self.text.edit_undo()
            self.text.see("insert")
            self._auto_apply_pending = True
        except _EXPECTED_APP_ERRORS:
            return

    def _on_context_redo(self):
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            self.text.edit_redo()
            self.text.see("insert")
            self._auto_apply_pending = True
        except _EXPECTED_APP_ERRORS:
            return

    def _on_context_paste(self):
        target_widget = getattr(self, "_input_context_target_widget", None)
        if target_widget is not None and target_widget is not getattr(self, "text", None):
            self._on_input_context_paste()
            return
        try:
            pasted = self.root.clipboard_get()
        except _EXPECTED_APP_ERRORS:
            return
        if pasted is None:
            return
        is_valid, safe_text, reason = clipboard_service.validate_clipboard_paste_payload(
            pasted,
            validation_service.validate_editor_text_payload,
        )
        if not is_valid:
            self._show_error_overlay("Invalid Entry", reason)
            return
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            if self._has_text_selection():
                self.text.delete("sel.first", "sel.last")
        except _EXPECTED_APP_ERRORS:
            pass
        try:
            self.text.insert("insert", safe_text)
            self.text.see("insert")
            self._auto_apply_pending = True
        except _EXPECTED_APP_ERRORS:
            return

    def _destroy_input_context_menu(self):
        menu = getattr(self, "_input_context_menu", None)
        self._input_context_target_widget = None
        self._input_context_target_allow_paste = False
        if menu is None:
            return
        try:
            menu.destroy()
        except _EXPECTED_APP_ERRORS:
            pass
        self._input_context_menu = None

    def _bind_input_context_widget(self, widget, *, allow_paste=True):
        if widget is None:
            return
        try:
            widget._hh_input_allow_paste = bool(allow_paste)
        except _EXPECTED_APP_ERRORS:
            return
        try:
            widget.bind("<Button-3>", self._show_input_context_with_text_menu, add="+")
        except _EXPECTED_APP_ERRORS:
            return

    @staticmethod
    def _input_widget_has_selection(widget):
        try:
            return bool(widget.selection_present())
        except _EXPECTED_APP_ERRORS:
            return False

    def _show_input_context_menu(self, event=None): return self._show_input_context_with_text_menu(event)

    def _show_widget_context_with_text_menu(self, event=None, *, allow_paste=True):
        widget = getattr(event, "widget", None)
        if widget is None:
            return None
        self._input_context_target_widget = widget
        self._input_context_target_allow_paste = bool(allow_paste)
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            self._build_text_context_menu()
            popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return "break"
        can_copy = self._input_widget_has_selection(widget)
        can_paste = bool(bool(allow_paste) and self._clipboard_has_text())
        self._set_text_context_menu_item_state("undo", False)
        self._set_text_context_menu_item_state("redo", False)
        self._set_text_context_menu_item_state("copy", can_copy)
        self._set_text_context_menu_item_state("paste", can_paste)
        self._set_text_context_menu_item_state("autofix", False)
        self._text_context_menu_hover_action = None
        try:
            if hasattr(widget, "focus_set"):
                widget.focus_set()
        except _EXPECTED_APP_ERRORS:
            pass
        x_root = getattr(event, "x_root", None)
        y_root = getattr(event, "y_root", None)
        if x_root is None or y_root is None:
            try:
                x_root = int(self.root.winfo_rootx()) + 20
                y_root = int(self.root.winfo_rooty()) + 20
            except _EXPECTED_APP_ERRORS:
                return "break"
        self._hide_text_context_menu()
        self._text_context_menu_hover_action = None
        self._show_text_context_menu_popup(int(x_root), int(y_root))
        return "break"

    def _show_input_context_with_text_menu(self, event=None):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return None
        widget = getattr(event, "widget", None)
        if widget is None:
            return None
        allow_paste = bool(getattr(widget, "_hh_input_allow_paste", False))
        return self._show_widget_context_with_text_menu(event, allow_paste=allow_paste)

    def _show_find_entry_context_menu(self, event=None): return self._show_widget_context_with_text_menu(event, allow_paste=True)

    def _on_input_context_copy(self):
        widget = getattr(self, "_input_context_target_widget", None)
        if widget is None:
            return
        if not self._input_widget_has_selection(widget):
            return
        try:
            copied = widget.selection_get()
        except _EXPECTED_APP_ERRORS:
            return
        if copied is None:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(copied)
        except _EXPECTED_APP_ERRORS:
            return

    def _on_input_context_paste(self):
        text_context_action_service.on_input_context_paste(
            self,
            clipboard_service=clipboard_service,
            validation_service=validation_service,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    @staticmethod
    def _parse_suggestion_before_after(message): return error_service.parse_suggestion_before_after(message)

    def _current_error_line_number(self):
        focus_idx = getattr(self, "_error_focus_index", None)
        if focus_idx:
            try:
                return int(str(focus_idx).split(".")[0])
            except _EXPECTED_APP_ERRORS:
                pass
        try:
            ranges = self.text.tag_ranges("json_error")
            if ranges:
                return int(str(ranges[0]).split(".")[0])
        except _EXPECTED_APP_ERRORS:
            pass
        return None

    def _current_overlay_suggestion(self): return editor_purge_service._current_overlay_suggestion(self)

    def _can_context_autofix(self):
        payload = self._current_overlay_suggestion()
        return bool(payload and payload.get("after") is not None)

    def _apply_line_autofix(self, line_no, before_text, after_text): return text_context_action_service.apply_line_autofix(
            self,
            line_no,
            before_text,
            after_text,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _restore_insert_index(self, restore_index, log_failure=False):
        """Best-effort cursor restore after local text rewrites or re-render passes."""
        if not restore_index:
            return
        target_line = 1
        try:
            target_line = int(self._line_number_from_index(restore_index) or 1)
        except _EXPECTED_APP_ERRORS:
            target_line = 1
        try:
            line_text = str(restore_index).split(".", 1)
            line_no = max(1, int(line_text[0]))
            col_no = max(0, int(line_text[1]))
            max_line = max(1, int(str(self.text.index("end-1c")).split(".", 1)[0]))
            line_no = min(line_no, max_line)
            live_line_text = str(self._line_text(line_no) or "")
            col_no = min(col_no, len(live_line_text))
            restore_index = f"{line_no}.{col_no}"
            self.text.mark_set("insert", restore_index)
            self.text.see(restore_index)
        except _EXPECTED_APP_ERRORS:
            if not bool(log_failure):
                return
            try:
                marker = type(
                    "E",
                    (),
                    {
                        "msg": "Cursor restore failed after autofix/apply cycle.",
                        "lineno": target_line,
                        "colno": 1,
                    },
                )
                self._log_json_error(
                    marker,
                    target_line,
                    note=f"cursor_restore_failed requested={str(restore_index)}",
                )
            except _EXPECTED_APP_ERRORS:
                pass
            return

    def _on_context_autofix(self):
        payload = self._current_overlay_suggestion()
        if not payload:
            return
        item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
        path = self.item_to_path.get(item_id, []) if item_id else []
        restore_index_before = ""
        try:
            restore_index_before = str(self.text.index("insert") or "")
        except _EXPECTED_APP_ERRORS:
            restore_index_before = ""
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        changed = self._apply_line_autofix(
            payload.get("line"),
            payload.get("before"),
            payload.get("after"),
        )
        if changed:
            # Cursor policy for right-click Auto-Fix: keep the caret at the
            # post-fix edit position (typically after inserted fix chars).
            restore_index_after = ""
            try:
                restore_index_after = str(self.text.index("insert") or "")
            except _EXPECTED_APP_ERRORS:
                restore_index_after = ""
            target_restore_index = str(restore_index_after or restore_index_before or "")
            self._restore_insert_index(target_restore_index)
            try:
                self._apply_json_view_lock_state(path)
            except _EXPECTED_APP_ERRORS:
                pass
            # Defer final cursor restore until apply_edit() completes and repaints this node.
            # Keep the exact post-fix column so mid-line fixes do not jump to line start/end.
            self._pending_insert_restore_index = target_restore_index
            self._auto_apply_pending = True

    @staticmethod
    def _error_symbol_notes(): return error_service.error_symbol_notes()

    def _is_symbol_error_note(self, note): return error_service.is_symbol_error_note(note)

    def _error_marker_colors(self, note, palette, insertion_only=False): return error_service.error_marker_colors(note, palette, insertion_only=insertion_only)

    def _tag_has_ranges(self, tag_name):
        try:
            return bool(self.text.tag_ranges(tag_name))
        except _EXPECTED_APP_ERRORS:
            return False

    def _current_error_palette(self): return error_service.current_error_palette(
            variant=getattr(self, "_app_theme_variant", "SIINDBAD"),
            theme=getattr(self, "_theme", {}),
        )

    def _apply_text_selection_style(self, use_error_palette=False):
        try:
            theme = getattr(self, "_theme", {}) or {}
            palette = self._current_error_palette() if use_error_palette else None
            sel_bg, sel_fg = error_service.selection_colors(
                theme,
                use_error_palette=use_error_palette,
                error_palette=palette,
            )
            self.text.configure(selectbackground=sel_bg, selectforeground=sel_fg)
            self.text.tag_config("sel", background=sel_bg, foreground=sel_fg)
            self.text.tag_raise("sel")
        except _EXPECTED_APP_ERRORS:
            return

    def _preferred_mono_family(self): return UI_FACTORY.preferred_mono_family(
            self,
            tkfont_module=tkfont,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _resolve_font_family(self, preferred_families, fallback): return UI_FACTORY.resolve_font_family(
            self,
            preferred_families,
            fallback,
            tkfont_module=tkfont,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _credit_name_font(self):
        fallback = self._preferred_mono_family()
        # Footer badge typography: prefer Tektur for a sharper cyber look.
        family = self._resolve_font_family(
            [
                "Tektur SemiBold",
                "Tektur",
                "Oxanium SemiBold",
                "Oxanium",
                "Rajdhani SemiBold",
                "Rajdhani",
                "Segoe UI Semibold",
                "Segoe UI Bold",
                "Segoe UI",
            ],
            fallback,
        )
        return (family, 9, "bold")

    def _footer_badge_chip_font(self):
        fallback = self._credit_name_font()
        if self._footer_style_variant() == "B":
            family = self._resolve_font_family(
                ["Tektur Med", "Tektur", "Oxanium", "Rajdhani", "Segoe UI Semibold", "Segoe UI"],
                fallback[0],
            )
            return (family, 9, "normal")
        return fallback

    def _font_dropdown_number_font(self):
        fallback = self._preferred_mono_family()
        family = self._resolve_font_family(
            [
                "Rajdhani SemiBold",
                "Rajdhani",
                "Bahnschrift SemiBold",
                "Bahnschrift",
                "Segoe UI Semibold",
                "Segoe UI",
            ],
            fallback,
        )
        return (family, 10, "bold")

    def _readme_font_for_theme(self):
        """Theme-aware monospaced font for README popup readability."""
        fallback = self._preferred_mono_family()
        readme_size = max(8, min(18, int(round(float(getattr(self, "_font_size", 10) or 10) - 1.0))))
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            family = self._resolve_font_family(
                ["JetBrains Mono", "Cascadia Code", "Consolas", "Courier New"],
                fallback,
            )
            return (family, readme_size)
        family = self._resolve_font_family(
            ["Cascadia Code", "JetBrains Mono", "Consolas", "Courier New"],
            fallback,
        )
        return (family, readme_size)

    def _refresh_open_readme_window(self):
        """Re-open README popup to apply updated font/theme + geometry sizing."""
        window = getattr(self, "_readme_window", None)
        if window is None:
            return
        position_hint = None
        try:
            if not window.winfo_exists():
                self._readme_window = None
                return
            try:
                position_hint = (int(window.winfo_x()), int(window.winfo_y()))
            except _EXPECTED_APP_ERRORS:
                position_hint = None
            window.destroy()
        except _EXPECTED_APP_ERRORS:
            self._readme_window = None
            return
        self._readme_window = None
        try:
            self.show_readme(position_hint=position_hint)
        except _EXPECTED_APP_ERRORS:
            pass

    def _on_font_size_selected(self, event=None):
        """Handle font size selection from dropdown."""
        combo = getattr(self, "font_size_combo", None)
        if combo is None:
            return
        try:
            size = int(combo.get())
            if 6 <= size <= 32:
                self._font_size = size
                self._update_font_size()
        except (ValueError, tk.TclError):
            pass

    def increase_font_size(self):
        """Increase the font size of the text widget."""
        if self._font_size < 32:  # Max font size limit
            self._font_size += 1
            self._update_font_size()
            combo = getattr(self, "font_size_combo", None)
            if combo is not None:
                try:
                    combo.set(str(self._font_size))
                except _EXPECTED_APP_ERRORS:
                    pass

    def decrease_font_size(self):
        """Decrease the font size of the text widget."""
        if self._font_size > 6:  # Min font size limit
            self._font_size -= 1
            self._update_font_size()
            combo = getattr(self, "font_size_combo", None)
            if combo is not None:
                try:
                    combo.set(str(self._font_size))
                except _EXPECTED_APP_ERRORS:
                    pass

    def _update_font_size(self):
        """Update the font size in the text widget."""
        if self.text:
            mono = (self._preferred_mono_family(), self._font_size)
            self.text.configure(font=mono)
        # Keep tree text tied to editor font while preserving icon alignment.
        try:
            self._apply_tree_style()
        except _EXPECTED_APP_ERRORS:
            pass
        if self._font_size_value_label and self._font_size_value_label.winfo_exists():
            try:
                self._font_size_value_label.configure(text=str(int(self._font_size)))
            except _EXPECTED_APP_ERRORS:
                pass
        # Persist the chosen font size for future runs
        try:
            self._save_user_settings()
        except _EXPECTED_APP_ERRORS:
            pass
        self._refresh_open_readme_window()
        # Keep active warning/error overlays synchronized with font-size changes.
        self._refresh_active_error_theme()
        # Keep INPUT-mode category views synced to editor font changes.
        self._refresh_input_mode_theme_widgets()

    def _sync_font_size_from_var(self):
        """Read the combobox StringVar and apply it to the internal font size."""
        var = getattr(self, "font_size_var", None)
        if var is None:
            return
        try:
            val = var.get()
            size = int(val)
            if 6 <= size <= 32:
                if size != self._font_size:
                    self._font_size = size
                    self._update_font_size()
        except _EXPECTED_APP_ERRORS:
            return

    def _settings_path(self):
        """Return path to the user settings file in the runtime data directory."""
        return os.path.join(self._runtime_data_dir(create=True), self.SETTINGS_FILENAME)

    @staticmethod
    def _legacy_settings_path():
        try:
            home = os.path.expanduser("~")
            return os.path.join(home, JsonEditor.LEGACY_SETTINGS_FILENAME)
        except _EXPECTED_APP_ERRORS:
            return os.path.join(os.getcwd(), JsonEditor.SETTINGS_FILENAME)

    def _load_user_settings(self):
        """Load user settings (font size, app theme, startup update-check preference)."""
        return user_settings_service.load_user_settings(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _save_user_settings(self):
        """Save user settings (font size, app theme, startup update-check preference)."""
        return user_settings_service.save_user_settings(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    @staticmethod
    def _normalize_button_token(value): return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def _siindbad_effective_style(self): return VISUALS._siindbad_effective_style(self)

    def _toolbar_button_font(self, small=False):
        style = self._siindbad_effective_style()
        if style == "B":
            family = self._resolve_font_family(
                [
                    "Tektur SemiBold",
                    "Tektur",
                    "Orbitron SemiBold",
                    "Orbitron",
                    "Audiowide",
                    "Eurostile",
                    "Bahnschrift SemiBold",
                    "Bahnschrift",
                    "Segoe UI Semibold",
                    "Segoe UI",
                ],
                self._preferred_mono_family(),
            )
        else:
            family = self._resolve_font_family(
                ["Segoe UI Semibold", "Segoe UI Bold", "Segoe UI"],
                self._preferred_mono_family(),
            )
        size = 8 if small else 10
        if style == "A" and small:
            size = 11
        if style == "A" and not small:
            size = 10
        return (family, size, "bold")

    def _siindbad_toolbar_button_symbol(self, key): return toolbar_service.siindbad_toolbar_button_symbol(
            style=self._siindbad_effective_style(),
            key=key,
        )

    @staticmethod
    def _hex_to_rgb_tuple(hex_color, default_rgb=(220, 235, 245)): return color_utility_service.hex_to_rgb_tuple(
            hex_color,
            default_rgb=default_rgb,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    @staticmethod
    def _normalize_root_tree_key(value): return tree_view_service.normalize_root_tree_key(value)

    def _tree_display_label_for_key(self, key): return tree_view_service.tree_display_label_for_key(
            key=key,
            tree_style_variant=getattr(self, "_tree_style_variant", "B"),
            safe_display_labels=self.TREE_B_SAFE_DISPLAY_LABELS,
        )

    def _init_chrome_runtime_state(self): return LIFECYCLE.init_chrome_runtime_state(self)

    def _init_footer_bugreport_runtime_state(self): return LIFECYCLE.init_footer_bugreport_runtime_state(self)

    def _init_text_context_runtime_state(self): return LIFECYCLE.init_text_context_runtime_state(self)

    def _init_theme_update_runtime_state(self):
        # Regression marker: _update_install_stage_hold_ms = 3000
        # Regression marker: _update_restart_notice_ms = 4200
        return LIFECYCLE.init_theme_update_runtime_state(self)

    def _init_editor_session_runtime_state(self):
        # Regression marker: self._list_labelers = tree_engine_service.default_list_labelers(self)
        # Regression marker: _allow_highlight_key_change_once
        return LIFECYCLE.init_editor_session_runtime_state(self)

    def _init_input_mode_runtime_state(self):
        # Regression marker: self._input_mode_last_render_path_key
        return LIFECYCLE.init_input_mode_runtime_state(self)

    def _init_tree_runtime_state(self): return LIFECYCLE.init_tree_runtime_state(self)

    @staticmethod
    def _bounded_cache_put(cache, key, value, max_items=128): return VISUALS._bounded_cache_put(cache, key, value, max_items)
    def _siindbad_toolbar_style_palette(self): return VISUALS._siindbad_toolbar_style_palette(self)
    def _draw_siindbad_toolbar_icon(self, key, fg_hex, accent_hex, style, accent2_hex=None): return VISUALS._draw_siindbad_toolbar_icon(self, key, fg_hex, accent_hex, style, accent2_hex)
    def _ensure_siindbad_button_icons(self): return VISUALS._ensure_siindbad_button_icons(self)
    def _find_entry_target_width(self): return VISUALS._find_entry_target_width(self)
    @staticmethod
    def _siindbad_toolbar_label_text(style, key, text): return VISUALS._siindbad_toolbar_label_text(style, key, text)
    def _update_find_entry_layout(self): return VISUALS._update_find_entry_layout(self)
    def _schedule_topbar_alignment(self, delay_ms=35): return VISUALS._schedule_topbar_alignment(self, delay_ms)
    @staticmethod
    def _window_is_maximized(window): return VISUALS._window_is_maximized(window)
    def _apply_toolbar_layout_mode(self, force=False): return VISUALS._apply_toolbar_layout_mode(self, force)
    def _apply_toolbar_spacing_for_mode(self, mode): return VISUALS._apply_toolbar_spacing_for_mode(self, mode)
    def _find_entry_base_width(self): return VISUALS._find_entry_base_width(self)
    def _apply_max_toolbar_search_compaction(self, toolbar_w, logo_w): return VISUALS._apply_max_toolbar_search_compaction(self, toolbar_w, logo_w)
    def _apply_toolbar_layout_normal(self, center): return VISUALS._apply_toolbar_layout_normal(self, center)
    def _apply_toolbar_layout_max(self, center, host): return VISUALS._apply_toolbar_layout_max(self, center, host)
    def _align_topbar_to_logo(self): return VISUALS._align_topbar_to_logo(self)
    @staticmethod
    def _siindbad_toolbar_button_width(style, key, text): return VISUALS._siindbad_toolbar_button_width(style, key, text)
    def _siindbad_toolbar_frame_width(self, style, key, text): return VISUALS._siindbad_toolbar_frame_width(self, style, key, text)
    def _siindbad_b_sprite_dir(self): return VISUALS._siindbad_b_sprite_dir(self)
    def _siindbad_b_sprite_manifest(self): return VISUALS._siindbad_b_sprite_manifest(self)
    def _invalidate_siindbad_b_sprite_cache(self): return VISUALS._invalidate_siindbad_b_sprite_cache(self)
    def _siindbad_b_render_mode(self, override=None): return VISUALS._siindbad_b_render_mode(self, override)
    def _siindbad_b_sprite_bundle(self, key, width, height, render_mode='full'): return VISUALS._siindbad_b_sprite_bundle(self, key, width, height, render_mode)
    def _siindbad_b_button_height(self, key, default_height=34): return VISUALS._siindbad_b_button_height(self, key, default_height)
    def _siindbad_b_search_spec(self): return VISUALS._siindbad_b_search_spec(self)
    def _siindbad_b_search_sprite_image(self, width, height): return VISUALS._siindbad_b_search_sprite_image(self, width, height)
    def _siindbad_b_font_sprite_spec(self): return VISUALS._siindbad_b_font_sprite_spec(self)
    def _load_siindbad_b_font_sprite_image(self): return VISUALS._load_siindbad_b_font_sprite_image(self)
    def _siindbad_b_asset_button_path(self, key): return VISUALS._siindbad_b_asset_button_path(self, key)
    @staticmethod
    def _pointer_within_widget(widget): return VISUALS._pointer_within_widget(widget)
    def _siindbad_b_render_button_bundle(self, key, text, width, height, palette, render_mode=None): return VISUALS._siindbad_b_render_button_bundle(self, key, text, width, height, palette, render_mode)
    def _stop_siindbad_b_button_scan(self, button): return VISUALS._stop_siindbad_b_button_scan(self, button)
    def _stop_all_siindbad_b_button_scans(self): return VISUALS._stop_all_siindbad_b_button_scans(self)
    def _invoke_siindbad_b_button(self, button, command): return VISUALS._invoke_siindbad_b_button(self, button, command)
    def _tick_siindbad_b_button_scan(self, button): return VISUALS._tick_siindbad_b_button_scan(self, button)
    def _start_siindbad_b_button_scan(self, button): return VISUALS._start_siindbad_b_button_scan(self, button)
    def _siindbad_b_button_hover_enter(self, button): return VISUALS._siindbad_b_button_hover_enter(self, button)
    def _siindbad_b_button_hover_leave(self, button): return VISUALS._siindbad_b_button_hover_leave(self, button)
    def _apply_siindbad_toolbar_button_style(self, button, key, text): return VISUALS._apply_siindbad_toolbar_button_style(self, button, key, text)
    def _apply_asset_toolbar_button_style(self, button): return VISUALS._apply_asset_toolbar_button_style(self, button)
    def _make_siindbad_stepper_button(self, parent, symbol, command): return VISUALS._make_siindbad_stepper_button(self, parent, symbol, command)
    def _make_siindbad_font_stepper(self, parent): return VISUALS._make_siindbad_font_stepper(self, parent)
    def _make_font_stepper(self, parent): return VISUALS._make_font_stepper(self, parent)
    def _render_font_control(self): return VISUALS._render_font_control(self)
    def _style_combobox_popdown(self, combo, bg, fg, select_bg, select_fg, font=None): return VISUALS._style_combobox_popdown(self, combo, bg, fg, select_bg, select_fg, font)
    @staticmethod
    def _scale_hitbox(hitbox, src_width, src_height, dst_width, dst_height): return VISUALS._scale_hitbox(hitbox, src_width, src_height, dst_width, dst_height)
    @staticmethod
    def _point_in_hitbox(px, py, hitbox): return VISUALS._point_in_hitbox(px, py, hitbox)
    def _font_stepper_action(self, width, height, click_x, click_y): return VISUALS._font_stepper_action(self, width, height, click_x, click_y)
    def _on_font_stepper_click(self, event): return VISUALS._on_font_stepper_click(self, event)
    def _on_font_stepper_motion(self, event): return VISUALS._on_font_stepper_motion(self, event)
    def _make_toolbar_button(self, parent, text, command, image_key=None): return VISUALS._make_toolbar_button(self, parent, text, command, image_key)
    def _set_font_stepper_geometry_from_asset(self, path): return VISUALS._set_font_stepper_geometry_from_asset(self, path)
    def _collect_toolbar_tokens_from_dir(self, folder_path, token_to_path): return VISUALS._collect_toolbar_tokens_from_dir(self, folder_path, token_to_path)
    def _load_toolbar_button_images_from_assets(self, style='A', mapping=None): return VISUALS._load_toolbar_button_images_from_assets(self, style, mapping)
    def _load_siindbad_toolbar_button_images(self): return VISUALS._load_siindbad_toolbar_button_images(self)
    def _load_toolbar_button_images(self): return VISUALS.load_toolbar_assets(self)
    def _refresh_toolbar_button_images(self): return VISUALS.refresh_theme_sprites(self)
    def _cancel_toolbar_refresh_after(self): return VISUALS._cancel_toolbar_refresh_after(self)
    def _run_toolbar_refresh_after(self): return VISUALS._run_toolbar_refresh_after(self)
    def _schedule_toolbar_refresh_after(self, delay_ms=1): return VISUALS._schedule_toolbar_refresh_after(self, delay_ms)
    @staticmethod
    def _theme_chip_palette(variant): return VISUALS._theme_chip_palette(variant)
    @staticmethod
    def _tree_variant_chip_palette(variant): return VISUALS._tree_variant_chip_palette(variant)
    def _footer_style_variant(self): return VISUALS._footer_style_variant(self)
    def _footer_visual_spec(self): return VISUALS._footer_visual_spec(self)
    def _bug_chip_palette(self, variant): return VISUALS._bug_chip_palette(self, variant)
    def _footer_badge_palette(self, variant): return VISUALS._footer_badge_palette(self, variant)
    def _build_bug_report_chip(self, parent): return VISUALS._build_bug_report_chip(self, parent)
    def _sync_bug_report_chip_colors(self): return VISUALS._sync_bug_report_chip_colors(self)
    def _on_bug_report_chip_enter(self, _event=None):
        self._bug_report_chip_hovered = True
        self._sync_bug_report_chip_colors()
    def _on_bug_report_chip_leave(self, _event=None):
        self._bug_report_chip_hovered = False
        self._sync_bug_report_chip_colors()
    def _load_bug_report_chip_icon(self, max_size=14, tint="#e6f6ff"):
        cache = getattr(self, "_bug_report_icon_cache", None)
        if cache is None:
            cache = {}
            self._bug_report_icon_cache = cache
        signature = (int(max_size), str(tint))
        cached = cache.get(signature)
        if cached is not None:
            return cached
        icon_path = os.path.join(self._resource_base_dir(), "assets", "buttons", "bug-report-icon.png")
        if not os.path.isfile(icon_path):
            self._bounded_cache_put(cache, signature, None, max_items=32)
            return None
        try:
            image_module = importlib.import_module("PIL.Image")
            with image_module.open(icon_path) as icon_file:
                icon = icon_file.convert("RGBA")
            alpha = icon.split()[-1]
            tint_hex = str(tint).strip().lstrip("#")
            if len(tint_hex) != 6:
                tint_hex = "e6f6ff"
            rgb = tuple(int(tint_hex[i:i + 2], 16) for i in (0, 2, 4))
            tinted = image_module.new("RGBA", icon.size, rgb + (0,))
            tinted.putalpha(alpha)
            icon = tinted
            if max_size and (icon.width > max_size or icon.height > max_size):
                scale = min(max_size / float(icon.width), max_size / float(icon.height))
                new_size = (
                    max(1, int(round(icon.width * scale))),
                    max(1, int(round(icon.height * scale))),
                )
                icon = icon.resize(new_size, image_module.LANCZOS)
            photo = self._pil_to_photo(icon)
            self._bounded_cache_put(cache, signature, photo, max_items=32)
            return photo
        except _EXPECTED_APP_ERRORS:
            self._bounded_cache_put(cache, signature, None, max_items=32)
            return None
    def _build_theme_selector(self, parent): return ui_build_service.build_theme_selector(self, parent, tk=tk)
    def _build_header_variant_switch(self, parent, show_title=True): return ui_build_service.build_header_variant_switch(self, parent, show_title, tk=tk)
    def _set_header_variant(self, variant):
        variant = str(variant).upper()
        if variant not in ("A", "B"):
            return
        self._header_variant = variant
        self._update_header_variant_controls()
        self._apply_footer_layout_variant()
        self._update_editor_mode_controls()
        try:
            self._refresh_runtime_theme_widgets()
        except _EXPECTED_APP_ERRORS:
            pass
    def _update_header_variant_controls(self):
        return ui_factory_service.update_header_variant_controls(
            self,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
    def _apply_footer_layout_variant(self): return footer_service._apply_footer_layout_variant(self)
    def _update_app_theme_controls(self):
        return ui_factory_service.update_app_theme_controls(
            self,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
    def _update_tree_style_controls(self):
        # Main editor lock: Tree style remains B.
        if str(getattr(self, "_tree_style_variant", "B")).upper() != "B":
            self._tree_style_variant = "B"
        active = "B"
        for variant, label in self._tree_style_labels.items():
            colors = self._tree_variant_chip_palette(variant)
            is_active = variant == active
            bg = colors["border"] if is_active else colors["bg"]
            try:
                label.configure(
                    bg=bg,
                    fg=colors["fg"],
                    highlightbackground=colors["border"],
                    highlightcolor=colors["border"],
                )
            except _EXPECTED_APP_ERRORS:
                continue
    def _set_tree_style_variant(self, variant):
        # Main editor lock: ignore external variant requests and keep B active.
        if str(getattr(self, "_tree_style_variant", "B")).upper() != "B":
            self._tree_style_variant = "B"
            self._tree_marker_icon_cache = {}
            self._apply_dark_theme()
            self._refresh_tree_item_markers()
        self._update_tree_style_controls()
    def _set_app_theme_variant(self, variant, save=True):
        switch_started = time.perf_counter()
        variant = str(variant).upper()
        if variant not in ("SIINDBAD", "KAMUE", "GLITCH"):
            return
        previous_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        previous_style = self._siindbad_effective_style()
        style_map = getattr(self, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B", "GLITCH": "B"}
            self._toolbar_style_variant_by_theme = style_map
        if variant not in style_map:
            style_map[variant] = "B"
        if variant == getattr(self, "_app_theme_variant", "SIINDBAD") and getattr(self, "_theme", None):
            self._update_app_theme_controls()
            return
        self._theme_switch_active = True
        try:
            self._app_theme_variant = variant
            self._apply_dark_theme()
            next_style = self._siindbad_effective_style()
            toolbar_host = getattr(self, "_toolbar_host", None)
            has_live_toolbar = (
                toolbar_host is not None
                and toolbar_host.winfo_exists()
                and bool(getattr(self, "_toolbar_buttons", {}))
                and previous_variant in ("SIINDBAD", "KAMUE", "GLITCH")
            )
            if has_live_toolbar and previous_style == "B" and next_style == "B":
                self._render_font_control()
                self._refresh_toolbar_button_images()
            else:
                self._rebuild_toolbar(preserve_find_text=True)
            self._refresh_runtime_theme_widgets()
            warmed = set(getattr(self, "_theme_prewarm_done", set()))
            queued = set(str(item).upper() for item in list(getattr(self, "_theme_prewarm_queue", []) or []))
            missing_variants = tuple(
                candidate
                for candidate in ("SIINDBAD", "KAMUE", "GLITCH")
                if candidate != variant and candidate not in warmed and candidate not in queued
            )
            if missing_variants:
                self._schedule_theme_asset_prewarm(targets=missing_variants, delay_ms=220)
            if save:
                try:
                    self._save_user_settings()
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    pass
            self._log_theme_perf(f"switch {previous_variant}->{variant}", started_ts=switch_started)
        finally:
            self._theme_switch_active = False
    def _refresh_runtime_theme_widgets(self): return theme_service._refresh_runtime_theme_widgets(self)
    @staticmethod
    def _startup_loader_lines(ready=False): return loader_service.startup_loader_lines(ready=ready)
    def _next_startup_loader_line(self, ready=False): return editor_purge_service._next_startup_loader_line(self, ready)
    def _show_startup_loader(self): return startup_loader_ui_service.show_startup_loader(
            self,
            tk=tk,
            time=time,
            startup_loader_core=startup_loader_core,
        )
    def _tick_startup_loader_progress(self):
        return ui_timer_service._tick_startup_loader_progress(**locals())
    def _tick_startup_loader_statement(self):
        return ui_timer_service._tick_startup_loader_statement(**locals())
    def _startup_loader_title_color_for_variant(self, variant): return loader_service.title_color_for_variant(
            variant,
            siindbad_palette=self._theme_palette_for_variant("SIINDBAD"),
            kamue_palette=self._theme_palette_for_variant("KAMUE"),
        )
    def _apply_startup_loader_title_variant(self): return editor_purge_service._apply_startup_loader_title_variant(self)
    def _tick_startup_loader_title(self): return editor_purge_service._tick_startup_loader_title(self)
    def _startup_loader_rounded_panel_photo(
        self,
        fill_hex,
        border_hex,
        width_px,
        height_px,
        border_px=1,
    ):
        width_px = max(2, int(width_px or 2))
        height_px = max(2, int(height_px or 2))
        border_px = max(1, int(border_px or 1))
        cache = getattr(self, "_startup_loader_panel_photo_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._startup_loader_panel_photo_cache = cache
        key = (
            str(fill_hex or "").lower(),
            str(border_hex or "").lower(),
            width_px,
            height_px,
            border_px,
        )
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            draw_module = importlib.import_module("PIL.ImageDraw")
            image_tk_module = importlib.import_module("PIL.ImageTk")
            aa = 3
            big_w = width_px * aa
            big_h = height_px * aa
            big_border = max(aa, border_px * aa)
            radius = max(aa * 2, int(round(min(big_w, big_h) * 0.44)))
            rgba = image_module.new("RGBA", (big_w, big_h), (0, 0, 0, 0))
            draw = draw_module.Draw(rgba)
            fill_color = str(fill_hex or "#0a1a2d")
            border_color = str(border_hex or "#3b5f81")
            draw.rounded_rectangle(
                (0, 0, max(0, big_w - 1), max(0, big_h - 1)),
                radius=radius,
                fill=fill_color,
                outline=border_color,
                width=big_border,
            )
            rgba = rgba.resize((width_px, height_px), image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(rgba)
            self._bounded_cache_put(cache, key, photo, max_items=256)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            self._bounded_cache_put(cache, key, None, max_items=256)
            return None
    @staticmethod
    def _set_startup_loader_bar_fill(fill_widget, pct): return editor_purge_service._set_startup_loader_bar_fill(fill_widget, pct)
    def _startup_loader_variant_progress(self, variant):
        variant = str(variant).upper()
        total = int(getattr(self, "_theme_prewarm_total_by_variant", {}).get(variant, 0) or 0)
        done = int(getattr(self, "_theme_prewarm_done_by_variant", {}).get(variant, 0) or 0)
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        if total <= 0:
            return 100.0 if variant in warmed else 0.0
        done = max(0, min(done, total))
        return float(done) * 100.0 / float(total)
    def _smooth_startup_loader_progress(self, target_pct: float, now_ts: float) -> float:
        target = max(0.0, min(100.0, float(target_pct or 0.0)))
        current = max(0.0, min(100.0, float(getattr(self, "_startup_loader_display_pct", 0.0) or 0.0)))
        if target <= current:
            self._startup_loader_last_progress_ts = float(now_ts)
            self._startup_loader_display_pct = current
            return current
        last_ts = float(getattr(self, "_startup_loader_last_progress_ts", 0.0) or 0.0)
        elapsed_ms = max(1.0, (float(now_ts) - last_ts) * 1000.0) if last_ts > 0 else 16.0
        rate = max(
            8.0,
            float(getattr(self, "_startup_loader_smooth_rate_pct_per_sec", 55.0) or 55.0),
        )
        max_step = max(0.1, (rate * elapsed_ms) / 1000.0)
        max_step = min(2.0, max_step)
        smoothed = target if (target - current) <= max_step else current + max_step
        smoothed = max(current, min(100.0, smoothed))
        self._startup_loader_last_progress_ts = float(now_ts)
        self._startup_loader_display_pct = smoothed
        return smoothed
    def _update_startup_loader_progress(self): return startup_loader_lifecycle_service.update_startup_loader_progress(
            self,
            time_module=time,
            startup_loader_core=startup_loader_core,
        )
    def _is_startup_full_load_ready(self): return startup_loader_lifecycle_service.is_startup_full_load_ready(
            self,
            startup_loader_core=startup_loader_core,
        )
    def _on_startup_full_load_ready(self): return startup_loader_lifecycle_service.on_startup_full_load_ready(
            self,
            tk_module=tk,
            time_module=time,
            startup_loader_core=startup_loader_core,
        )
    def _hide_startup_loader(self):
        # source-contract compatibility for legacy regression guards:
        # overlay_exists = False
        # overlay_exists = bool(overlay.winfo_exists())
        # except (tk.TclError, RuntimeError, AttributeError, ValueError):
        return startup_loader_lifecycle_service.hide_startup_loader(
            self,
            tk_module=tk,
            time_module=time,
            startup_loader_core=startup_loader_core,
        )
    @staticmethod
    def _restore_startup_root_alpha(target): return startup_loader_lifecycle_service.restore_startup_root_alpha(
            target,
            tk_module=tk,
        )
    def _log_theme_perf(self, label, started_ts=None):
        if not bool(getattr(self, "_theme_perf_logging", False)):
            return
        if started_ts is None:
            _LOG.debug("theme_perf label=%s", label)
            return
        elapsed = (time.perf_counter() - float(started_ts)) * 1000.0
        _LOG.debug("theme_perf label=%s elapsed_ms=%.1f", label, elapsed)
    def _build_theme_prewarm_tasks(self, variant): return theme_service.build_theme_prewarm_tasks(self, variant)
    def _execute_theme_prewarm_task(self, task): return theme_service._execute_theme_prewarm_task(self, task)
    def _finish_theme_prewarm_variant(self, variant): return theme_service.finish_theme_prewarm_variant(self, variant)
    def _schedule_theme_asset_prewarm(self, targets=None, delay_ms=120): return theme_service.schedule_theme_asset_prewarm(self, targets=targets, delay_ms=delay_ms)
    def _run_theme_asset_prewarm(self): return theme_service._run_theme_asset_prewarm(self)
    def _prewarm_theme_variant_assets(self, variant):
        tasks = self._build_theme_prewarm_tasks(variant)
        for task in tasks:
            try:
                self._execute_theme_prewarm_task(task)
            except (tk.TclError, RuntimeError, AttributeError, OSError, TypeError, ValueError, ImportError):
                continue
    def _set_toolbar_style_variant(self, variant):
        if not bool(getattr(self, "_show_toolbar_variant_controls", False)):
            return
        variant = str(variant).upper()
        if variant not in ("A", "B"):
            return
        current_theme = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if current_theme not in ("SIINDBAD", "KAMUE", "GLITCH"):
            self._update_toolbar_style_controls()
            return
        forced_focus = str(getattr(self, "_siindbad_style_focus", "")).upper()
        if forced_focus in ("A", "B") and variant != forced_focus:
            self._update_toolbar_style_controls()
            return
        current_style = self._siindbad_effective_style()
        if variant == current_style:
            return
        style_map = getattr(self, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B", "GLITCH": "B"}
            self._toolbar_style_variant_by_theme = style_map
        style_map[current_theme] = variant
        if current_theme == "SIINDBAD":
            self._toolbar_style_variant = variant
        self._invalidate_siindbad_b_sprite_cache()
        self._rebuild_toolbar(preserve_find_text=True)
        self._update_toolbar_style_controls()
    def _update_toolbar_style_controls(self):
        return ui_factory_service.update_toolbar_style_controls(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
    def _shade_toolbar_button_for_theme(self, image, cache_key=None): return asset_image_service.shade_toolbar_button_for_theme(
            self,
            image,
            cache_key=cache_key,
            importlib_module=importlib,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
    def _harmonize_kamue_b_outer_frame(self, image): return asset_image_service.harmonize_kamue_b_outer_frame(
            self,
            image,
            importlib_module=importlib,
        )
    def _load_toolbar_button_image(self, path, max_width=208, max_height=40, stretch_to_fit=False): return asset_image_service.load_toolbar_button_image(
            self,
            path,
            max_width=max_width,
            max_height=max_height,
            stretch_to_fit=stretch_to_fit,
            importlib_module=importlib,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )
    def _open_external_link(self, url):
        try:
            webbrowser.open_new_tab(url)
        except (webbrowser.Error, OSError, RuntimeError):
            messagebox.showerror("Open Link", f"Failed to open link:\n{url}")
    @staticmethod
    def _bind_click_recursive(widget, callback):
        widget.bind("<Button-1>", callback)
        try:
            widget.configure(cursor="hand2")
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        for child in widget.winfo_children():
            JsonEditor._bind_click_recursive(child, callback)
    @staticmethod
    def _extract_badge_boxes(image, threshold=16): return footer_service._extract_badge_boxes(image, threshold)
    def _load_credit_badge_sources(self):
        cached = getattr(self, "_credit_badge_sources_cache", None)
        if cached is not None:
            return cached
        path = os.path.join(self._resource_base_dir(), "assets", "buttons", "badges.png")
        if not os.path.isfile(path):
            self._credit_badge_sources_cache = []
            return []
        try:
            image_module = importlib.import_module("PIL.Image")
            source = theme_service.get_cached_rgba_image(self, path, image_module)
            if source is None:
                self._credit_badge_sources_cache = []
                return []
            boxes = self._extract_badge_boxes(source)
            if len(boxes) < 2:
                self._credit_badge_sources_cache = []
                return []
            result = [source.crop(box).copy() for box in boxes[:2]]
            self._credit_badge_sources_cache = result
            return result
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            self._credit_badge_sources_cache = []
            return []
    def _load_credit_github_icon(self, max_size=16, tint="#dff6ff", with_plate=False): return footer_service._load_credit_github_icon(self, max_size, tint, with_plate)
    def _load_credit_discord_icon(self, max_size=16, tint="#dff6ff", with_plate=False): return footer_service._load_credit_discord_icon(self, max_size, tint, with_plate)
    def _resize_pil_image_to_height(self, image, max_height):
        if not image or not max_height or image.height <= max_height:
            return image
        try:
            image_module = importlib.import_module("PIL.Image")
            scale = max_height / float(image.height)
            new_size = (max(1, int(round(image.width * scale))), max_height)
            return image.resize(new_size, image_module.LANCZOS)
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            return image
    def _enhance_badge_image(self, image):
        try:
            image_enhance_module = importlib.import_module("PIL.ImageEnhance")
            boosted = image_enhance_module.Contrast(image).enhance(1.18)
            boosted = image_enhance_module.Sharpness(boosted).enhance(1.28)
            return boosted
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            return image
    def _pil_to_photo(self, image):
        try:
            image_tk_module = importlib.import_module("PIL.ImageTk")
            return image_tk_module.PhotoImage(image)
        except (ImportError, OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            return None
    def _render_credit_badges(self): return footer_service._render_credit_badges(self)
    def _render_credit_discord_badges(self): return footer_service._render_credit_discord_badges(self)
    def _build_credit_badges(self, parent):
        self._credit_badge_host = parent
        self._render_credit_badges()
    def _build_credit_discord_badges(self, parent):
        self._credit_discord_badge_host = parent
        self._render_credit_discord_badges()
    @staticmethod
    def _is_banner_logo_path(path):
        name = os.path.basename(str(path)).lower()
        return name.startswith("logo2") or name.startswith("klogo") or name.startswith("glitch")
    def _clear_logo_widget(self):
        if self.logo_frame and self.logo_frame.winfo_exists():
            try:
                self.logo_frame.destroy()
            except _EXPECTED_APP_ERRORS:
                pass
        elif self.logo_label and self.logo_label.winfo_exists():
            try:
                self.logo_label.destroy()
            except _EXPECTED_APP_ERRORS:
                pass
        self.logo_frame = None
        self._logo_frame_inner = None
        self.logo_label = None
    def _update_logo_for_theme(self, force=False):
        return VISUALS._update_logo_for_theme(**locals())
    def _find_logo_path(self):
        return VISUALS._find_logo_path(**locals())
    def _resource_base_dir(self): return VISUALS._resource_base_dir(self, _module_resource_base_dir)
    def _set_window_icon(self):
        self._set_window_icon_for(self.root)
    def _set_window_icon_for(self, window):
        if window is None:
            return
        base_dir = self._resource_base_dir()
        candidates = ["S_icon.ico", "S_Icon.ico"]
        for name in candidates:
            icon_path = os.path.join(base_dir, "assets", name)
            if os.path.isfile(icon_path):
                try:
                    window.iconbitmap(icon_path)
                    return
                except _EXPECTED_APP_ERRORS:
                    continue
    def _build_logo_glow_frame(self, parent, image):
        theme = getattr(self, "_theme", {})
        bg = theme.get("bg", "#0f131a")
        # Match the active theme (blue for SIINDBAD, purple blend for KAMUE).
        glow_outer = theme.get("logo_border_outer", "#349fc7")
        glow_inner = theme.get("logo_border_inner", "#a9ddf0")
        outer = tk.Frame(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=glow_outer,
            highlightcolor=glow_outer,
        )
        inner = tk.Frame(
            outer,
            bg=bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=glow_inner,
            highlightcolor=glow_inner,
        )
        inner.pack(padx=0, pady=0)
        self._logo_frame_inner = inner
        self.logo_label = tk.Label(
            inner,
            image=image,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        self.logo_label.pack(padx=0, pady=0)
        return outer
    def _apply_logo_frame_theme(self):
        theme = getattr(self, "_theme", {})
        bg = theme.get("bg", "#0f131a")
        outer = theme.get("logo_border_outer", "#349fc7")
        inner = theme.get("logo_border_inner", "#a9ddf0")
        if self.logo_frame and self.logo_frame.winfo_exists():
            try:
                self.logo_frame.configure(
                    bg=bg,
                    highlightbackground=outer,
                    highlightcolor=outer,
                )
            except _EXPECTED_APP_ERRORS:
                pass
        if self._logo_frame_inner and self._logo_frame_inner.winfo_exists():
            try:
                self._logo_frame_inner.configure(
                    bg=bg,
                    highlightbackground=inner,
                    highlightcolor=inner,
                )
            except _EXPECTED_APP_ERRORS:
                pass
        if self.logo_label and self.logo_label.winfo_exists():
            try:
                self.logo_label.configure(bg=bg)
            except _EXPECTED_APP_ERRORS:
                pass
    def _load_logo_image(self, path): return asset_image_service.load_logo_image(
            self,
            path,
            importlib_module=importlib,
            os_module=os,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
            theme_service=theme_service,
        )
    @staticmethod
    def _kamue_readme_header_art():
        lines = [
            "888    d8P         d8888 888b     d888 888     888 8888888888",
            "888   d8P         d88888 8888b   d8888 888     888 888       ",
            "888  d8P         d88P888 88888b.d88888 888     888 888       ",
            "888d88K         d88P 888 888Y88888P888 888     888 8888888   ",
            "8888888b       d88P  888 888 Y888P 888 888     888 888       ",
            "888  Y88b     d88P   888 888  Y8P  888 888     888 888       ",
            "888   Y88b   d8888888888 888   \"   888 Y88b. .d88P 888       ",
            "888    Y88b d88P     888 888       888  \"Y88888P\"  8888888888",
        ]
        return "\n".join(lines)
    @staticmethod
    def _siindbad_readme_header_art():
        lines = [
            ".d8888. d888888b d8b   db d8888b. d8888b.  .d8b.  d8888b.",
            "88'  YP   `88'   888o  88 88  `8D 88  `8D d8' `8b 88  `8D",
            "`8bo.      88    88V8o 88 88   88 88oooY' 88ooo88 88   88",
            "  `Y8b.    88    88 V8o88 88   88 88~~~b. 88~~~88 88   88",
            "db   8D   .88.   88  V888 88  .8D 88   8D 88   88 88  .8D",
            "`8888Y' Y888888P VP   V8P Y8888D' Y8888P' YP   YP Y8888D'",
        ]
        return "\n".join(lines)
    @staticmethod
    def _center_multiline_block(block, width):
        centered = []
        for raw_line in str(block).splitlines():
            # Preserve trailing spaces so fixed-width ASCII art keeps its shape.
            line = raw_line
            if line == "":
                centered.append("")
                continue
            pad = max(0, (int(width) - len(line)) // 2)
            centered.append((" " * pad) + line)
        return "\n".join(centered)
    @staticmethod
    def _apply_readme_header(content, header_block, center_width=None):
        text = str(content or "")
        lines = text.splitlines()
        sep_idx = None
        for idx, line in enumerate(lines):
            if line.strip().startswith("==="):
                sep_idx = idx
                break
        header = str(header_block or "")
        if center_width is not None:
            header = JsonEditor._center_multiline_block(header, center_width)
        if sep_idx is None:
            return f"{header}\n\n{text}"
        tail = "\n".join(lines[sep_idx:])
        return f"{header}\n\n{tail}"
    def _apply_kamue_readme_header(self, content, center_width=None):
        header = self._kamue_readme_header_art()
        return self._apply_readme_header(content, header, center_width=center_width)
    def _apply_siindbad_readme_header(self, content, center_width=None):
        header = self._siindbad_readme_header_art()
        return self._apply_readme_header(content, header, center_width=center_width)
    @staticmethod
    def _format_readme_content(content, wrap_width): return editor_ui_core.EDITOR_UI.readme_ui_service.format_readme_content(content, wrap_width)
    def show_readme(self, position_hint=None): return editor_ui_core.EDITOR_UI.readme_ui_service.show_readme(
            self,
            position_hint=position_hint,
            tk_module=tk,
            ttk_module=ttk,
            tkfont_module=tkfont,
            messagebox_module=messagebox,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def set_status(self, msg):
        if self.status is not None:
            self.status.config(text=msg)

    def _begin_document_load_session(self) -> None:
        startup_loader_lifecycle_service.begin_document_load_session(self)

    def _end_document_load_session(self) -> None:
        startup_loader_lifecycle_service.end_document_load_session(
            self,
            time_module=time,
        )

    def _is_document_load_cooldown_active(self) -> bool:
        return startup_loader_lifecycle_service.is_document_load_cooldown_active(
            self,
            time_module=time,
        )

    def _finish_load_file_async(self, request_id: int, path: str, payload: object, error_text: str) -> None:
        startup_loader_lifecycle_service.finish_document_load_async(
            self,
            request_id,
            path,
            payload,
            error_text,
            document_service_module=document_service,
            messagebox_module=messagebox,
            time_module=time,
        )

    def _poll_load_file_async(self, request_id: int) -> None:
        startup_loader_lifecycle_service.poll_document_load_async(
            self,
            request_id,
            tk_module=tk,
            document_service_module=document_service,
            messagebox_module=messagebox,
            time_module=time,
        )

    def _load_file_async(self, path: str) -> None:
        startup_loader_lifecycle_service.load_file_async(
            self,
            path,
            os_module=os,
            threading_module=threading,
            json_module=json,
            tk_module=tk,
            document_service_module=document_service,
            messagebox_module=messagebox,
            time_module=time,
        )

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
        )
        if path:
            self._load_file_async(path)

    def load_file(self, path): return editor_purge_service.load_file(self, path)

    @staticmethod
    def _tree_marker_palette(theme_variant): return theme_service.tree_marker_palette(theme_variant)

    @staticmethod
    def _sha256_file(path): return tree_engine_service.sha256_file(path)

    def _check_tree_marker_integrity(self): return tree_engine_service.check_tree_marker_integrity(
            self,
            os_module=os,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _load_tree_marker_icon(self, kind, selected=False, expandable=False, expanded=False): return tree_engine_service.load_tree_marker_icon(
            self,
            kind,
            selected=selected,
            expandable=expandable,
            expanded=expanded,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    @staticmethod
    def _nudge_marker_image_y(image, delta_y=-1.0): return tree_engine_service.nudge_marker_image_y(
            image,
            delta_y=delta_y,
        )

    def _is_input_red_arrow_root_path(self, path): return tree_policy_service.should_use_input_red_arrow_for_path(self, path)

    def _is_input_database_locked_subcategory_path(self, path): return input_mode_render_dispatch_service.is_input_database_locked_subcategory_path(self, path)

    def _load_input_bank_red_arrow_icon(self, expandable=False, expanded=False): return tree_engine_service.load_input_bank_red_arrow_icon(
            self,
            expandable=expandable,
            expanded=expanded,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _refresh_tree_item_markers(self):
        tree_engine_service.refresh_tree_item_markers(self)

    def _refresh_tree_marker_for_item(self, item_id, selected=False):
        tree_engine_service.refresh_tree_marker_for_item(self, item_id, selected=selected)

    def _rebuild_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.item_to_path.clear()
        self._last_tree_selected_item = None
        self._input_mode_force_refresh = True
        self._reset_find_state()

        # Render top-level categories under Tk's implicit root (hidden "root" row).
        # Keep [] as the root path so data/export behavior stays unchanged.
        self.item_to_path[""] = []
        self._populate_children("")
        self._refresh_tree_item_markers()

    def _rebuild_tree_for_mode_change(self):
        tree = getattr(self, "tree", None)
        if tree is None:
            return
        if getattr(self, "data", None) is None:
            return
        previous_item = None
        previous_path = None
        try:
            previous_item = tree.focus()
            previous_path = self.item_to_path.get(previous_item)
        except (tk.TclError, RuntimeError, AttributeError):
            previous_item = None
            previous_path = None
        self._rebuild_tree()
        target_item = None
        try:
            if isinstance(previous_path, list):
                target_item = self._ensure_tree_item_for_path(previous_path)
            elif (
                isinstance(previous_path, tuple)
                and len(previous_path) == 3
                and previous_path[0] == "__group__"
            ):
                target_item = self._ensure_tree_group_item_loaded(previous_path[1], previous_path[2])
            if target_item:
                self._open_to_item(target_item)
                tree.focus(target_item)
                tree.selection_set(target_item)
                tree.see(target_item)
        except (tk.TclError, RuntimeError, AttributeError, KeyError, IndexError, TypeError, ValueError):
            pass

    def _enforce_input_tree_expand_locks(self):
        # Collapse INPUT no-expand categories/groups even when tree state was expanded in JSON mode.
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        tree = getattr(self, "tree", None)
        if tree is None:
            return
        try:
            if not tree.winfo_exists():
                return
        except _EXPECTED_APP_ERRORS:
            return

        items = self._collect_tree_items("")
        locked_ids = set()
        for item_id in items:
            if not self._is_input_tree_expand_blocked(item_id):
                continue
            try:
                tree.item(item_id, open=False)
                locked_ids.add(item_id)
            except _EXPECTED_APP_ERRORS:
                continue

        if not locked_ids:
            return

        # Keep selection visible/valid when the selected node is inside a locked branch.
        try:
            focused = tree.focus()
        except _EXPECTED_APP_ERRORS:
            focused = ""
        if not focused:
            return

        target = None
        cursor = focused
        while cursor:
            parent = ""
            try:
                parent = tree.parent(cursor)
            except _EXPECTED_APP_ERRORS:
                parent = ""
            if parent in locked_ids:
                target = parent
                break
            cursor = parent

        if not target:
            return
        try:
            tree.focus(target)
            tree.selection_set(target)
            tree.see(target)
        except _EXPECTED_APP_ERRORS:
            return

    def _add_placeholder_if_container(self, item_id, value):
        if isinstance(value, (dict, list)) and len(value) > 0:
            self.tree.insert(item_id, "end", text="(loading)")

    def _reset_find_state(self):
        self.find_matches = []
        self.find_index = 0
        self.last_find_query = ""
        self._find_search_entries = []
        self._json_find_path_token_cache = {}
        self._json_find_last_query = ""
        self._json_find_tag_widget = None
        self._find_last_root_item = ""
        text_widget = getattr(self, "text", None)
        if text_widget is not None:
            try:
                text_widget.tag_remove("find_next_match", "1.0", "end")
            except _EXPECTED_APP_ERRORS:
                pass

    def _collect_tree_items(self, root_id=""):
        items = []
        for child in self.tree.get_children(root_id):
            items.append(child)
            items.extend(self._collect_tree_items(child))
        return items

    def _open_to_item(self, item_id):
        parent = self.tree.parent(item_id)
        while parent:
            self.tree.item(parent, open=True)
            parent = self.tree.parent(parent)

    def _build_find_search_index(self):
        entries = []
        self._append_find_search_entries([], self.data, entries)
        return entries

    @staticmethod
    def _find_search_value_summary(value, max_tokens=24, max_chars=360): return tree_navigation_service.find_search_value_summary(
            value,
            max_tokens=max_tokens,
            max_chars=max_chars,
        )

    def _append_find_search_entries(self, path, value, entries): return editor_purge_service._append_find_search_entries(self, path, value, entries)

    def _ensure_tree_item_for_path(self, target_path):
        TREE_NAV = getattr(self, "TREE_NAV", None)
        if TREE_NAV is None:
            TREE_NAV = tree_navigation_service.bind(
                self,
                expected_errors=_EXPECTED_APP_ERRORS,
            )
            self.TREE_NAV = TREE_NAV
        return TREE_NAV.resolve_path(target_path)

    def _network_group_for_list_index(self, list_path, row_index):
        # Regression contract marker: TREE_NAV.get_group_for_index(list_path, row_index)
        return input_mode_service._network_group_for_list_index(**locals())

    def _resolve_grouped_list_item(self, current_item, prefix):
        TREE_NAV = getattr(self, "TREE_NAV", None)
        if TREE_NAV is None:
            TREE_NAV = tree_navigation_service.bind(
                self,
                expected_errors=_EXPECTED_APP_ERRORS,
            )
            self.TREE_NAV = TREE_NAV
        return TREE_NAV.resolve_grouped_list_item(current_item, prefix)

    def _ensure_tree_group_item_loaded(self, list_path, group):
        TREE_NAV = getattr(self, "TREE_NAV", None)
        if TREE_NAV is None:
            TREE_NAV = tree_navigation_service.bind(
                self,
                expected_errors=_EXPECTED_APP_ERRORS,
            )
            self.TREE_NAV = TREE_NAV
        return TREE_NAV.ensure_group_item_loaded(list_path, group)

    def find_next(self, event=None): return json_view_manager.JSON_VIEW.json_find_orchestrator_service.find_next(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _collapse_previous_find_root_if_category_changed(self, next_item_id):
        json_find_nav_service.collapse_previous_find_root_if_category_changed(self, next_item_id)

    def _build_json_find_matches(self, query_lower): return json_find_service.build_json_find_matches(self, query_lower)

    def _filter_json_find_matches(self, prior_matches, query_lower): return json_find_service.filter_json_find_matches(self, prior_matches, query_lower)

    def _find_next_json_text_match(self, query): return json_text_find_service.find_next_json_text_match(self, query)

    def _focus_json_find_match(self, query):
        json_text_find_service.focus_json_find_match(self, query)

    def _find_next_input_mode(self):
        input_mode_find_service.find_next_input_mode(self, tk_module=tk)

    def _build_input_mode_search_entries(self): return input_mode_find_service.build_input_mode_search_entries(self, tk_module=tk)

    @staticmethod
    def _find_first_entry_descendant(root_widget): return input_mode_find_service.find_first_entry_descendant(root_widget, tk_module=tk)

    def _scroll_input_widget_into_view(self, widget):
        input_mode_find_service.scroll_input_widget_into_view(self, widget)

    def _populate_children(self, item_id):
        tree_engine_service.populate_children(self, item_id)

    @staticmethod
    def _is_database_table_rows_path(path): return input_mode_render_dispatch_service.is_database_table_rows_path(path)

    @staticmethod
    def _database_table_row_label(idx, item): return label_format_service.database_table_row_label(idx, item)

    def on_expand(self, event):
        return ui_timer_service.on_expand(**locals())

    def on_collapse(self, event):
        self._refresh_tree_item_markers()

    def _tree_item_can_toggle(self, item_id): return tree_engine_service.tree_item_can_toggle(self, item_id)

    def _on_tree_click_toggle(self, event): return tree_engine_service.on_tree_click_toggle(self, event)

    def _on_tree_double_click_guard(self, event): return tree_engine_service.on_tree_double_click_guard(self, event)

    def on_select(self, event):
        self._mark_tree_interaction_active()
        item_id = self.tree.focus()
        if not item_id:
            return
        previous_item = str(getattr(self, "_last_tree_selected_item", "") or "")
        if previous_item and previous_item != item_id:
            self._refresh_tree_marker_for_item(previous_item, selected=False)
        self._refresh_tree_marker_for_item(item_id, selected=True)
        self._last_tree_selected_item = item_id
        self._auto_apply_pending = False
        self._destroy_error_overlay()
        self._clear_json_error_highlight()
        self._error_visual_mode = "guide"
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
            self._schedule_input_mode_refresh(item_id=item_id, immediate=False)
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            _, list_path, group = path
            value = self._get_value(list_path)
            group_items = input_mode_service.collect_group_items_for_selection(self, list_path, value, group)
            if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
                if self._can_skip_input_mode_refresh(item_id, list_path):
                    self.set_status(f"group {group} ({len(group_items)})")
                    return
                self._refresh_input_mode_fields(list_path, group_items)
            else:
                self._show_value(group_items, path=list_path)
            self.set_status(f"group {group} ({len(group_items)})")
            return
        value = self._get_value(path)
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
            if self._can_skip_input_mode_refresh(item_id, path):
                self.set_status(self._describe(value))
                self._update_find_controls_for_mode()
                return
            self._refresh_input_mode_fields(path, value)
            self._update_find_controls_for_mode()
        else:
            self._show_value(value, path=path)
        self.set_status(self._describe(value))

    def _show_value(self, value, path=None):
        json_view_render_service.show_value(self, value, path=path)

    def _initial_highlight_line_limit(self): return json_view_render_service.initial_highlight_line_limit(self)

    def _cancel_pending_json_view_lock_state(self):
        json_view_render_service.cancel_pending_json_view_lock_state(self)

    def _schedule_json_view_lock_state(self, path, render_seq=None):
        json_view_render_service.schedule_json_view_lock_state(
            self,
            path,
            render_seq=render_seq,
        )

    def _json_lock_tag_palette(self):
        return theme_service.json_lock_tag_palette(
            str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        )

    def _configure_json_lock_tags(self): return json_diagnostics_service._configure_json_lock_tags(self)

    def _clear_json_lock_highlight(self): return json_diagnostics_service._clear_json_lock_highlight(self)

    def _set_json_text_editable(self, editable=True): return json_diagnostics_service._set_json_text_editable(self, editable)

    # H-UI-05: extracted JSON repair/diagnostics routing is bound via json_engine.repair_dispatch.

    def _on_text_keypress(self, event): return json_diagnostics_service._on_text_keypress(self, event)

    def _on_text_nav_attempt(self, event): return json_diagnostics_service._on_text_nav_attempt(self, event)

    def _is_index_on_error_line(self, index): return json_diagnostics_service._is_index_on_error_line(self, index)

    def _line_number_from_index(self, index): return json_diagnostics_service._line_number_from_index(self, index)

    def _preferred_error_insert_index(self, line, fallback_index): return json_diagnostics_service._preferred_error_insert_index(self, line, fallback_index)

    def _enforce_error_focus(self):
        if not self._error_focus_index:
            return
        try:
            self.text.mark_set("insert", self._error_focus_index)
            self.text.see(self._error_focus_index)
        except _EXPECTED_APP_ERRORS:
            return

    def _on_text_keyrelease(self, event):
        try:
            keysym = getattr(event, "keysym", "") or ""
            char = getattr(event, "char", "") or ""
            is_edit_key = bool(char) or keysym in ("BackSpace", "Delete", "Return", "KP_Enter", "space")
            if not is_edit_key:
                return
            if not self._auto_apply_pending:
                return
            if self._auto_apply_in_progress:
                return
            if self._can_auto_apply_current_edit():
                self._auto_apply_in_progress = True
                self._auto_apply_pending = False
                self._cancel_live_feedback_timer()
                try:
                    self._error_visual_mode = "guide"
                    self.apply_edit()
                finally:
                    self._auto_apply_in_progress = False
            else:
                # User is actively fixing but still wrong: debounce expensive live parse/validation.
                self._schedule_live_error_feedback()
        except _EXPECTED_APP_ERRORS:
            return

    def _cancel_live_feedback_timer(self):
        return ui_timer_service._cancel_live_feedback_timer(**locals())

    def _schedule_live_error_feedback(self):
        return ui_timer_service._schedule_live_error_feedback(**locals())

    def _run_live_error_feedback(self):
        return ui_timer_service._run_live_error_feedback(**locals())

    def _can_auto_apply_current_edit(self): return json_edit_flow_service.can_auto_apply_current_edit(self)

    def _show_live_error_feedback(self): return editor_purge_service._show_live_error_feedback(self)

    def _show_error_overlay(self, title, message, actions=None): return editor_purge_service._show_error_overlay(self, title, message, actions)

    def _destroy_error_overlay(self):
        error_overlay_service.destroy_error_overlay(self)

    def _apply_error_tint(self):
        error_overlay_service.apply_error_tint(self)

    def _clear_error_tint(self):
        error_overlay_service.clear_error_tint(self)

    def _refresh_active_error_theme(self):
        error_overlay_service.refresh_active_error_theme(self)

    def save_file(self): return editor_purge_service.save_file(self)

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            title="Save JSON",
            defaultextension=".json",
            filetypes=[("All Files", "*.*"), ("JSON", "*.json")],
        )
        if not path:
            return
        self.path = path
        self.save_file()

    def export_hhsave(self): return editor_purge_service.export_hhsave(self)

    def _get_value(self, path): return json_path_service.get_value(self.data, path)

    def _set_value(self, path, new_value): return editor_purge_service._set_value(self, path, new_value)

    def _is_network_list(self, path, value): return highlight_label_service.is_network_list(path, value, self.network_types_set)

    def _find_first_dict_key_change(self, old_value, new_value, current_path=None): return label_format_service.find_first_dict_key_change(old_value, new_value, current_path=current_path)

    def _is_json_edit_allowed(self, path, new_value, show_feedback=True, auto_restore=False):
        # Orange lock system now runs as label-only guidance:
        # keep highlight tags, but do not block/restore edits or show lock overlays.
        # Delegated lock policies still rely on highlight_label_service.is_locked_field_path checks.
        # Contract note: callers may still pass auto_restore=True for regression compatibility.
        # Legacy warning actions "Auto-Fix" and "Continue" remain delegated in edit guard flow.
        _ = (path, new_value, show_feedback, auto_restore)
        return True

    def _is_edit_allowed(self, path, new_value): return editor_purge_service._is_edit_allowed(self, path, new_value)

    def _network_context(self, path): return highlight_label_service.network_context(
            path=path,
            value_getter=self._get_value,
            network_types_set=self.network_types_set,
        )


# H-UI-05: bind extracted JSON repair/diagnostic wrappers onto JsonEditor.
for _repair_method_name in json_repair_dispatch_service.dispatch_method_names():
    setattr(
        JsonEditor,
        _repair_method_name,
        json_repair_dispatch_service.build_editor_method(_repair_method_name),
    )


def main():
    path = None
    if len(sys.argv) > 1:
        path = sys.argv[1]
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    setattr(root, "_hh_use_startup_loader_window", True)
    root.withdraw()
    JsonEditor(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
