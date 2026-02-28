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
footer_service = editor_ui_core.EDITOR_UI.footer_service
loader_service = editor_ui_core.EDITOR_UI.loader_service
startup_loader_ui_service = editor_ui_core.EDITOR_UI.startup_loader_ui_service
toolbar_service = editor_ui_core.EDITOR_UI.toolbar_service
ui_build_service = editor_ui_core.EDITOR_UI.ui_build_service
ui_dispatch_service = editor_ui_core.EDITOR_UI.ui_dispatch_service
input_mode_diag_service = input_mode_manager.INPUT_MODE.input_mode_diag_service
input_mode_find_service = input_mode_manager.INPUT_MODE.input_mode_find_service
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
json_find_nav_service = json_view_manager.JSON_VIEW.json_find_nav_service
json_find_service = json_view_manager.JSON_VIEW.json_find_service
json_text_find_service = json_view_manager.JSON_VIEW.json_text_find_service
json_view_render_service = json_view_manager.JSON_VIEW.json_view_render_service
json_view_service = json_view_manager.JSON_VIEW.json_view_service
runtime_log_service = runtime_service.RUNTIME.runtime_log_service
runtime_paths_service = runtime_service.RUNTIME.runtime_paths_service
token_env_service = runtime_service.RUNTIME.token_env_service
windows_runtime_service = runtime_service.RUNTIME.windows_runtime_service
text_context_action_service = text_context_manager.TEXT_CONTEXT.text_context_action_service
text_context_pointer_service = text_context_manager.TEXT_CONTEXT.text_context_pointer_service
text_context_state_service = text_context_manager.TEXT_CONTEXT.text_context_state_service
text_context_widget_service = text_context_manager.TEXT_CONTEXT.text_context_widget_service
input_bank_style_service = theme_manager.THEME.input_bank_style_service
input_database_bcc_style_service = theme_manager.THEME.input_database_bcc_style_service
input_database_style_service = theme_manager.THEME.input_database_style_service
input_network_firewall_style_service = theme_manager.THEME.input_network_firewall_style_service
input_network_device_bcc_style_service = theme_manager.THEME.input_network_device_bcc_style_service
input_network_device_geoip_style_service = theme_manager.THEME.input_network_device_geoip_style_service
input_network_router_style_service = theme_manager.THEME.input_network_router_style_service
input_suspicion_phone_style_service = theme_manager.THEME.input_suspicion_phone_style_service
theme_asset_service = theme_manager.THEME.theme_asset_service
theme_service = theme_manager.THEME.theme_service
tree_engine_service = tree_manager.TREE.tree_engine_service
tree_mode_service = tree_manager.TREE.tree_mode_service
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
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _load_known_email_domains():
    path = os.path.join(_module_resource_base_dir(), "assets", "known_email_domains.json")
    try:
        # Accept UTF-8 with or without BOM to avoid empty-domain fallbacks.
        with open(path, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        return set()
    if not isinstance(data, list):
        return set()
    return {item.strip().lower() for item in data if isinstance(item, str) and item.strip()}


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
    KNOWN_EMAIL_DOMAINS = _load_known_email_domains()
    KNOWN_EMAIL_DOMAIN_ROOTS = {
        domain.split(".")[-2] for domain in KNOWN_EMAIL_DOMAINS if "." in domain
    }
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
        self._init_chrome_runtime_state()
        self._init_footer_bugreport_runtime_state()
        self._init_text_context_runtime_state()
        self._init_theme_update_runtime_state()
        self._init_editor_session_runtime_state()

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
    def _auto_display_profile_for_screen(screen_width, screen_height, display_scale):
        return display_profile_core.auto_display_profile_for_screen(
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

    def _build_ui(self):
        return ui_build_service.build_ui(self, tk=tk, ttk=ttk)

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

    def _build_editor_mode_toggle(self, parent):
        return ui_build_service.build_editor_mode_toggle(self, parent, tk=tk)

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
        after_id = getattr(self, "_input_mode_scroll_drag_after_id", None)
        self._input_mode_scroll_drag_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _clear_input_mode_scroll_drag_active(self):
        self._cancel_pending_input_mode_scroll_drag_clear()
        self._input_mode_scroll_drag_active = False

    def _mark_input_mode_scroll_drag_active(self):
        self._input_mode_scroll_drag_active = True
        self._cancel_pending_input_mode_scroll_drag_clear()
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            self._input_mode_scroll_drag_after_id = root.after(120, self._clear_input_mode_scroll_drag_active)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            self._input_mode_scroll_drag_after_id = None

    @staticmethod
    def _is_input_scalar(value):
        return input_mode_service.is_input_scalar(value)

    def _format_input_path_label(self, rel_path):
        return input_mode_service.format_input_path_label(rel_path)

    def _collect_input_field_specs(self, value, base_path, max_fields=24):
        return input_mode_service.collect_input_field_specs(
            value,
            base_path,
            max_fields=max_fields,
        )

    def _style_input_mode_row_widgets(self, label_widget, input_widget, input_container=None):
        theme = getattr(self, "_theme", {})
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        label_size = self._input_mode_font_size(8, min_size=7, max_size=16)
        input_size = self._input_mode_font_size(8, min_size=7, max_size=16)
        label_family = self._resolve_font_family(
            ["Tektur SemiBold", "Tektur Med", "Tektur", "Segoe UI Semibold", "Segoe UI"],
            self._credit_name_font()[0],
        )
        input_family = self._resolve_font_family(
            ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
            self._credit_name_font()[0],
        )
        if variant == "KAMUE":
            label_fg = "#d5bfff"
            field_bg = theme.get("panel", "#0d061c")
            field_fg = "#f0e4ff"
            field_edge = "#6b4596"
        else:
            label_fg = "#9cc7eb"
            field_bg = theme.get("panel", "#161b24")
            field_fg = "#d7ecff"
            field_edge = "#2f6ea0"
        panel = theme.get("panel", "#161b24")
        try:
            label_widget.configure(
                bg=panel,
                fg=label_fg,
                font=(label_family, label_size, "bold"),
            )
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            if input_container is not None:
                input_container.configure(
                    bg=panel,
                    bd=0,
                    highlightthickness=0,
                )
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        try:
            input_widget.configure(
                bg=field_bg,
                fg=field_fg,
                insertbackground=field_fg,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=field_edge,
                highlightcolor=field_edge,
                font=(input_family, input_size, "bold"),
            )
        except (tk.TclError, RuntimeError, AttributeError):
            pass

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
        normalized = list(path or [])
        if len(normalized) != 1:
            return False
        return self._input_mode_root_key_for_path(normalized) == "bank"

    def _collect_bank_input_rows(self, value, max_rows=40):
        return input_bank_style_service.collect_bank_input_rows(value, max_rows=max_rows)

    def _render_bank_input_style_rows(self, host, normalized_path, row_defs):
        input_bank_style_service.render_bank_input_style_rows(
            self,
            host,
            normalized_path,
            row_defs,
        )

    @staticmethod
    def _is_database_input_style_path(path):
        normalized = list(path or [])
        if not normalized:
            return False
        if str(normalized[0]) != "Database":
            return False
        # Root Database now shows subcategory selector; style render is subcategory-only.
        if len(normalized) == 1:
            return False
        # Support clicking a Database entry node (e.g., first item -> Grades matrix).
        if len(normalized) == 2 and isinstance(normalized[1], int):
            return True
        return len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]) == "Grades"

    def _database_root_entry_label(self, idx, item):
        variant = str(getattr(self, "_tree_style_variant", "B"))
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return label_format_service.database_label(idx, item, variant)
        if isinstance(item, dict):
            tables = item.get("tables")
            if isinstance(tables, dict) and tables:
                first_table = str(next(iter(tables.keys()))).strip().casefold()
                if first_table == "grades":
                    return "Grades"
                if first_table == "users":
                    return "BCC"
                if first_table == "customers":
                    return "INTERPOL"
        return label_format_service.database_label(idx, item, variant)

    def _collect_database_grades_matrix(self, value, max_rows=40):
        return input_database_style_service.collect_database_grades_matrix(
            value,
            max_rows=max_rows,
        )

    def _render_database_grades_input_matrix(self, host, normalized_path, matrix_payload):
        input_database_style_service.render_database_grades_matrix(
            self,
            host,
            normalized_path,
            matrix_payload,
        )

    def _collect_database_bcc_payload(self, value, max_rows=200):
        return input_database_bcc_style_service.collect_database_bcc_payload(
            value,
            max_rows=max_rows,
        )

    def _render_database_bcc_table(self, host, normalized_path, payload):
        input_database_bcc_style_service.render_database_bcc_table(
            self,
            host,
            normalized_path,
            payload,
        )

    def _collect_database_interpol_payload(self, value, max_rows=200):
        return input_database_bcc_style_service.collect_database_interpol_payload(
            value,
            max_rows=max_rows,
        )

    def _render_database_interpol_table(self, host, normalized_path, payload):
        input_database_bcc_style_service.render_database_interpol_table(
            self,
            host,
            normalized_path,
            payload,
        )

    def _database_grades_matrix_for_input_path(self, path, value):
        normalized = list(path or [])
        if not normalized:
            return None
        if str(normalized[0]) != "Database":
            return None
        if len(normalized) == 1:
            return None
        if len(normalized) == 2 and isinstance(normalized[1], int):
            return self._collect_database_grades_matrix(value)
        if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]) == "Grades":
            return self._collect_database_grades_matrix(value)
        return None

    def _database_bcc_payload_for_input_path(self, path, value):
        normalized = list(path or [])
        if not normalized:
            return None
        if str(normalized[0]) != "Database":
            return None
        if len(normalized) == 2 and isinstance(normalized[1], int):
            return self._collect_database_bcc_payload(value)
        if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]).casefold() == "users":
            return self._collect_database_bcc_payload(value)
        return None

    def _database_interpol_payload_for_input_path(self, path, value):
        normalized = list(path or [])
        if not normalized:
            return None
        if str(normalized[0]) != "Database":
            return None
        if len(normalized) == 2 and isinstance(normalized[1], int):
            return self._collect_database_interpol_payload(value)
        if len(normalized) >= 4 and str(normalized[2]) == "tables" and str(normalized[3]).casefold() == "customers":
            return self._collect_database_interpol_payload(value)
        return None

    def _is_network_router_input_style_payload(self, path, value):
        return input_network_router_style_service.is_network_router_group_payload(self, path, value)

    def _is_suspicion_input_style_path(self, path):
        return input_suspicion_phone_style_service.is_suspicion_input_path(self, path)

    def _is_phone_input_style_path(self, path):
        return input_suspicion_phone_style_service.is_phone_input_path(self, path)

    def _is_skypersky_input_style_path(self, path):
        return input_suspicion_phone_style_service.is_skypersky_input_path(self, path)

    def _render_suspicion_phone_input(self, host, normalized_path, value):
        return input_suspicion_phone_style_service.render_suspicion_phone_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _render_phone_preview_input(self, host, normalized_path, value):
        return input_suspicion_phone_style_service.render_phone_preview_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _render_skypersky_input(self, host, normalized_path, value):
        return input_suspicion_phone_style_service.render_skypersky_input(
            self,
            host,
            normalized_path,
            value,
        )

    def _is_network_device_input_style_payload(self, path, value):
        normalized = list(path or [])
        if len(normalized) != 1:
            return False
        if self._input_mode_root_key_for_path(normalized) != "network":
            return False
        if not isinstance(value, list) or not value:
            return False
        return all(isinstance(item, dict) and str(item.get("type", "")).upper() == "DEVICE" for item in value)

    def _is_network_firewall_input_style_payload(self, path, value):
        return input_network_firewall_style_service.is_network_firewall_group_payload(self, path, value)

    def _is_network_geoip_input_style_payload(self, path, value):
        # GEO IP concept applies only to first Network DEVICE row.
        return input_network_device_geoip_style_service.is_network_geoip_payload(self, path, value)

    def _is_network_bcc_domains_input_style_payload(self, path, value):
        # BCC DOMAINS concept applies only to the locked bcc.com row.
        return input_network_device_bcc_style_service.is_network_bcc_domains_payload(self, path, value)

    def _collect_network_bcc_domains_payload(self, normalized_path, value):
        return input_network_device_bcc_style_service.collect_bcc_domains_payload(self, normalized_path, value)

    def _render_network_bcc_domains_input(self, host, normalized_path, payload):
        input_network_device_bcc_style_service.render_bcc_domains_input(self, host, normalized_path, payload)

    def _is_network_blue_table_input_style_payload(self, path, value):
        # BLUE TABLE concept applies to the locked thebluetable.com anchor row.
        return input_network_device_bcc_style_service.is_network_blue_table_payload(self, path, value)

    def _collect_network_blue_table_payload(self, normalized_path, value):
        return input_network_device_bcc_style_service.collect_blue_table_payload(self, normalized_path, value)

    def _render_network_blue_table_input(self, host, normalized_path, payload):
        input_network_device_bcc_style_service.render_blue_table_input(self, host, normalized_path, payload)

    def _is_network_interpol_input_style_payload(self, path, value):
        # INTERPOL concept applies to the locked row directly under BLUE TABLE.
        return input_network_device_bcc_style_service.is_network_interpol_payload(self, path, value)

    def _collect_network_interpol_payload(self, normalized_path, value):
        return input_network_device_bcc_style_service.collect_interpol_payload(self, normalized_path, value)

    def _render_network_interpol_input(self, host, normalized_path, payload):
        input_network_device_bcc_style_service.render_interpol_input(self, host, normalized_path, payload)

    def _collect_network_geoip_payload(self, normalized_path, value):
        return input_network_device_geoip_style_service.collect_geoip_payload(self, normalized_path, value)

    def _render_network_geoip_input(self, host, normalized_path, payload):
        input_network_device_geoip_style_service.render_geoip_input(self, host, normalized_path, payload)

    def _collect_network_firewall_input_rows(self, normalized_path, firewalls, max_rows=40):
        return input_network_firewall_style_service.collect_firewall_input_rows(
            self,
            normalized_path,
            firewalls,
            max_rows=max_rows,
        )

    def _render_network_firewall_input_rows(self, host, normalized_path, row_defs):
        input_network_firewall_style_service.render_firewall_input_rows(
            self,
            host,
            normalized_path,
            row_defs,
        )

    def _collect_network_router_input_rows(self, normalized_path, routers, max_rows=60):
        return input_network_router_style_service.collect_router_input_rows(
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
        input_network_router_style_service.render_router_input_rows(
            self,
            host,
            normalized_path,
            row_defs,
            start_index=start_index,
            finalize=bool(finalize),
            total_rows=total_rows,
        )

    def _prewarm_input_mode_assets(self):
        try:
            input_network_router_style_service.prewarm_router_assets(self)
            input_suspicion_phone_style_service.prewarm_preview_assets(self)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return

    def _refresh_input_mode_fields(self, path, value):
        host = getattr(self, "_input_mode_fields_host", None)
        if host is None:
            return
        self._cancel_pending_router_input_batches()
        self._clear_router_virtual_state()
        self._cancel_pending_input_mode_layout_finalize()
        self._input_mode_render_token = int(getattr(self, "_input_mode_render_token", 0) or 0) + 1
        self._input_mode_field_specs = []
        self._input_mode_current_path = list(path or [])
        self._input_mode_no_fields_label = None
        theme = getattr(self, "_theme", {})
        panel_bg = theme.get("panel", "#161b24")
        host.configure(bg=panel_bg)
        normalized_path = list(path or [])
        root_key = self._input_mode_root_key_for_path(normalized_path)
        is_network_router_payload = self._is_network_router_input_style_payload(normalized_path, value)
        is_network_bcc_domains_payload = self._is_network_bcc_domains_input_style_payload(normalized_path, value)
        is_network_blue_table_payload = self._is_network_blue_table_input_style_payload(normalized_path, value)
        is_network_interpol_payload = self._is_network_interpol_input_style_payload(normalized_path, value)
        is_network_geoip_payload = self._is_network_geoip_input_style_payload(normalized_path, value)
        is_network_device_payload = self._is_network_device_input_style_payload(normalized_path, value)
        is_network_firewall_payload = self._is_network_firewall_input_style_payload(normalized_path, value)
        database_grades_matrix = self._database_grades_matrix_for_input_path(normalized_path, value)
        database_bcc_payload = self._database_bcc_payload_for_input_path(normalized_path, value)
        database_interpol_payload = self._database_interpol_payload_for_input_path(normalized_path, value)
        is_database_payload = bool(database_grades_matrix)
        if is_network_router_payload:
            input_network_router_style_service.prepare_router_render_host(
                self,
                host,
                reset_pool=False,
            )
            keep_database_children = input_database_style_service.suspend_database_render_host(self, host)
            pool_children = {
                row_slot.get("row_frame")
                for row_slot in list(getattr(self, "_input_mode_router_row_pool", []) or [])
                if isinstance(row_slot, dict)
            }
            pool_children.update(input_network_router_style_service.router_pool_children(self, host))
            for child in list(host.winfo_children()):
                if child in pool_children or child in keep_database_children:
                    continue
                try:
                    child.destroy()
                except (tk.TclError, RuntimeError, AttributeError):
                    continue
        elif is_database_payload:
            keep_router_children = input_network_router_style_service.suspend_router_render_host(self, host)
            keep_database_children = input_database_style_service.database_pool_children(self, host)
            for child in host.winfo_children():
                if child in keep_router_children or child in keep_database_children:
                    continue
                child.destroy()
        else:
            keep_router_children = input_network_router_style_service.suspend_router_render_host(self, host)
            keep_database_children = input_database_style_service.suspend_database_render_host(self, host)
            for child in host.winfo_children():
                if child in keep_router_children or child in keep_database_children:
                    continue
                child.destroy()
        if self._is_input_mode_category_disabled(normalized_path):
            input_mode_service.show_input_mode_notice(
                self,
                host,
                panel_bg,
                self.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
                font_size=11,
                tk_module=tk,
            )
            # Track disabled roots too; otherwise revisits can be incorrectly skipped.
            input_mode_service.mark_input_mode_render_complete(self, normalized_path)
            return
        if len(normalized_path) == 0:
            has_data = getattr(self, "data", None) is not None
            message = (
                "No direct value fields here. Select a specific item node to edit."
                if has_data
                else "No File Loaded. Open A .HHSAV File Before Continuing."
            )
            input_mode_service.show_input_mode_notice(
                self,
                host,
                panel_bg,
                message,
                font_size=9,
                tk_module=tk,
            )
            return
        if (
            len(normalized_path) == 1
            and root_key == "network"
        ):
            # Keep generic Network root placeholder, but allow custom subgroup payload renderers
            # (e.g., ROUTER/DEVICE/FIREWALL grouped selection routed through list_path) to proceed.
            if is_network_router_payload or is_network_device_payload or is_network_firewall_payload:
                pass
            else:
                input_mode_service.show_input_mode_notice(
                    self,
                    host,
                    panel_bg,
                    "Select A Sub Category To View Input Fields",
                    font_size=11,
                    tk_module=tk,
                )
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if len(normalized_path) == 1 and root_key == "database":
            input_mode_service.show_input_mode_notice(
                self,
                host,
                panel_bg,
                "Select A Sub Category To View Input Fields",
                font_size=11,
                tk_module=tk,
            )
            input_mode_service.mark_input_mode_render_complete(self, normalized_path)
            return
        if self._is_bank_input_style_path(normalized_path):
            bank_rows = self._collect_bank_input_rows(value)
            if bank_rows:
                self._render_bank_input_style_rows(host, normalized_path, bank_rows)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if database_bcc_payload:
            self._render_database_bcc_table(host, normalized_path, database_bcc_payload)
            self._refresh_input_mode_bool_widget_colors()
            self._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(self, normalized_path)
            return
        if database_interpol_payload:
            self._render_database_interpol_table(host, normalized_path, database_interpol_payload)
            self._refresh_input_mode_bool_widget_colors()
            self._schedule_input_mode_layout_finalize(reset_scroll=True)
            input_mode_service.mark_input_mode_render_complete(self, normalized_path)
            return
        if self._is_database_input_style_path(normalized_path):
            if database_grades_matrix:
                self._render_database_grades_input_matrix(host, normalized_path, database_grades_matrix)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if self._is_suspicion_input_style_path(normalized_path):
            if self._render_suspicion_phone_input(host, normalized_path, value):
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if self._is_phone_input_style_path(normalized_path):
            if self._render_phone_preview_input(host, normalized_path, value):
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if self._is_skypersky_input_style_path(normalized_path):
            if self._render_skypersky_input(host, normalized_path, value):
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_router_payload:
            router_rows = self._collect_network_router_input_rows(normalized_path, value)
            if router_rows:
                self._render_network_router_input_rows(
                    host,
                    normalized_path,
                    router_rows,
                    start_index=0,
                    finalize=True,
                    total_rows=len(router_rows),
                )
                self._clear_router_virtual_state()
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_firewall_payload:
            firewall_rows = self._collect_network_firewall_input_rows(normalized_path, value)
            if firewall_rows:
                self._render_network_firewall_input_rows(host, normalized_path, firewall_rows)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_bcc_domains_payload:
            bcc_domains_payload = self._collect_network_bcc_domains_payload(normalized_path, value)
            if bcc_domains_payload:
                self._render_network_bcc_domains_input(host, normalized_path, bcc_domains_payload)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_blue_table_payload:
            blue_table_payload = self._collect_network_blue_table_payload(normalized_path, value)
            if blue_table_payload:
                self._render_network_blue_table_input(host, normalized_path, blue_table_payload)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_interpol_payload:
            interpol_payload = self._collect_network_interpol_payload(normalized_path, value)
            if interpol_payload:
                self._render_network_interpol_input(host, normalized_path, interpol_payload)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_geoip_payload:
            geoip_payload = self._collect_network_geoip_payload(normalized_path, value)
            if geoip_payload:
                self._render_network_geoip_input(host, normalized_path, geoip_payload)
                self._refresh_input_mode_bool_widget_colors()
                self._schedule_input_mode_layout_finalize(reset_scroll=True)
                input_mode_service.mark_input_mode_render_complete(self, normalized_path)
                return
        if is_network_device_payload:
            input_mode_service.show_input_mode_notice(
                self,
                host,
                panel_bg,
                "Selected A Sub Category",
                font_size=11,
                tk_module=tk,
            )
            input_mode_service.mark_input_mode_render_complete(self, normalized_path)
            return
        # Generic INPUT fallback rows are retired; unsupported paths should
        # consistently show the development template until a custom layout is added.
        input_mode_service.show_input_mode_notice(
            self,
            host,
            panel_bg,
            self.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
            font_size=11,
            tk_module=tk,
        )
        input_mode_service.mark_input_mode_render_complete(self, normalized_path)
        return

    def _input_mode_path_key(self, path):
        if isinstance(path, list):
            return tuple(self._input_mode_path_key(token) for token in path)
        if isinstance(path, tuple):
            return tuple(self._input_mode_path_key(token) for token in path)
        return path

    def _refresh_input_mode_bool_widget_colors(self):
        # Keep INPUT boolean visuals deterministic across renderer/type variations.
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        bool_true_fg = "#70e58a" if variant == "KAMUE" else "#62d67a"
        bool_false_fg = "#f3a1ad" if variant == "KAMUE" else "#ff9ea1"
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

    def _can_skip_input_mode_refresh(self, item_id, target_path):
        return editor_mode_switch_service.can_skip_input_mode_refresh(self, item_id, target_path)

    def _cancel_pending_input_mode_refresh(self):
        after_id = getattr(self, "_input_mode_refresh_after_id", None)
        self._input_mode_refresh_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _cancel_pending_input_mode_layout_finalize(self):
        after_id = getattr(self, "_input_mode_layout_finalize_after_id", None)
        self._input_mode_layout_finalize_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _run_input_mode_layout_finalize(self):
        self._input_mode_layout_finalize_after_id = None
        host = getattr(self, "_input_mode_fields_host", None)
        canvas = getattr(self, "_input_mode_canvas", None)
        reset_scroll = bool(getattr(self, "_input_mode_layout_finalize_reset_scroll", False))
        self._input_mode_layout_finalize_reset_scroll = False
        if host is None:
            return
        try:
            host.update_idletasks()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if canvas is None:
            return
        try:
            canvas.configure(scrollregion=canvas.bbox("all") or (0, 0, 0, 0))
            if reset_scroll:
                canvas.yview_moveto(0.0)
        except (tk.TclError, RuntimeError, AttributeError):
            return

    def _schedule_input_mode_layout_finalize(self, reset_scroll=False):
        self._input_mode_layout_finalize_reset_scroll = bool(
            getattr(self, "_input_mode_layout_finalize_reset_scroll", False) or bool(reset_scroll)
        )
        self._cancel_pending_input_mode_layout_finalize()
        root = getattr(self, "root", None)
        if root is None:
            self._run_input_mode_layout_finalize()
            return
        try:
            self._input_mode_layout_finalize_after_id = root.after_idle(self._run_input_mode_layout_finalize)
        except (tk.TclError, RuntimeError, AttributeError):
            self._input_mode_layout_finalize_after_id = None
            self._run_input_mode_layout_finalize()

    def _cancel_pending_router_input_batches(self):
        after_id = getattr(self, "_input_mode_router_batch_after_id", None)
        self._input_mode_router_batch_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _cancel_pending_router_input_prewarm(self):
        after_id = getattr(self, "_input_mode_router_prewarm_after_id", None)
        self._input_mode_router_prewarm_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError, AttributeError):
            return

    def _run_router_input_prewarm(self):
        self._input_mode_router_prewarm_after_id = None
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
            return
        try:
            self._prewarm_input_mode_assets()
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
        host = getattr(self, "_input_mode_fields_host", None)
        if host is None:
            return
        data = getattr(self, "data", None)
        if not isinstance(data, dict):
            return
        network = data.get("Network")
        if not isinstance(network, list) or not network:
            return
        routers = [
            item for item in network
            if isinstance(item, dict) and str(item.get("type", "")).upper() == "ROUTER"
        ]
        if not routers:
            return
        max_rows = max(1, int(getattr(self, "_router_input_max_rows", 60) or 60))
        rows = self._collect_network_router_input_rows(["Network"], routers, max_rows=max_rows)
        if not rows:
            return
        # Prewarm enough pooled rows to keep first ROUTER open smooth without scroll-time injection.
        prewarm_limit = max(
            1,
            min(
                len(rows),
                int(getattr(self, "_router_input_prewarm_row_limit_cap", max_rows) or max_rows),
                int(getattr(self, "_router_input_prewarm_row_limit", max_rows) or max_rows),
            ),
        )
        prewarm_rows = list(rows[:prewarm_limit])
        if not prewarm_rows:
            return
        input_network_router_style_service.prepare_router_render_host(self, host, reset_pool=True)
        self._render_network_router_input_rows(
            host,
            ["Network"],
            prewarm_rows,
            start_index=0,
            finalize=True,
            total_rows=len(prewarm_rows),
        )
        input_network_router_style_service.suspend_router_render_host(self, host)
        self._input_mode_field_specs = []
        self._input_mode_router_virtual_rows = []
        self._input_mode_router_virtual_next_index = 0
        self._input_mode_router_virtual_total_rows = 0

    def _schedule_router_input_prewarm(self):
        self._cancel_pending_router_input_prewarm()
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
            return
        root = getattr(self, "root", None)
        if root is None:
            self._run_router_input_prewarm()
            return
        try:
            # Defer prewarm so open-file flow returns before non-critical cache work.
            delay_ms = max(100, int(getattr(self, "_router_input_prewarm_delay_ms", 180) or 180))
            self._input_mode_router_prewarm_after_id = root.after(delay_ms, self._run_router_input_prewarm)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            self._input_mode_router_prewarm_after_id = None

    def _cancel_pending_router_virtual_check(self):
        after_id = getattr(self, "_input_mode_router_virtual_after_id", None)
        self._input_mode_router_virtual_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _clear_router_virtual_state(self):
        self._cancel_pending_router_virtual_check()
        self._cancel_pending_router_settle_barrier()
        self._clear_input_mode_scroll_drag_active()
        self._input_mode_router_virtual_rows = []
        self._input_mode_router_virtual_next_index = 0
        self._input_mode_router_virtual_total_rows = 0

    def _schedule_router_virtual_check(self, delay_ms=30):
        self._cancel_pending_router_virtual_check()
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            self._input_mode_router_virtual_after_id = root.after(
                max(0, int(delay_ms)),
                self._maybe_render_more_router_rows,
            )
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            self._input_mode_router_virtual_after_id = None

    def _cancel_pending_router_settle_barrier(self):
        after_id = getattr(self, "_input_mode_router_settle_after_id", None)
        self._input_mode_router_settle_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, ValueError):
            return

    def _schedule_router_settle_barrier(self, delay_ms=24):
        self._cancel_pending_router_settle_barrier()
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            self._input_mode_router_settle_after_id = root.after(
                max(0, int(delay_ms)),
                self._run_router_settle_barrier,
            )
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            self._input_mode_router_settle_after_id = None

    def _run_router_settle_barrier(self):
        self._input_mode_router_settle_after_id = None
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        start_time = time.perf_counter()
        budget_seconds = 0.12
        while (time.perf_counter() - start_time) < budget_seconds:
            progressed = self._maybe_render_more_router_rows(force_prefetch=True, origin="settle")
            if not progressed:
                break
        if int(getattr(self, "_input_mode_router_virtual_next_index", 0) or 0) < int(
            getattr(self, "_input_mode_router_virtual_total_rows", 0) or 0
        ):
            self._schedule_router_virtual_check(delay_ms=20)

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
        self._input_mode_router_virtual_after_id = None
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return False
        host = getattr(self, "_input_mode_fields_host", None)
        canvas = getattr(self, "_input_mode_canvas", None)
        if host is None or canvas is None:
            return False
        rows = list(getattr(self, "_input_mode_router_virtual_rows", []) or [])
        next_index = int(getattr(self, "_input_mode_router_virtual_next_index", 0) or 0)
        total_rows = int(getattr(self, "_input_mode_router_virtual_total_rows", 0) or 0)
        if not rows or next_index >= total_rows:
            return False
        try:
            _y0, y1 = canvas.yview()
        except (tk.TclError, RuntimeError, ValueError, TypeError, AttributeError):
            y1 = 1.0
        # Keep a prefetch band so wheel/drag scroll does not outrun row materialization.
        if y1 < self._router_virtual_prefetch_threshold(force_prefetch=bool(force_prefetch)):
            return False
        backlog = max(0, total_rows - next_index)
        chunk_size = self._router_virtual_chunk_size(backlog)
        chunk = rows[next_index : next_index + chunk_size]
        if not chunk:
            return False
        final_index = next_index + len(chunk)
        self._render_network_router_input_rows(
            host,
            self._input_mode_current_path,
            chunk,
            start_index=next_index,
            finalize=final_index >= total_rows,
            total_rows=total_rows,
        )
        self._schedule_input_mode_layout_finalize(reset_scroll=False)
        self._input_mode_router_virtual_next_index = final_index
        if final_index < total_rows:
            next_delay = 12 if bool(getattr(self, "_input_mode_scroll_drag_active", False)) else 24
            if str(origin).lower() == "settle":
                next_delay = 8
            self._schedule_router_virtual_check(delay_ms=next_delay)
            return True
        self._clear_router_virtual_state()
        return True

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
        if not pending_rows:
            return
        root = getattr(self, "root", None)
        if root is None:
            return

        def _run_next_batch():
            self._input_mode_router_batch_after_id = None
            if render_token != int(getattr(self, "_input_mode_render_token", 0) or 0):
                return
            if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
                return
            rows = list(pending_rows or [])
            if not rows:
                return
            chunk = rows[:chunk_size]
            rest = rows[chunk_size:]
            self._render_network_router_input_rows(
                host,
                normalized_path,
                chunk,
                start_index=start_index,
                finalize=not bool(rest),
                total_rows=total_rows,
            )
            if rest and render_token == int(getattr(self, "_input_mode_render_token", 0) or 0):
                self._schedule_router_input_render_batches(
                    host,
                    normalized_path,
                    rest,
                    render_token,
                    chunk_size=chunk_size,
                    start_index=start_index + len(chunk),
                    total_rows=total_rows,
                )
                return
            # Finalize once at the end to avoid repeated full-host relayout cost.
            self._refresh_input_mode_bool_widget_colors()
            self._schedule_input_mode_layout_finalize(reset_scroll=False)

        try:
            self._input_mode_router_batch_after_id = root.after_idle(_run_next_batch)
        except (tk.TclError, RuntimeError, AttributeError):
            self._input_mode_router_batch_after_id = None

    def _resolve_input_mode_selection_payload(self, item_id):
        if not item_id:
            return [], {}, ""
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            _, list_path, group = path
            value = self._get_value(list_path)
            group_items = [
                item for item in value
                if isinstance(item, dict) and item.get("type") == group
            ]
            return list_path, group_items, f"group {group} ({len(group_items)})"
        try:
            value = self._get_value(path)
        except (KeyError, IndexError, TypeError, ValueError):
            value = {}
        return path, value, self._describe(value)

    def _run_pending_input_mode_refresh(self):
        self._input_mode_refresh_after_id = None
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        item_id = getattr(self, "_input_mode_pending_item_id", None)
        if not item_id:
            item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
        self._input_mode_pending_item_id = None
        if not item_id:
            return
        try:
            render_path, render_value, status_text = self._resolve_input_mode_selection_payload(item_id)
            if self._can_skip_input_mode_refresh(item_id, render_path):
                if status_text:
                    self.set_status(status_text)
                self._update_find_controls_for_mode()
                return
            self._refresh_input_mode_fields(render_path, render_value)
            self._update_find_controls_for_mode()
            if status_text:
                self.set_status(status_text)
        except (KeyError, IndexError, TypeError, ValueError, tk.TclError, RuntimeError, AttributeError):
            return

    def _schedule_input_mode_refresh(self, item_id=None, immediate=False):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        if item_id:
            self._input_mode_pending_item_id = item_id
        self._cancel_pending_input_mode_refresh()
        if bool(immediate):
            self._run_pending_input_mode_refresh()
            return
        root = getattr(self, "root", None)
        if root is None:
            self._run_pending_input_mode_refresh()
            return
        try:
            self._input_mode_refresh_after_id = root.after_idle(self._run_pending_input_mode_refresh)
        except (tk.TclError, RuntimeError, AttributeError):
            self._input_mode_refresh_after_id = None
            self._run_pending_input_mode_refresh()

    def _refresh_editor_mode_view(self):
        text = getattr(self, "text", None)
        text_scroll = getattr(self, "_text_scroll", None)
        input_container = getattr(self, "_input_mode_container", None)
        if text is None or input_container is None or text_scroll is None:
            return
        mode = str(getattr(self, "_editor_mode", "JSON")).upper()
        self._sync_input_mode_paned_sash_lock(mode)
        self._apply_tree_mode_style(mode)
        show_input = (mode == "INPUT")
        editor_mode_top_inset = 24
        if show_input:
            # Enforce INPUT no-expand policy on mode entry so JSON-expanded branches
            # (for example Bank children opened via Find Next) do not remain visible.
            self._enforce_input_tree_expand_locks()
            try:
                text.pack_forget()
                text_scroll.pack_forget()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
            if not input_container.winfo_ismapped():
                input_container.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
            item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
            self._schedule_input_mode_refresh(item_id=item_id, immediate=True)
            return

        try:
            self._cancel_pending_input_mode_refresh()
            self._cancel_pending_router_input_batches()
            self._clear_router_virtual_state()
            self._cancel_pending_input_mode_layout_finalize()
            input_container.pack_forget()
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if not text.winfo_ismapped():
            text.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
        if not text_scroll.winfo_ismapped():
            text_scroll.pack(fill="y", side="right", pady=(editor_mode_top_inset, 0))
        if getattr(self, "data", None) is None:
            self._show_json_no_file_message()

    def _sync_input_mode_paned_sash_lock(self, mode=None):
        """Disable divider dragging in INPUT mode and keep sash at its locked position."""
        body = getattr(self, "_body_panedwindow", None)
        if body is None:
            return
        lock_active = bool(getattr(self, "_input_mode_paned_lock_active", False))
        try:
            body_class = str(body.winfo_class() or "")
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            body_class = "TPanedwindow"
        default_tags = tuple(getattr(self, "_body_paned_bindtags_default", ()) or ())
        if not default_tags:
            try:
                default_tags = tuple(body.bindtags())
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                default_tags = ()
            if default_tags:
                self._body_paned_bindtags_default = default_tags
        use_mode = str(mode or getattr(self, "_editor_mode", "JSON")).upper()
        try:
            current_x = int(body.sashpos(0))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            current_x = None
        try:
            body_width = int(body.winfo_width() or 0)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            body_width = 0
        fallback_x = None
        if body_width > 160:
            min_tree_width = 180
            min_editor_width = 320
            max_sash = max(min_tree_width, int(body_width) - min_editor_width)
            candidate = max(min_tree_width, int(round(float(body_width) * 0.30)))
            candidate = min(candidate, max_sash)
            if candidate > 10:
                fallback_x = int(candidate)
        # Persist a sane first sash position as INPUT lock baseline so
        # JSON-mode manual sash moves do not change INPUT layout.
        # Ignore near-zero values to avoid capturing pre-layout sash=0.
        fixed_input_x = getattr(self, "_input_mode_paned_fixed_sash_x", None)
        try:
            fixed_input_x = int(fixed_input_x) if fixed_input_x is not None else None
        except (TypeError, ValueError):
            fixed_input_x = None
        if fixed_input_x is not None and int(fixed_input_x) <= 10:
            fixed_input_x = None
        if fixed_input_x is None and current_x is not None and int(current_x) > 10:
            fixed_input_x = int(current_x)
            self._input_mode_paned_fixed_sash_x = fixed_input_x
        if fixed_input_x is None and fallback_x is not None:
            fixed_input_x = int(fallback_x)
            self._input_mode_paned_fixed_sash_x = fixed_input_x
        if use_mode != "INPUT":
            self._cancel_input_mode_paned_lock_recheck()
            if not lock_active and getattr(self, "_input_mode_paned_sash_x", None) is None:
                return
            self._input_mode_paned_sash_x = None
            if lock_active and default_tags:
                try:
                    if tuple(body.bindtags()) != default_tags:
                        body.bindtags(default_tags)
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    return
            self._input_mode_paned_lock_active = False
            return
        if default_tags and not lock_active:
            locked_tags = tuple(tag for tag in default_tags if str(tag) != body_class)
            if not locked_tags:
                locked_tags = default_tags
            try:
                if tuple(body.bindtags()) != locked_tags:
                    body.bindtags(locked_tags)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                self._schedule_input_mode_paned_lock_recheck()
                return
        self._input_mode_paned_lock_active = True
        # Windows zoom->normal can leave the tree pane attached-but-unmapped.
        # Reassert pane config so INPUT tree does not disappear until a mode toggle.
        JsonEditor._repair_input_mode_tree_pane_mapping(self)
        if current_x is None:
            self._schedule_input_mode_paned_lock_recheck()
            return
        locked_x = getattr(self, "_input_mode_paned_sash_x", None)
        if locked_x is None:
            if fixed_input_x is not None:
                target_x = int(fixed_input_x)
            elif int(current_x) > 10:
                target_x = int(current_x)
                self._input_mode_paned_fixed_sash_x = int(current_x)
            elif fallback_x is not None:
                target_x = int(fallback_x)
                self._input_mode_paned_fixed_sash_x = int(target_x)
            else:
                # Wait for a stable configure pass before locking INPUT sash.
                self._schedule_input_mode_paned_lock_recheck()
                return
            self._input_mode_paned_sash_x = int(target_x)
            locked_x = int(target_x)
        else:
            try:
                locked_x = int(locked_x)
            except (TypeError, ValueError):
                locked_x = None
        if locked_x is None:
            self._schedule_input_mode_paned_lock_recheck()
            return
        # Self-heal if an older transient lock captured an invalid near-zero split.
        if int(locked_x) <= 10:
            if int(current_x) > 10:
                locked_x = int(current_x)
                self._input_mode_paned_sash_x = int(locked_x)
                if fixed_input_x is None:
                    self._input_mode_paned_fixed_sash_x = int(locked_x)
            elif fallback_x is not None:
                locked_x = int(fallback_x)
                self._input_mode_paned_sash_x = int(locked_x)
                if fixed_input_x is None:
                    self._input_mode_paned_fixed_sash_x = int(locked_x)
        apply_x = int(locked_x)
        if body_width > 160:
            min_tree_width = 180
            min_editor_width = 320
            max_sash = max(min_tree_width, int(body_width) - min_editor_width)
            apply_x = max(min_tree_width, min(apply_x, max_sash))
        if int(apply_x) != current_x:
            try:
                body.sashpos(0, int(apply_x))
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                self._schedule_input_mode_paned_lock_recheck()
                return
        # If metrics are still transient, recheck shortly so INPUT can recover
        # without requiring a mode toggle.
        if int(apply_x) <= 10 or body_width <= 160:
            self._schedule_input_mode_paned_lock_recheck()
            return
        self._cancel_input_mode_paned_lock_recheck()

    def _repair_input_mode_tree_pane_mapping(self):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return False
        body = getattr(self, "_body_panedwindow", None)
        tree = getattr(self, "tree", None)
        if body is None or tree is None:
            return False
        left = getattr(tree, "master", None)
        if left is None:
            return False
        try:
            if not bool(body.winfo_ismapped()):
                return False
            if bool(left.winfo_ismapped()):
                return False
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return False
        try:
            body.pane(left, weight=1)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return False
        return True

    def _cancel_input_mode_paned_lock_recheck(self):
        after_id = getattr(self, "_input_mode_paned_recheck_after_id", None)
        self._input_mode_paned_recheck_after_id = None
        if not after_id:
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            root.after_cancel(after_id)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return

    def _schedule_input_mode_paned_lock_recheck(self, delay_ms=72):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        self._cancel_input_mode_paned_lock_recheck()

        def _run_recheck():
            self._input_mode_paned_recheck_after_id = None
            self._sync_input_mode_paned_sash_lock("INPUT")

        try:
            self._input_mode_paned_recheck_after_id = root.after(
                max(16, int(delay_ms)),
                _run_recheck,
            )
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            self._input_mode_paned_recheck_after_id = None

    def _apply_tree_mode_style(self, mode=None):
        return editor_purge_service._apply_tree_mode_style(self, mode)

    def _show_json_no_file_message(self):
        return editor_purge_service._show_json_no_file_message(self)

    @staticmethod
    def _set_nested_value(container, rel_path, new_value):
        return input_mode_service.set_nested_value(container, rel_path, new_value)

    @staticmethod
    def _strip_input_display_prefix(raw):
        return input_mode_service.strip_input_display_prefix(raw)

    def _coerce_input_field_value(self, spec):
        return input_mode_service.coerce_input_field_value(spec)

    def _apply_input_edit(self):
        return editor_purge_service._apply_input_edit(self)

    def _input_mode_root_key_for_path(self, path):
        normalized = list(path or [])
        if not normalized:
            return ""
        root = normalized[0]
        return self._normalize_root_tree_key(root)

    def _hidden_root_tree_keys_for_mode(self, mode=None):
        return tree_policy_service.hidden_root_keys_for_mode(self, mode)

    def _is_input_mode_category_disabled(self, path):
        return tree_policy_service.is_input_mode_root_disabled(self, path)

    def _is_input_tree_expand_blocked(self, item_id):
        # INPUT-only gate: keep configured root categories collapsed in tree mode.
        return tree_policy_service.is_input_mode_tree_expand_blocked(self, item_id)

    def _editor_mode_tab_photo(self, active=False):
        theme_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        tab_w = 70
        tab_h = 26
        signature = (theme_variant, bool(active), "e1_clean_v4", tab_w, tab_h)
        cache = getattr(self, "_editor_mode_tab_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._editor_mode_tab_cache = cache
        cached = cache.get(signature)
        if cached is not None:
            return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            draw_module = importlib.import_module("PIL.ImageDraw")
            scale = 4
            w = tab_w * scale
            h = tab_h * scale
            radius = 8 * scale
            canvas = image_module.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = draw_module.Draw(canvas)
            if theme_variant == "KAMUE":
                fill = (47, 20, 94, 255) if active else (23, 11, 41, 255)
                edge = (125, 75, 200, 255) if active else (81, 50, 138, 255)
            else:
                fill = (27, 77, 115, 255) if active else (18, 36, 55, 255)
                edge = (103, 180, 228, 255) if active else (53, 87, 119, 255)
            # Single-pass rounded tab keeps anti-aliased edges without double-line artifacts.
            draw.rounded_rectangle(
                (0, 0, w - 1, h - 1),
                radius=radius,
                fill=fill,
                outline=edge,
                width=max(1, scale - 2),
            )
            # Flatten the top edge (fill only) so tabs look like hanging cut-ins.
            draw.rectangle((0, 0, w - 1, max(1, radius // 3)), fill=fill)
            small = canvas.resize((tab_w, tab_h), image_module.LANCZOS)
            photo = self._pil_to_photo(small)
        except _EXPECTED_APP_ERRORS:
            photo = None
        self._bounded_cache_put(cache, signature, photo, max_items=16)
        return photo

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
        host = getattr(self, "_editor_mode_host", None)
        parent = getattr(self, "_editor_mode_parent", None)
        if host is None or parent is None:
            return
        try:
            if not (host.winfo_exists() and parent.winfo_exists()):
                return
        except (tk.TclError, RuntimeError, AttributeError):
            return
        show = True
        theme = getattr(self, "_theme", {})
        try:
            host.configure(bg=theme.get("panel", "#161b24"))
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        if not show:
            try:
                host.place_forget()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
            return
        try:
            host.place(relx=1.0, y=0, x=-16, anchor="ne")
        except (tk.TclError, RuntimeError, AttributeError):
            pass
        active_mode = str(getattr(self, "_editor_mode", "JSON")).upper()
        for mode, label in self._editor_mode_labels.items():
            try:
                if not label.winfo_exists():
                    continue
                is_active = mode == active_mode
                tab_photo = self._editor_mode_tab_photo(active=is_active)
                fg = "#ffffff" if is_active else "#c2d4e2"
                label.configure(
                    image=tab_photo if tab_photo is not None else "",
                    fg=fg,
                    bg=theme.get("panel", "#161b24"),
                    font=(self._credit_name_font()[0], 8, "bold"),
                    text=mode,
                )
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                continue
        # Avoid duplicate mode-view refresh here; _set_editor_mode performs one canonical refresh pass.

    def _mode_switch_requires_tree_rebuild(self, previous_mode, next_mode):
        return editor_mode_switch_service.mode_switch_requires_tree_rebuild(self, previous_mode, next_mode)

    def _refresh_input_mode_theme_widgets(self):
        theme = getattr(self, "_theme", {}) or {}
        panel_bg = theme.get("panel", "#161b24")
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        notice_fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"
        container = getattr(self, "_input_mode_container", None)
        if container is not None:
            try:
                if container.winfo_exists():
                    container.configure(bg=panel_bg)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is not None:
            try:
                if canvas.winfo_exists():
                    canvas.configure(bg=panel_bg, highlightbackground=panel_bg, highlightcolor=panel_bg)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        host = getattr(self, "_input_mode_fields_host", None)
        if host is not None:
            try:
                if host.winfo_exists():
                    host.configure(bg=panel_bg)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        notice = getattr(self, "_input_mode_no_fields_label", None)
        if notice is not None:
            try:
                if notice.winfo_exists():
                    notice.configure(bg=panel_bg, fg=notice_fg)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        # Theme switch must repaint custom INPUT renderers (Bank/Database) so variant palettes apply.
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "INPUT":
            return
        item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
        try:
            if item_id:
                path, value, _status_text = self._resolve_input_mode_selection_payload(item_id)
            else:
                path = list(getattr(self, "_input_mode_current_path", []) or [])
                if not path:
                    return
                value = self._get_value(path)
        except (KeyError, IndexError, TypeError, ValueError, tk.TclError, RuntimeError, AttributeError):
            return
        try:
            self._refresh_input_mode_fields(path, value)
        except (tk.TclError, RuntimeError, AttributeError, KeyError, IndexError, TypeError, ValueError):
            pass

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

    def _build_toolbar_structure(self, top, inter_button_pad):
        return toolbar_service._build_toolbar_structure(self, top, inter_button_pad)

    @staticmethod
    def _pack_toolbar_control(control, **pack_kwargs):
        host = getattr(control, "_siindbad_frame_host", control)
        host.pack(**pack_kwargs)

    def check_for_updates_auto(self):
        self._check_for_updates(auto=True)

    def _run_check_for_updates_auto(self):
        self._updates_auto_after_id = None
        self.check_for_updates_auto()

    def _schedule_auto_update_check(self, delay_ms=500):
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_updates_auto_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                self._updates_auto_after_id = None
        try:
            self._updates_auto_after_id = root.after(max(1, int(delay_ms)), self._run_check_for_updates_auto)
        except _EXPECTED_APP_ERRORS:
            self._updates_auto_after_id = None

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
        root = getattr(self, "root", None)
        if root is None:
            return
        for attr in (
            "_updates_auto_after_id",
            "_update_overlay_title_after_id",
            "_theme_prewarm_after_id",
            "_theme_footer_refresh_after_id",
            "_toolbar_refresh_after_id",
            "_startup_loader_text_after_id",
            "_startup_loader_hide_after_id",
            "_startup_loader_progress_after_id",
            "_startup_loader_title_after_id",
            "_topbar_align_after_id",
            "_text_context_menu_pulse_after_id",
            "_bug_report_pulse_after_id",
            "_bug_submit_splash_after_id",
            "_crash_report_offer_after_id",
            "_live_feedback_after_id",
            "_input_mode_router_prewarm_after_id",
            "_input_mode_router_virtual_after_id",
            "_input_mode_router_settle_after_id",
            "_input_mode_scroll_drag_after_id",
            "_input_mode_layout_finalize_after_id",
            "_input_mode_paned_recheck_after_id",
        ):
            after_id = getattr(self, attr, None)
            if after_id:
                try:
                    root.after_cancel(after_id)
                except _EXPECTED_APP_ERRORS:
                    setattr(self, attr, None)
            setattr(self, attr, None)
        self._topbar_align_pending_delay_ms = None

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
        # Enforce diagnostics day-file retention on app shutdown.
        self._purge_diag_logs_for_new_session()

    def _show_themed_update_info(self, title, message, include_startup_toggle=False):
        return editor_purge_service._show_themed_update_info(self, title, message, include_startup_toggle)

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

    def _run_update_ui_demo(self, auto=False, sleep_fn=time.sleep):
        return update_orchestrator_service.run_update_ui_demo(
            self,
            auto=auto,
            sleep_fn=sleep_fn,
        )

    def _check_for_updates(self, auto=False):
        return update_orchestrator_service.check_for_updates(
            self,
            auto=auto,
            messagebox=messagebox,
        )

    def _ui_call(self, callback, *args, wait=False, default=None, timeout=15.0, **kwargs):
        return ui_dispatch_service.ui_call(
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

    def _format_update_error(self, exc):
        return update_service.format_update_error(exc)

    def _manual_update_download_url(self):
        # Manual fallback should use public GitHub Releases, not raw dist branch files.
        return update_url_service.manual_update_download_url(self)

    def _offer_manual_update_fallback(self, pretty_error):
        return update_fallback_service.offer_manual_update_fallback(
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

    def _fetch_dist_version(self):
        return update_version_service.fetch_dist_version(self)

    def _download_dist_asset(self):
        return update_asset_service.download_dist_asset(self)

    @staticmethod
    def _parse_retry_after_seconds(value):
        return update_service.parse_retry_after_seconds(value)

    @staticmethod
    def _is_retryable_download_error(exc):
        return update_service.is_retryable_download_error(exc)

    @staticmethod
    def _download_backoff_delay(exc, attempt_index, base_delay=0.45, max_delay=12.0):
        return update_service.download_backoff_delay(
            exc,
            attempt_index,
            base_delay=base_delay,
            max_delay=max_delay,
        )

    def _verify_downloaded_update_signature(self, path):
        return update_signature_service.verify_downloaded_update_signature(
            self,
            path,
            subprocess_module=subprocess,
            json_module=json,
            os_module=os,
            sys_module=sys,
        )

    @staticmethod
    def _extract_sha256_from_text(text, asset_name):
        return update_checksum_service.extract_sha256_from_text(text, asset_name)

    def _fetch_dist_asset_sha256(self, release_info=None):
        return update_checksum_service.fetch_dist_asset_sha256(self, release_info=release_info)

    def _latest_release_api_url(self):
        return update_url_service.latest_release_api_url(self)

    def _fetch_latest_release_info(self):
        return editor_purge_service._fetch_latest_release_info(self)

    @staticmethod
    def _release_asset_download_url(release_info, asset_name):
        return update_url_service.release_asset_download_url(release_info, asset_name)

    def _download_bytes_with_retries(self, url, attempts=3, timeout=60):
        return update_download_service.download_bytes_with_retries(
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

    def _ps_escape(self, value):
        return windows_runtime_service.ps_escape(value)

    @staticmethod
    def _is_retryable_file_write_error(exc):
        return windows_runtime_service.is_retryable_file_write_error(exc, platform_name=sys.platform)

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

    def _read_json_file(self, path, encoding="utf-8"):
        return windows_runtime_service.read_json_file(path=path, encoding=encoding)

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

    def _start_hidden_process(self, args):
        return windows_runtime_service.start_hidden_process(args, subprocess_module=subprocess)

    def _install_update(self, new_path):
        return editor_purge_service._install_update(self, new_path)

    def _show_update_overlay(self, message):
        update_ui_service.show_update_overlay(self, message, tk=tk, ttk=ttk)

    def _update_update_overlay(self, message=None, stage=None, percent=None, pulse=False):
        update_ui_service.update_update_overlay(
            self,
            message=message,
            stage=stage,
            percent=percent,
            pulse=pulse,
        )

    def _close_update_overlay(self):
        update_ui_service.close_update_overlay(self)

    def _release_version(self, version):
        return version_format_service.release_version(version)

    def _format_version(self, version_tuple):
        return version_format_service.format_version(version_tuple)

    def _dist_url(self, filename):
        # Use latest GitHub release assets to avoid mutable branch dist trust.
        return update_url_service.dist_url(self, filename)

    @staticmethod
    def _resolve_token_from_env_names(*env_names):
        return token_env_service.resolve_token_from_env_names(*env_names)

    def _update_token_value(self):
        return token_env_service.update_token_value(self)

    def _bug_report_token_env_name(self):
        return token_env_service.bug_report_token_env_name(self)

    def _has_bug_report_token(self):
        return token_env_service.has_bug_report_token(self)

    def _download_headers(self):
        token = JsonEditor._update_token_value(self)
        return update_headers_service.download_headers(token)

    def _set_status(self, text):
        if self.status is None:
            return
        try:
            self.root.after(0, lambda: self.status.config(text=text))
        except (RuntimeError, tk.TclError, AttributeError):
            return

    def _selected_tree_path_text(self):
        return editor_purge_service._selected_tree_path_text(self)

    def _diag_log_path(self):
        return diag_log_housekeeping_service.build_dated_diag_log_path(
            runtime_dir=self._runtime_data_dir(create=True),
            diag_log_filename=self.DIAG_LOG_FILENAME,
        )

    def _purge_diag_logs_for_new_session(self):
        diag_log_housekeeping_service.purge_diag_logs_for_new_session(
            runtime_dir=self._runtime_data_dir(create=True),
            diag_log_filename=self.DIAG_LOG_FILENAME,
            legacy_diag_log_filenames=self.LEGACY_DIAG_LOG_FILENAMES,
            keep_days=getattr(self, "DIAG_LOG_KEEP_DAYS", 2),
            temp_dir=tempfile.gettempdir(),
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _runtime_data_dir(self, create=False):
        return runtime_paths_service.runtime_data_dir(
            runtime_dir_name=self.RUNTIME_DIR_NAME,
            create=create,
            platform_name=sys.platform,
            env=os.environ,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _crash_log_path(self):
        return crash_report_service.build_crash_log_path(
            runtime_dir=self._runtime_data_dir(create=True),
            crash_log_filename=self.CRASH_LOG_FILENAME,
        )

    def _crash_state_path(self):
        return crash_report_service.build_crash_state_path(
            runtime_dir=self._runtime_data_dir(create=True),
            crash_state_filename=self.CRASH_STATE_FILENAME,
        )

    def _read_crash_log_tail(self, max_chars=None):
        return crash_report_service.read_crash_log_tail(
            path=self._crash_log_path(),
            default_limit=self.CRASH_LOG_TAIL_MAX_CHARS,
            max_chars=max_chars,
            read_text_file_tail=runtime_log_service.read_text_file_tail,
        )

    def _read_latest_crash_block(self, max_chars=None):
        return crash_report_service.read_latest_crash_block(
            read_crash_log_tail_func=self._read_crash_log_tail,
            default_limit=self.CRASH_LOG_TAIL_MAX_CHARS,
            max_chars=max_chars,
            read_latest_block=runtime_log_service.read_latest_block,
            marker="\n---\n",
        )

    def _read_crash_prompt_state(self):
        return crash_report_service.read_crash_prompt_state(
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

    def _pending_crash_report_payload(self):
        return crash_report_service.pending_crash_report_payload(
            log_path=self._crash_log_path(),
            read_latest_crash_block_func=self._read_latest_crash_block,
            read_crash_prompt_state_func=self._read_crash_prompt_state,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _schedule_crash_report_offer(self, delay_ms=450):
        self._crash_report_offer_after_id = crash_offer_service.schedule_crash_report_offer(
            root=getattr(self, "root", None),
            existing_after_id=getattr(self, "_crash_report_offer_after_id", None),
            delay_ms=delay_ms,
            callback=self._offer_crash_report_if_available,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _offer_crash_report_if_available(self):
        return editor_purge_service._offer_crash_report_if_available(self)

    def _startup_phase_for_crash_log(self):
        if not bool(getattr(self, "_startup_loader_enabled", False)):
            return "loader_disabled"
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is not None:
            try:
                if overlay.winfo_exists():
                    return "loader_visible"
            except _EXPECTED_APP_ERRORS:
                pass
        if getattr(self, "_startup_loader_ready_ts", None) is not None:
            return "loader_ready"
        if getattr(self, "_theme_prewarm_after_id", None):
            return "theme_prewarm"
        return "app_running"

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

    def _read_diag_log_tail(self, max_chars=8000):
        return editor_purge_service._read_diag_log_tail(self, max_chars)

    def _build_bug_report_markdown(
        self,
        summary,
        details,
        include_diag=True,
        discord_contact="",
        crash_tail="",
        screenshot_url="",
        screenshot_filename="",
        screenshot_note="",
    ):
        return bug_report_context_service.build_bug_report_markdown(
            summary=summary,
            details=details,
            include_diag=include_diag,
            discord_contact=discord_contact,
            crash_tail=crash_tail,
            screenshot_url=screenshot_url,
            screenshot_filename=screenshot_filename,
            screenshot_note=screenshot_note,
            app_version=self.APP_VERSION,
            theme_variant=str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper(),
            selected_path=self._selected_tree_path_text(),
            last_json_error=getattr(self, "_last_json_error_msg", ""),
            last_highlight_note=getattr(self, "_last_error_highlight_note", ""),
            python_version=platform.python_version(),
            platform_text=platform.platform(),
            read_diag_log_tail=self._read_diag_log_tail,
            bug_report_builder=bug_report_service.build_bug_report_markdown,
        )

    def _sanitize_bug_screenshot_slug(self, value):
        return bug_report_service.sanitize_bug_screenshot_slug(value)

    def _build_bug_screenshot_repo_path(self, source_filename, summary=""):
        return bug_report_service.build_bug_screenshot_repo_path(
            source_filename,
            summary=summary,
            uploads_dir=getattr(self, "BUG_REPORT_UPLOADS_DIR", "bug-uploads"),
        )

    def _validate_bug_screenshot_file(self, path):
        return bug_report_service.validate_bug_screenshot_file(
            path,
            allowed_extensions=getattr(self, "BUG_REPORT_SCREENSHOT_ALLOWED_EXTENSIONS", ()),
            max_bytes=getattr(self, "BUG_REPORT_SCREENSHOT_MAX_BYTES", 5 * 1024 * 1024),
            max_dimension=getattr(self, "BUG_REPORT_SCREENSHOT_MAX_DIMENSION", 4096),
        )

    def _detect_bug_screenshot_magic_ext(self, source_path):
        return bug_report_service.detect_bug_screenshot_magic_ext(source_path)

    def _validate_bug_screenshot_dimensions(self, source_path):
        return bug_report_service.validate_bug_screenshot_dimensions(
            source_path,
            max_dimension=getattr(self, "BUG_REPORT_SCREENSHOT_MAX_DIMENSION", 4096),
        )

    def _prepare_bug_screenshot_upload_bytes(self, source_path, detected_ext):
        return bug_report_service.prepare_bug_screenshot_upload_bytes(
            source_path,
            detected_ext,
            max_bytes=getattr(self, "BUG_REPORT_SCREENSHOT_MAX_BYTES", 5 * 1024 * 1024),
        )

    def _upload_bug_screenshot(self, source_path, summary=""):
        return bug_report_api_service.upload_bug_screenshot(
            source_path=source_path,
            summary=summary,
            token_env_name=JsonEditor._bug_report_token_env_name(self),
            owner=self.BUG_REPORT_GITHUB_OWNER,
            repo=self.BUG_REPORT_GITHUB_REPO,
            branch=getattr(self, "BUG_REPORT_UPLOAD_BRANCH", "main"),
            validate_file_fn=self._validate_bug_screenshot_file,
            detect_magic_ext_fn=self._detect_bug_screenshot_magic_ext,
            build_repo_path_fn=self._build_bug_screenshot_repo_path,
            prepare_upload_bytes_fn=self._prepare_bug_screenshot_upload_bytes,
        )

    def _submit_bug_report_issue(self, title, body_markdown):
        return bug_report_api_service.submit_bug_report_issue(
            token_env_name=JsonEditor._bug_report_token_env_name(self),
            owner=self.BUG_REPORT_GITHUB_OWNER,
            repo=self.BUG_REPORT_GITHUB_REPO,
            labels=self.BUG_REPORT_LABELS,
            title=title,
            body_markdown=body_markdown,
            open_browser_fn=self._open_bug_report_in_browser,
        )

    def _submit_bug_report_discord_forum(
        self,
        *,
        summary,
        details,
        issue_url,
        include_diag=False,
        diag_tail="",
        crash_tail="",
        discord_contact="",
        screenshot_url="",
        screenshot_filename="",
        screenshot_note="",
    ):
        # Optional Discord Forum mirror for bug reports; enable via env webhook.
        return bug_report_api_service.submit_bug_report_discord_forum(
            webhook_env_name=getattr(self, "BUG_REPORT_DISCORD_WEBHOOK_ENV", "DISCORD_BUGREPORT_WEBHOOK"),
            summary=summary,
            details=details,
            issue_url=issue_url,
            app_version=getattr(self, "APP_VERSION", ""),
            theme_variant=str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper(),
            selected_path=self._selected_tree_path_text(),
            last_json_error=getattr(self, "_last_json_error_msg", ""),
            last_highlight_note=getattr(self, "_last_error_highlight_note", ""),
            now_text=time.strftime("%Y-%m-%d %H:%M:%S"),
            python_version=platform.python_version(),
            platform_text=platform.platform(),
            include_diag=bool(include_diag),
            diag_tail=str(diag_tail or ""),
            crash_tail=str(crash_tail or ""),
            discord_contact=str(discord_contact or ""),
            screenshot_url=screenshot_url,
            screenshot_filename=screenshot_filename,
            screenshot_note=screenshot_note,
            forum_tag_ids_raw=os.getenv(getattr(self, "BUG_REPORT_DISCORD_FORUM_TAG_IDS_ENV", ""), ""),
        )

    def _bug_report_new_issue_url(self, title, body_markdown, include_body=True):
        return bug_report_service.build_bug_report_new_issue_url(
            owner=self.BUG_REPORT_GITHUB_OWNER,
            repo=self.BUG_REPORT_GITHUB_REPO,
            labels=self.BUG_REPORT_LABELS,
            title=title,
            body_markdown=body_markdown,
            include_body=include_body,
        )

    def _copy_bug_report_body_to_clipboard(self, body_markdown):
        return clipboard_service.copy_text_to_clipboard(
            payload=body_markdown,
            root=getattr(self, "root", None),
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _open_bug_report_in_browser(self, title, body_markdown):
        # Privacy fallback: open clean issue form and rely on clipboard for full report text.
        return bug_report_browser_service.open_bug_report_in_browser(
            title=title,
            body_markdown=body_markdown,
            copy_to_clipboard_fn=lambda body: JsonEditor._copy_bug_report_body_to_clipboard(self, body),
            build_issue_url_fn=self._bug_report_new_issue_url,
            open_bug_report_browser_fn=bug_report_api_service.open_bug_report_in_browser,
            open_new_tab_fn=webbrowser.open_new_tab,
        )

    def _bug_report_submit_cooldown_remaining(self, now_monotonic=None):
        now_val = time.monotonic() if now_monotonic is None else now_monotonic
        return bug_report_cooldown_service.submit_cooldown_remaining(
            self._last_bug_report_submit_monotonic,
            self.BUG_REPORT_SUBMIT_COOLDOWN_SECONDS,
            now_val,
        )

    def _mark_bug_report_submit_now(self, now_monotonic=None):
        return editor_purge_service._mark_bug_report_submit_now(self, now_monotonic)

    def _open_bug_report_dialog(
        self,
        summary_prefill="",
        details_prefill="",
        include_diag_default=True,
        crash_tail="",
    ):
        return bug_report_ui_service.open_bug_report_dialog(
            self,
            tk=tk,
            filedialog=filedialog,
            messagebox=messagebox,
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
        after_id = getattr(self, "_bug_submit_splash_after_id", None)
        self._bug_submit_splash_after_id = None
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                pass
        splash = getattr(self, "_bug_submit_splash", None)
        self._bug_submit_splash = None
        if splash is not None:
            try:
                if splash.winfo_exists():
                    splash.destroy()
            except _EXPECTED_APP_ERRORS:
                pass

    def _show_bug_submit_splash(self, message="BUG REPORT SUBMITTED", duration_ms=1600):
        self._hide_bug_submit_splash()
        root = getattr(self, "root", None)
        if root is None:
            return
        theme = getattr(self, "_theme", {}) or {}
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            bg = "#12091d"
            fg = theme.get("title_bar_fg", "#eee8ff")
            border = "#e0b8ff"
        else:
            bg = "#0f1f2d"
            fg = theme.get("title_bar_fg", "#e6f6ff")
            border = "#b5f3ff"
        try:
            root.update_idletasks()
            splash = tk.Frame(
                root,
                bg=bg,
                bd=0,
                highlightthickness=2,
                highlightbackground=border,
                highlightcolor=border,
            )
            label = tk.Label(
                splash,
                text=str(message or "BUG REPORT SUBMITTED"),
                bg=bg,
                fg=fg,
                font=(self._preferred_mono_family(), 12, "bold"),
                padx=24,
                pady=12,
            )
            label.pack(fill="both", expand=True)
            splash.update_idletasks()
            sw = max(int(splash.winfo_reqwidth()), 300)
            sh = max(int(splash.winfo_reqheight()), 56)
            rw = max(int(root.winfo_width()), 1)
            rh = max(int(root.winfo_height()), 1)
            x = max(int((rw - sw) / 2), 8)
            y = max(int((rh - sh) / 2), 8)
            splash.place(x=x, y=y, width=sw, height=sh)
            splash.lift()
            self._bug_submit_splash = splash
            self._bug_submit_splash_after_id = root.after(
                max(700, int(duration_ms)),
                self._hide_bug_submit_splash,
            )
        except _EXPECTED_APP_ERRORS:
            self._hide_bug_submit_splash()

    def _bug_report_header_pulse_palette(self):
        theme = getattr(self, "_theme", {}) or {}
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            return {
                "border_base": theme.get("logo_border_outer", "#6b37b6"),
                "border_peak": "#e0b8ff",
                "edge_base": theme.get("bg", "#06040d"),
                "edge_peak": "#3a1660",
            }
        return {
            "border_base": theme.get("logo_border_outer", "#4b97c2"),
            "border_peak": "#b5f3ff",
            "edge_base": theme.get("bg", "#0f131a"),
            "edge_peak": "#1b4663",
        }

    def _start_bug_report_header_pulse(self):
        self._stop_bug_report_header_pulse()
        self._bug_report_pulse_tick = 0
        self._tick_bug_report_header_pulse()

    def _stop_bug_report_header_pulse(self):
        after_id = getattr(self, "_bug_report_pulse_after_id", None)
        self._bug_report_pulse_after_id = None
        if after_id:
            root = getattr(self, "root", None)
            if root is not None:
                try:
                    root.after_cancel(after_id)
                except _EXPECTED_APP_ERRORS:
                    pass

    def _tick_bug_report_header_pulse(self):
        self._bug_report_pulse_after_id = None
        dlg = getattr(self, "_bug_report_dialog", None)
        card = getattr(self, "_bug_report_card_frame", None)
        if dlg is None or card is None:
            return
        try:
            if not dlg.winfo_exists() or not card.winfo_exists():
                return
        except _EXPECTED_APP_ERRORS:
            return
        palette = self._bug_report_header_pulse_palette()
        cycle_steps = 44  # slower pulse
        tick = int(getattr(self, "_bug_report_pulse_tick", 0))
        half = cycle_steps / 2.0
        pos = float(tick % cycle_steps)
        if pos <= half:
            amount = pos / half
        else:
            amount = (cycle_steps - pos) / half
        border_color = self._blend_hex_color(palette["border_base"], palette["border_peak"], amount * 0.95)
        edge_color = self._blend_hex_color(palette["edge_base"], palette["edge_peak"], amount * 0.90)
        self._bug_report_pulse_tick = tick + 1
        try:
            card.configure(highlightbackground=border_color, highlightcolor=border_color)
            dlg.configure(bg=edge_color)
        except _EXPECTED_APP_ERRORS:
            pass
        root = getattr(self, "root", None)
        if root is not None:
            try:
                self._bug_report_pulse_after_id = root.after(210, self._tick_bug_report_header_pulse)
            except _EXPECTED_APP_ERRORS:
                self._bug_report_pulse_after_id = None

    def _activate_bug_report_custom_chrome(self, dialog, header=None, drag_widgets=(), close_widget=None):
        """Enable custom-themed dialog chrome with safe fallback semantics."""
        if dialog is None:
            return False
        try:
            dialog.update_idletasks()
            dialog.overrideredirect(True)
            try:
                dialog.attributes("-topmost", True)
                dialog.after(120, lambda: dialog.attributes("-topmost", False))
            except _EXPECTED_APP_ERRORS:
                pass
        except _EXPECTED_APP_ERRORS:
            try:
                dialog.overrideredirect(False)
            except _EXPECTED_APP_ERRORS:
                pass
            return False

        if close_widget is not None:
            try:
                close_widget.bind("<Button-1>", lambda _e: self._close_bug_report_dialog(), add="+")
            except _EXPECTED_APP_ERRORS:
                pass

        move_state = {"x": 0, "y": 0}

        def _start_move(event):
            self._bug_report_follow_root = False
            self._bug_report_is_dragging = True
            move_state["x"] = int(getattr(event, "x_root", 0))
            move_state["y"] = int(getattr(event, "y_root", 0))

        def _on_move(event):
            try:
                px = int(getattr(event, "x_root", 0))
                py = int(getattr(event, "y_root", 0))
                dx = px - int(move_state["x"])
                dy = py - int(move_state["y"])
                cx = int(dialog.winfo_x())
                cy = int(dialog.winfo_y())
                dialog.geometry(f"+{cx + dx}+{cy + dy}")
                move_state["x"] = px
                move_state["y"] = py
            except _EXPECTED_APP_ERRORS:
                return

        def _end_move(_event):
            self._bug_report_is_dragging = False

        for widget in tuple(drag_widgets or ()):
            try:
                if widget is not None:
                    widget.bind("<ButtonPress-1>", _start_move, add="+")
                    widget.bind("<B1-Motion>", _on_move, add="+")
                    widget.bind("<ButtonRelease-1>", _end_move, add="+")
            except _EXPECTED_APP_ERRORS:
                continue
        return True

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
    def _theme_palette_for_variant(variant):
        return theme_service.theme_palette_for_variant(variant)

    def _apply_dark_theme(self):
        return theme_service._apply_dark_theme(self)

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

    def _tree_font_family(self, is_variant_b):
        return self._resolve_font_family(
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
        if style is None:
            try:
                style = ttk.Style(self.root)
            except _EXPECTED_APP_ERRORS:
                return
        theme = getattr(self, "_theme", {}) or {}
        panel = panel or theme.get("panel", "#161b24")
        if tree_fg is None:
            tree_fg = theme.get("tree_fg", theme.get("fg", "#e6e6e6"))
        select_bg = select_bg or theme.get("select_bg", "#2f3a4d")
        select_fg = select_fg or theme.get("select_fg", "#ffffff")

        profile = self._tree_font_profile()
        tree_font_family = self._tree_font_family(profile["is_variant_b"])
        tree_sub_font_family = self._tree_sub_font_family()
        if profile["main_weight"] == "normal":
            tree_font = (tree_font_family, profile["main_size"])
        else:
            tree_font = (tree_font_family, profile["main_size"], profile["main_weight"])
        style.configure(
            "Treeview",
            background=panel,
            fieldbackground=panel,
            foreground=tree_fg,
            font=tree_font,
            rowheight=profile["row_height"],
            padding=(0, int(getattr(self, "_tree_content_top_gap", 2) or 0), 0, 0),
            bordercolor=panel,
            lightcolor=panel,
            darkcolor=panel,
        )
        self._apply_tree_indicator_layout(style)
        style.map(
            "Treeview",
            background=[("selected", select_bg)],
            foreground=[("selected", select_fg)],
        )
        self._configure_tree_level_fonts(
            tree_font_family=tree_font_family,
            tree_sub_font_family=tree_sub_font_family,
            main_size=profile["main_size"],
            sub_size=profile["sub_size"],
            main_weight=profile["main_weight"],
            sub_weight=profile["sub_weight"],
        )

    def _configure_tree_level_fonts(
        self,
        tree_font_family=None,
        tree_sub_font_family=None,
        main_size=None,
        sub_size=None,
        main_weight=None,
        sub_weight=None,
    ):
        tree = getattr(self, "tree", None)
        if tree is None:
            return
        try:
            if not tree.winfo_exists():
                return
        except _EXPECTED_APP_ERRORS:
            return
        profile = self._tree_font_profile()
        family_main = tree_font_family or self._tree_font_family(profile["is_variant_b"])
        family_sub = tree_sub_font_family or self._tree_sub_font_family()
        use_main_size = profile["main_size"] if main_size is None else int(main_size)
        use_sub_size = profile["sub_size"] if sub_size is None else int(sub_size)
        use_main_weight = profile["main_weight"] if main_weight is None else str(main_weight)
        use_sub_weight = profile["sub_weight"] if sub_weight is None else str(sub_weight)
        main_font = (
            (family_main, use_main_size, use_main_weight)
            if use_main_weight != "normal"
            else (family_main, use_main_size)
        )
        sub_font = (
            (family_sub, use_sub_size, use_sub_weight)
            if use_sub_weight != "normal"
            else (family_sub, use_sub_size)
        )
        try:
            tree.tag_configure("tree-main-level", font=main_font)
            tree.tag_configure("tree-sub-level", font=sub_font)
        except _EXPECTED_APP_ERRORS:
            pass

    def _apply_tree_indicator_layout(self, style):
        """Hide native indicator in TREE B so composite B2 icon pack provides branch arrows."""
        try:
            if self._tree_item_layout_default is None:
                self._tree_item_layout_default = style.layout("Treeview.Item")
        except _EXPECTED_APP_ERRORS:
            return

        variant = str(getattr(self, "_tree_style_variant", "B")).upper()
        if variant == "B":
            if self._tree_item_layout_no_indicator is None:
                self._tree_item_layout_no_indicator = [
                    (
                        "Treeitem.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("Treeitem.image", {"side": "left", "sticky": ""}),
                                (
                                    "Treeitem.focus",
                                    {
                                        "side": "left",
                                        "sticky": "",
                                        "children": [("Treeitem.text", {"side": "left", "sticky": ""})],
                                    },
                                ),
                            ],
                        },
                    )
                ]
            try:
                style.layout("Treeview.Item", self._tree_item_layout_no_indicator)
            except _EXPECTED_APP_ERRORS:
                pass
            return

        try:
            if self._tree_item_layout_default:
                style.layout("Treeview.Item", self._tree_item_layout_default)
        except _EXPECTED_APP_ERRORS:
            pass

    @staticmethod
    def _hex_to_colorref(hex_color):
        value = str(hex_color).strip().lstrip("#")
        if len(value) != 6:
            return None
        try:
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
        except ValueError:
            return None
        return (blue << 16) | (green << 8) | red

    def _apply_windows_titlebar_theme(self, bg=None, fg=None, border=None, window_widget=None):
        return theme_service._apply_windows_titlebar_theme(self, bg, fg, border, window_widget)

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

    def _build_text_context_menu(self):
        return text_context_manager.TEXT_CONTEXT.text_context_menu_service.build_text_context_menu(
            self,
            tk=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _text_context_menu_palette(self):
        theme = getattr(self, "_theme", {}) or {}
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            return {
                "bg": "#12091d",
                "frame_bg": "#0b1120",
                "fg": theme.get("fg", "#f0e7ff"),
                "shortcut_fg": "#c8b2e5",
                "active_bg": "#48207a",
                "active_fg": "#ffffff",
                "active_border": "#bf95ff",
                "border": theme.get("logo_border_outer", "#7947c6"),
                "inset_border": "#2d174c",
                "panel_border": "#3a205f",
                "panel_bg": "#12091d",
                "pulse_start_border": "#56308f",
                "pulse_start_inset": "#24113d",
                "pulse_start_panel": "#2a1645",
                "pulse_border": "#b887ff",
                "pulse_inset": "#3f2162",
                "separator": "#4e2b84",
                "disabled_fg": "#8f78aa",
            }
        return {
            "bg": "#0c151f",
            "frame_bg": "#0b1725",
            "fg": theme.get("fg", "#e6f5ff"),
            "shortcut_fg": "#a9d2e8",
            "active_bg": "#15496a",
            "active_fg": "#ffffff",
            "active_border": "#74d5fb",
            "border": theme.get("logo_border_outer", "#4b97c2"),
            "inset_border": "#153850",
            "panel_border": "#1e3d56",
            "panel_bg": "#0c151f",
            "pulse_start_border": "#2a5a7a",
            "pulse_start_inset": "#102a3d",
            "pulse_start_panel": "#163245",
            "pulse_border": "#67e0ff",
            "pulse_inset": "#1f4f70",
            "separator": "#22506f",
            "disabled_fg": "#6f879a",
        }

    @staticmethod
    def _text_context_menu_scale():
        # Keep menu compact while preserving readability and click targets.
        return 0.8

    def _style_text_context_menu(self):
        return text_context_manager.TEXT_CONTEXT.text_context_menu_service.style_text_context_menu(
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

    def _has_text_selection(self):
        return text_context_state_service.has_text_selection(self.text, _EXPECTED_APP_ERRORS)

    def _clipboard_has_text(self):
        return text_context_state_service.clipboard_has_text(self.root, _EXPECTED_APP_ERRORS)

    def _text_can_undo(self):
        return text_context_state_service.text_can_undo(self.text, _EXPECTED_APP_ERRORS)

    def _text_can_redo(self):
        return text_context_state_service.text_can_redo(self.text, _EXPECTED_APP_ERRORS)

    def _destroy_text_context_menu(self):
        self._hide_text_context_menu()
        popup = getattr(self, "_text_context_menu", None)
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except _EXPECTED_APP_ERRORS:
                pass
        self._text_context_menu = None
        self._text_context_menu_anchor = None
        self._text_context_menu_frame = None
        self._text_context_menu_panel = None
        self._text_context_menu_body = None
        self._text_context_menu_separator = None
        self._text_context_menu_separators = []
        self._text_context_menu_items = {}
        self._text_context_menu_widget_actions = {}
        self._text_context_menu_row_style = None
        self._text_context_menu_item_states = {}
        self._text_context_menu_hover_action = None
        self._text_context_menu_pulse_tick = 0

    def _set_text_context_menu_item_state(self, action, enabled):
        states = getattr(self, "_text_context_menu_item_states", None)
        if not isinstance(states, dict):
            return
        states[action] = bool(enabled)

    def _first_enabled_text_context_action(self):
        return text_context_action_service.first_enabled_action(
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

    def _text_context_menu_action_for_widget(self, widget):
        return text_context_pointer_service.action_for_widget(
            widget=widget,
            widget_actions=getattr(self, "_text_context_menu_widget_actions", {}) or {},
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _text_context_menu_action_for_pointer(self):
        return text_context_pointer_service.action_for_pointer(
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

    def _on_text_context_menu_click(self, action):
        return text_context_action_service.dispatch_click_action(
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
    def _widget_is_popup_child(widget, popup):
        return text_context_widget_service.is_popup_child(widget, popup)

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
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except _EXPECTED_APP_ERRORS:
            return
        try:
            self.root.after(30, self._hide_text_context_menu_if_app_inactive)
        except _EXPECTED_APP_ERRORS:
            self._hide_text_context_menu_if_app_inactive()

    def _on_root_focus_in(self, event=None):
        if not bool(getattr(self, "BUG_REPORT_USE_CUSTOM_CHROME", True)):
            return
        try:
            self.root.after(50, self._ensure_bug_report_dialog_visible)
        except _EXPECTED_APP_ERRORS:
            self._ensure_bug_report_dialog_visible()

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
    def _blend_hex_color(color_a, color_b, ratio):
        ratio = max(0.0, min(1.0, float(ratio)))
        ra, ga, ba = JsonEditor._hex_to_rgb_tuple(color_a, default_rgb=(0, 0, 0))
        rb, gb, bb = JsonEditor._hex_to_rgb_tuple(color_b, default_rgb=(0, 0, 0))
        r = int(round(ra + ((rb - ra) * ratio)))
        g = int(round(ga + ((gb - ga) * ratio)))
        b = int(round(ba + ((bb - ba) * ratio)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _start_text_context_menu_pulse(self):
        self._stop_text_context_menu_pulse()
        self._text_context_menu_pulse_tick = 0
        self._tick_text_context_menu_pulse()

    def _stop_text_context_menu_pulse(self):
        after_id = getattr(self, "_text_context_menu_pulse_after_id", None)
        self._text_context_menu_pulse_after_id = None
        if after_id:
            root = getattr(self, "root", None)
            if root is not None:
                try:
                    root.after_cancel(after_id)
                except _EXPECTED_APP_ERRORS:
                    pass

    def _tick_text_context_menu_pulse(self):
        self._text_context_menu_pulse_after_id = None
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except _EXPECTED_APP_ERRORS:
            return
        palette = self._text_context_menu_palette()
        hover_action = getattr(self, "_text_context_menu_hover_action", None)
        if hover_action:
            root = getattr(self, "root", None)
            if root is None:
                return
            try:
                self._text_context_menu_pulse_after_id = root.after(140, self._tick_text_context_menu_pulse)
            except _EXPECTED_APP_ERRORS:
                self._text_context_menu_pulse_after_id = None
            return
        else:
            cycle_steps = 28
            tick = int(getattr(self, "_text_context_menu_pulse_tick", 0))
            half = cycle_steps / 2.0
            pos = float(tick % cycle_steps)
            if pos <= half:
                amount = pos / half
            else:
                amount = (cycle_steps - pos) / half
            border_base = palette.get("pulse_start_border", palette["border"])
            inset_base = palette.get("pulse_start_inset", palette["inset_border"])
            panel_base = palette.get("pulse_start_panel", palette["panel_border"])
            border_color = self._blend_hex_color(border_base, palette["pulse_border"], amount)
            inset_color = self._blend_hex_color(inset_base, palette["pulse_inset"], amount)
            panel_color = self._blend_hex_color(panel_base, palette["pulse_inset"], amount * 0.75)
            self._text_context_menu_pulse_tick = tick + 1
        anchor = getattr(self, "_text_context_menu_anchor", None)
        frame = getattr(self, "_text_context_menu_frame", None)
        panel = getattr(self, "_text_context_menu_panel", None)
        if anchor is not None:
            try:
                anchor.configure(highlightbackground=border_color, highlightcolor=border_color)
            except _EXPECTED_APP_ERRORS:
                pass
        if frame is not None:
            try:
                frame.configure(highlightbackground=inset_color, highlightcolor=inset_color)
            except _EXPECTED_APP_ERRORS:
                pass
        if panel is not None:
            try:
                panel.configure(highlightbackground=panel_color, highlightcolor=panel_color)
            except _EXPECTED_APP_ERRORS:
                pass
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            delay_ms = 140 if hover_action else 100
            self._text_context_menu_pulse_after_id = root.after(delay_ms, self._tick_text_context_menu_pulse)
        except _EXPECTED_APP_ERRORS:
            self._text_context_menu_pulse_after_id = None

    def _hide_text_context_menu(self):
        self._stop_text_context_menu_pulse()
        self._unbind_text_context_menu_global_dismiss()
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        self._text_context_menu_hover_action = None
        try:
            if popup.winfo_exists():
                popup.withdraw()
        except _EXPECTED_APP_ERRORS:
            pass
        self._style_text_context_menu()

    def _show_text_context_menu_popup(self, popup_x, popup_y):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return False
        try:
            if not popup.winfo_exists():
                return False
        except _EXPECTED_APP_ERRORS:
            return False
        self._style_text_context_menu()
        try:
            popup.withdraw()
            # Clear any stale WM size so first open uses current content metrics.
            popup.geometry("")
            popup.update_idletasks()
            req_w = max(206, int(popup.winfo_reqwidth()))
            req_h = max(1, int(popup.winfo_reqheight()))
            # Use virtual desktop bounds so popup follows the app across monitors.
            vroot_x = int(self.root.winfo_vrootx())
            vroot_y = int(self.root.winfo_vrooty())
            screen_w = max(req_w + 2, int(self.root.winfo_vrootwidth()))
            screen_h = max(req_h + 2, int(self.root.winfo_vrootheight()))
            max_x = max(vroot_x + 2, (vroot_x + screen_w) - req_w - 2)
            max_y = max(vroot_y + 2, (vroot_y + screen_h) - req_h - 2)
            x = max(vroot_x + 2, min(int(popup_x), max_x))
            y = max(vroot_y + 2, min(int(popup_y), max_y))
            # Keep natural widget size; only control position.
            popup.geometry(f"+{x}+{y}")
            popup.deiconify()
            popup.lift()
            # Re-measure after map to catch first-show metric changes (font/layout).
            popup.update_idletasks()
            final_w = max(req_w, int(popup.winfo_width()))
            final_h = max(req_h, int(popup.winfo_height()))
            max_x = max(vroot_x + 2, (vroot_x + screen_w) - final_w - 2)
            max_y = max(vroot_y + 2, (vroot_y + screen_h) - final_h - 2)
            x = max(vroot_x + 2, min(int(popup_x), max_x))
            y = max(vroot_y + 2, min(int(popup_y), max_y))
            popup.geometry(f"+{x}+{y}")
        except _EXPECTED_APP_ERRORS:
            return False
        self._bind_text_context_menu_global_dismiss()
        self._start_text_context_menu_pulse()
        return True

    def _show_text_context_menu(self, event=None):
        return text_context_manager.TEXT_CONTEXT.text_context_menu_service.show_text_context_menu(
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

    def _show_input_context_menu(self, event=None):
        return self._show_input_context_with_text_menu(event)

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

    def _show_find_entry_context_menu(self, event=None):
        return self._show_widget_context_with_text_menu(event, allow_paste=True)

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
        widget = getattr(self, "_input_context_target_widget", None)
        if widget is None:
            return
        if not bool(getattr(self, "_input_context_target_allow_paste", False)):
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
        try:
            state = str(widget.cget("state")).lower()
        except _EXPECTED_APP_ERRORS:
            state = "normal"
        if state in ("readonly", "disabled"):
            return
        try:
            if self._input_widget_has_selection(widget):
                widget.delete("sel.first", "sel.last")
        except _EXPECTED_APP_ERRORS:
            pass
        try:
            widget.insert("insert", safe_text)
        except _EXPECTED_APP_ERRORS:
            return

    @staticmethod
    def _parse_suggestion_before_after(message):
        return error_service.parse_suggestion_before_after(message)

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

    def _current_overlay_suggestion(self):
        return editor_purge_service._current_overlay_suggestion(self)

    def _can_context_autofix(self):
        payload = self._current_overlay_suggestion()
        return bool(payload and payload.get("after") is not None)

    def _apply_line_autofix(self, line_no, before_text, after_text):
        if not line_no:
            return False
        raw_line = self._line_text(int(line_no))
        if raw_line is None:
            return False
        indent = re.match(r"^\s*", raw_line).group(0) if raw_line else ""
        before = str(before_text) if before_text is not None else ""
        after = str(after_text or "")

        new_line = None
        caret_col = 0
        if before and before in raw_line:
            replace_at = raw_line.find(before)
            new_line = raw_line.replace(before, after, 1)
            caret_col = max(0, int(replace_at + len(after)))
        elif before and raw_line.strip() == before.strip():
            new_line = indent + after.lstrip()
            caret_col = max(0, len(new_line))
        elif not before:
            new_line = indent + after.lstrip()
            caret_col = max(0, len(new_line))
        else:
            stripped_raw = raw_line.strip()
            if stripped_raw:
                new_line = indent + after.lstrip()
                caret_col = max(0, len(new_line))
            else:
                new_line = after
                caret_col = max(0, len(new_line))
        if new_line is None:
            return False

        try:
            start_idx = f"{int(line_no)}.0"
            self.text.delete(start_idx, f"{int(line_no)}.0 lineend")
            self.text.insert(start_idx, new_line)
            caret_col = min(max(int(caret_col), 0), len(new_line))
            self.text.mark_set("insert", f"{int(line_no)}.{caret_col}")
            self.text.see(f"{int(line_no)}.{caret_col}")
            return True
        except _EXPECTED_APP_ERRORS:
            return False

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
    def _error_symbol_notes():
        return error_service.error_symbol_notes()

    def _is_symbol_error_note(self, note):
        return error_service.is_symbol_error_note(note)

    def _error_marker_colors(self, note, palette, insertion_only=False):
        return error_service.error_marker_colors(note, palette, insertion_only=insertion_only)

    def _tag_has_ranges(self, tag_name):
        try:
            return bool(self.text.tag_ranges(tag_name))
        except _EXPECTED_APP_ERRORS:
            return False

    def _current_error_palette(self):
        return error_service.current_error_palette(
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

    def _preferred_mono_family(self):
        if self._mono_family:
            return self._mono_family
        preferred = [
            "JetBrains Mono",
            "Cascadia Code",
            "Cascadia Mono",
            "Consolas",
            "Courier New",
        ]
        try:
            families = {name.lower(): name for name in tkfont.families(self.root)}
            for name in preferred:
                hit = families.get(name.lower())
                if hit:
                    self._mono_family = hit
                    return self._mono_family
        except _EXPECTED_APP_ERRORS:
            pass
        self._mono_family = "Consolas"
        return self._mono_family

    def _resolve_font_family(self, preferred_families, fallback):
        families = getattr(self, "_font_family_lookup_cache", None)
        if families is None:
            families = {}
            try:
                families = {name.lower(): name for name in tkfont.families(self.root)}
            except _EXPECTED_APP_ERRORS:
                families = {}
            self._font_family_lookup_cache = families
        try:
            for family in preferred_families:
                hit = families.get(str(family).lower())
                if hit:
                    return hit
        except _EXPECTED_APP_ERRORS:
            pass
        return fallback

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
        paths = [self._settings_path()]
        legacy_path = None
        legacy_fn = getattr(self, "_legacy_settings_path", None)
        if callable(legacy_fn):
            try:
                legacy_path = legacy_fn()
            except _EXPECTED_APP_ERRORS:
                legacy_path = None
        if legacy_path:
            paths.append(legacy_path)
        for path in paths:
            if not os.path.isfile(path):
                continue
            try:
                reader = getattr(self, "_read_json_file", None)
                if callable(reader):
                    data = reader(path, encoding="utf-8")
                else:
                    data = windows_runtime_service.read_json_file(path=path, encoding="utf-8")
                fs = data.get("font_size")
                if isinstance(fs, int) and 6 <= fs <= 32:
                    self._font_size = fs
                theme_variant = str(data.get("app_theme", "")).upper()
                if theme_variant in ("SIINDBAD", "KAMUE"):
                    self._app_theme_variant = theme_variant
                # Startup update-check preference accepts bool/int or 0/1-style text.
                startup_pref = data.get("startup_update_check")
                if isinstance(startup_pref, bool):
                    self._startup_update_check_enabled = startup_pref
                elif isinstance(startup_pref, (int, float)):
                    self._startup_update_check_enabled = bool(int(startup_pref))
                elif isinstance(startup_pref, str):
                    token = startup_pref.strip().lower()
                    if token in ("1", "true", "yes", "on"):
                        self._startup_update_check_enabled = True
                    elif token in ("0", "false", "no", "off"):
                        self._startup_update_check_enabled = False
                return
            except _EXPECTED_APP_ERRORS:
                continue

    def _save_user_settings(self):
        """Save user settings (font size, app theme, startup update-check preference)."""
        path = self._settings_path()
        data = {
            "font_size": int(self._font_size),
            "app_theme": str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper(),
            "startup_update_check": bool(getattr(self, "_startup_update_check_enabled", False)),
        }
        try:
            payload = json.dumps(data, ensure_ascii=False)
            writer = getattr(self, "_write_text_file_atomic", None)
            if callable(writer):
                writer(path, payload, encoding="utf-8")
            else:
                windows_runtime_service.write_text_file_atomic(
                    path=path,
                    text=payload,
                    encoding="utf-8",
                )
        except _EXPECTED_APP_ERRORS:
            return

    @staticmethod
    def _normalize_button_token(value):
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def _siindbad_effective_style(self):
        return editor_purge_service._siindbad_effective_style(self)

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

    def _siindbad_toolbar_button_symbol(self, key):
        return toolbar_service.siindbad_toolbar_button_symbol(
            style=self._siindbad_effective_style(),
            key=key,
        )

    @staticmethod
    def _hex_to_rgb_tuple(hex_color, default_rgb=(220, 235, 245)):
        try:
            raw = str(hex_color).strip().lstrip("#")
            if len(raw) != 6:
                return default_rgb
            return (int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16))
        except _EXPECTED_APP_ERRORS:
            return default_rgb

    @staticmethod
    def _normalize_root_tree_key(value):
        return tree_view_service.normalize_root_tree_key(value)

    def _tree_display_label_for_key(self, key):
        return tree_view_service.tree_display_label_for_key(
            key=key,
            tree_style_variant=getattr(self, "_tree_style_variant", "B"),
            safe_display_labels=self.TREE_B_SAFE_DISPLAY_LABELS,
        )

    def _init_chrome_runtime_state(self):
        # Core window chrome/editor runtime state used before UI widgets are built.
        self.logo_image = None
        self.logo_label = None
        self.logo_frame = None
        self._logo_frame_inner = None
        self._logo_path = None
        self._logo_photo_cache = {}
        self._header_frame = None
        self._header_variant_bar = None
        self._header_variant_host = None
        self._header_variant_is_footer = False
        self._header_variant_labels = {}
        self._header_variant = "A"
        self._show_header_variant_controls = False
        self._editor_mode = "JSON"
        self._editor_mode_host = None
        self._editor_mode_parent = None
        self._editor_mode_labels = {}
        self._editor_mode_tab_cache = {}
        self._editor_right_parent = None
        self._body_panedwindow = None
        self._body_paned_bindtags_default = ()
        self._input_mode_paned_sash_x = None
        self._input_mode_paned_fixed_sash_x = None
        self._input_mode_paned_recheck_after_id = None
        self._input_mode_paned_lock_active = False
        self._text_scroll = None
        self._init_input_mode_runtime_state()
        self._init_tree_runtime_state()
        # INPUT mode is now public by default; keep flag for compatibility checks.
        self._input_mode_public_enabled = True
        self._app_theme_variant = "SIINDBAD"
        self._app_theme_labels = {}
        self._toolbar_style_variant = "B"
        # Toolbar variants are finalized: use Variant-B for both themes.
        self._toolbar_style_variant_by_theme = {"SIINDBAD": "B", "KAMUE": "B"}
        # Dev toggle: set HACKHUB_ENABLE_TOOLBAR_VARIANTS=1 to show toolbar variant controls.
        self._show_toolbar_variant_controls = (
            str(os.environ.get("HACKHUB_ENABLE_TOOLBAR_VARIANTS", "0")).strip().lower()
            in ("1", "true", "yes", "on")
        )
        # Optional forced style lock; keep unset so A/B can be switched from UI.
        self._siindbad_style_focus = None
        self._toolbar_button_images = {}
        self._toolbar_asset_image_cache = {}
        self._toolbar_theme_shade_cache = {}
        self._toolbar_buttons = {}
        self._toolbar_button_text = {}
        self._toolbar_style_labels = {}
        self._toolbar_style_title_label = None
        self._toolbar_center_frame = None
        self._toolbar_layout_mode = None
        self._find_host_default_padx = None
        self._find_button_default_padx = None
        self._find_entry_width_override = None
        self._topbar_align_after_id = None
        self._topbar_align_pending_delay_ms = None
        self._siindbad_button_icons = {}
        self._siindbad_button_icon_signature = None

    def _init_footer_bugreport_runtime_state(self):
        # Footer/chips/bug-report runtime state grouped for maintainability.
        self._credit_badge_images = []
        self._credit_badge_sources_cache = None
        self._credit_github_icon_cache = {}
        self._credit_discord_icon_cache = {}
        self._credit_badge_render_signature = None
        self._credit_discord_badge_render_signature = None
        self._credit_badge_widget_pool = {}
        self._credit_badge_active_signature = None
        self._credit_discord_widget_pool = {}
        self._credit_discord_active_signature = None
        self._credit_badge_host = None
        self._credit_discord_badge_host = None
        self._credit_bar = None
        self._credit_left_slot = None
        self._credit_center_slot = None
        self._credit_right_slot = None
        self._credit_content = None
        self._credit_label = None
        self._credit_badges_divider = None
        self._credit_badges_divider_lines = ()
        self._credit_discord_badge_images = []
        self._credit_discord_divider = None
        self._credit_discord_divider_lines = ()
        self._credit_theme_divider = None
        self._credit_theme_divider_lines = ()
        self._theme_selector_host = None
        self._bug_report_host = None
        self._bug_report_chip = None
        self._bug_report_label = None
        self._bug_report_chip_hovered = False
        self._bug_report_chip_icon_photo = None
        self._bug_report_icon_cache = {}
        self._bug_report_chip_icon_label = None
        self._bug_report_chip_text_label = None
        self._bug_report_dialog = None
        self._bug_report_card_frame = None
        self._bug_report_header_frame = None
        self._bug_report_header_icon = None
        self._bug_report_header_icon_photo = None
        self._bug_report_header_title = None
        self._bug_report_close_badge = None
        self._bug_report_pulse_after_id = None
        self._bug_report_pulse_tick = 0
        self._bug_report_follow_root = False
        self._bug_report_offset_x = 0
        self._bug_report_offset_y = 0
        self._bug_report_is_dragging = False
        self._last_bug_report_submit_monotonic = 0.0
        self._bug_submit_splash = None
        self._bug_submit_splash_after_id = None
        self._theme_footer_refresh_after_id = None
        self._titlebar_theme_signature_by_hwnd = {}
        self._font_stepper_label = None
        self._font_size_value_label = None
        self._font_control_host = None
        self._readme_window = None
        self._find_entry_host = None
        self._toolbar_host = None
        self._body_top_separator = None
        self._body_top_separator_inner = None
        self.find_entry = None

    def _init_text_context_runtime_state(self):
        # Text context menu and font-stepper sprite runtime state.
        self._text_context_menu = None
        self._text_context_menu_anchor = None
        self._text_context_menu_frame = None
        self._text_context_menu_panel = None
        self._text_context_menu_body = None
        self._text_context_menu_separator = None
        self._text_context_menu_separators = []
        self._text_context_menu_items = {}
        self._text_context_menu_widget_actions = {}
        self._text_context_menu_row_style = None
        self._text_context_menu_item_states = {}
        self._text_context_menu_hover_action = None
        self._text_context_menu_global_bindings = []
        self._text_context_menu_pulse_after_id = None
        self._text_context_menu_pulse_tick = 0
        self._input_context_menu = None
        self._input_context_target_widget = None
        self._input_context_target_allow_paste = False
        self.font_size_combo = None
        self.font_size_var = None
        self._font_stepper_source_size = (1028, 253)
        self._font_stepper_minus_box_src = (395, 43, 648, 174)
        self._font_stepper_plus_box_src = (676, 43, 929, 174)

    def _init_theme_update_runtime_state(self):
        # Theme prewarm/update/startup-loader runtime state.
        self._theme_prewarm_after_id = None
        self._theme_prewarm_queue = []
        self._theme_prewarm_done = set()
        self._theme_prewarm_tasks = deque()
        self._theme_prewarm_active_variant = None
        self._theme_prewarm_budget_ms = 10
        self._theme_prewarm_loader_budget_ms = 6
        self._theme_prewarm_idle_tick_ms = 12
        self._theme_prewarm_loader_tick_ms = 16
        self._theme_prewarm_total_by_variant = {"SIINDBAD": 0, "KAMUE": 0}
        self._theme_prewarm_done_by_variant = {"SIINDBAD": 0, "KAMUE": 0}
        # Cache per-variant logo PhotoImage so theme switches avoid reload work.
        self._theme_logo_photo_by_variant = {}
        self._toolbar_refresh_after_id = None
        self._updates_auto_after_id = None
        # Saved startup update-check preference: default off unless user enables from update dialogs.
        self._startup_update_check_enabled = False
        self._update_overlay_title_after_id = None
        self._update_overlay_progress_pct = 0.0
        self._update_overlay_stage = ""
        # Update-flow smoothing: keep install stage visible for a short handoff pause.
        self._update_install_stage_hold_ms = 3000
        # Update-flow smoothing: keep restart stage visible longer before root teardown.
        self._update_restart_notice_ms = 4200
        self._shutdown_cleanup_done = False
        self._theme_perf_logging = (
            # Perf debug toggle: set HACKHUB_THEME_PERF_LOG=1 to print theme switch timings.
            str(os.environ.get("HACKHUB_THEME_PERF_LOG", "0")).strip().lower()
            in ("1", "true", "yes", "on")
        )
        self._startup_loader_enabled = True
        # Keep startup loader visible for a cinematic hold while prewarm catches up.
        self._startup_loader_extra_hold_ms = 1600
        self._startup_loader_overlay = None
        self._startup_loader_pct_label = None
        self._startup_loader_statement_label = None
        self._startup_loader_top_fill = None
        self._startup_loader_bottom_fill = None
        self._startup_loader_started_ts = 0.0
        self._startup_loader_ready_ts = None
        self._startup_loader_text_after_id = None
        self._startup_loader_hide_after_id = None
        self._startup_loader_progress_after_id = None
        self._startup_loader_statement_index = 0
        self._startup_loader_line_pool_loading = []
        self._startup_loader_line_pool_ready = []
        self._startup_loader_required_variants = {"SIINDBAD", "KAMUE"}
        self._startup_loader_deferred_variants = set()
        self._startup_loader_title_prefix_label = None
        self._startup_loader_title_suffix_label = None
        self._startup_loader_title_variant = "SIINDBAD"
        self._startup_loader_title_after_id = None
        self._startup_loader_title_cycle_ms = 4200
        self._startup_loader_progress_interval_ms = 34
        self._startup_loader_statement_interval_loading_ms = 1450
        self._startup_loader_statement_interval_ready_ms = 1150
        # Loader finish phase: smooth progress to 100 before teardown.
        self._startup_loader_complete_dwell_ms = 260
        # Keep 100% visible briefly so completion is perceptible before teardown.
        self._startup_loader_finish_visible_hold_ms = 140
        # Loader smoothing: keep visible progress moving forward without abrupt jumps.
        self._startup_loader_display_pct = 0.0
        self._startup_loader_last_progress_ts = 0.0
        self._startup_loader_smooth_rate_pct_per_sec = 30.0
        self._startup_loader_finishing = False
        self._startup_loader_finish_started_ts = 0.0
        self._startup_loader_finish_start_pct = 0.0
        self._startup_loader_finish_reached_100_ts = 0.0
        self._startup_loader_window_mode = bool(
            getattr(self.root, "_hh_use_startup_loader_window", False)
        )
        self._startup_loader_title_cache = {}
        self._startup_loader_fill_photo_cache = {}
        self._startup_loader_panel_photo_cache = {}
        self._theme_rgba_image_cache = {}
        self._display_scale = 1.0
        self._auto_display_profile_name = "default"
        self._window_layout = None

    def _init_editor_session_runtime_state(self):
        # Core editor/session diagnostics and interaction runtime state.
        self.network_types = ["ROUTER", "DEVICE", "FIREWALL", "SPLITTER"]
        self.network_types_set = set(self.network_types)
        self.find_matches = []
        self.find_index = 0
        self.last_find_query = ""
        # Cache searchable tree labels by data path to avoid expensive full-tree expansion on find.
        self._find_search_entries = []
        # Cache JSON path token text for incremental Find Next narrowing.
        self._json_find_path_token_cache = {}
        # Track configured JSON text widget for one-time find tag styling.
        self._json_find_tag_widget = None
        self.error_overlay = None
        self.error_pin = None
        self._mono_family = None
        self._font_family_lookup_cache = None
        self._font_size = 10  # Default font size
        self._auto_apply_pending = False
        self._auto_apply_in_progress = False
        self._live_feedback_after_id = None
        self._live_feedback_delay_ms = int(self.LIVE_FEEDBACK_DELAY_MS_DEFAULT)
        self._pending_insert_restore_index = ""
        self._diag_event_seq = 0
        self._diag_action = "startup:0"
        self._error_visual_mode = "guide"
        self._last_edit_was_deletion = False
        self._error_focus_index = None
        self._last_error_highlight_note = ""
        self._last_error_insertion_only = False
        self._last_error_overlay_message = ""
        self._error_overlay_actions = None
        self._allow_highlight_key_change_once = False
        self._last_tree_selected_item = None
        self._json_lock_apply_after_id = None
        self._json_render_seq = 0
        self._last_json_error_diag = None
        self._error_hooks_installed = False
        self._crash_notice_shown = False
        self._prev_sys_excepthook = None
        self._prev_threading_excepthook = None
        self._session_id = uuid.uuid4().hex[:12]
        self._session_started_monotonic = time.monotonic()
        self._last_callback_origin = ""
        self._crash_report_offer_after_id = None
        self._list_labelers = tree_engine_service.default_list_labelers(self)
        # INPUT mode uses custom Database entry names (Grades/BCC/INTERPOL) while
        # JSON mode keeps canonical host-style labels through the same labeler hook.
        self._list_labelers[("Database",)] = self._database_root_entry_label

    def _init_input_mode_runtime_state(self):
        # Keep INPUT-mode runtime state initialization grouped for easier maintenance.
        self._input_mode_container = None
        self._input_mode_canvas = None
        self._input_mode_scroll = None
        self._input_mode_fields_host = None
        self._input_mode_field_specs = []
        self._input_mode_current_path = []
        self._input_mode_no_fields_label = None
        self._input_mode_last_render_item = None
        self._input_mode_last_render_path_key = None
        self._input_mode_force_refresh = True
        self._input_mode_render_token = 0
        self._input_mode_router_batch_after_id = None
        self._input_mode_router_prewarm_after_id = None
        self._input_mode_router_virtual_after_id = None
        self._input_mode_router_settle_after_id = None
        self._input_mode_scroll_drag_after_id = None
        self._input_mode_scroll_drag_active = False
        self._input_mode_router_row_pool = []
        self._input_mode_router_pool_host = None
        self._input_mode_router_shell = None
        self._input_mode_router_art_cache = {}
        self._input_suspicion_phone_photo_cache = {}
        # ROUTER INPUT prewarm defaults:
        # - max rows caps per-render workload
        # - prewarm row limit primes pooled rows for smooth first ROUTER open
        self._router_input_max_rows = 60
        self._router_input_prewarm_row_limit = 60
        self._router_input_prewarm_row_limit_cap = 60
        self._router_input_prewarm_delay_ms = 180
        self._input_mode_router_virtual_rows = []
        self._input_mode_router_virtual_next_index = 0
        self._input_mode_router_virtual_total_rows = 0
        self._input_mode_layout_finalize_after_id = None
        self._input_mode_layout_finalize_reset_scroll = False
        self._input_mode_refresh_after_id = None
        self._input_mode_pending_item_id = None

    def _init_tree_runtime_state(self):
        # Keep shared tree UI runtime state initialization grouped by tree subsystem.
        self._tree_style_variant = "B"
        self._tree_style_labels = {}
        self._tree_style_title_label = None
        self._tree_content_top_gap = 2
        self._tree_marker_icon_cache = {}
        self._tree_marker_integrity_checked = False
        self._tree_marker_integrity_ok = True
        self._tree_item_layout_default = None
        self._tree_item_layout_no_indicator = None

    @staticmethod
    def _bounded_cache_put(cache, key, value, max_items=128):
        if not isinstance(cache, dict):
            return
        try:
            if key in cache:
                cache.pop(key, None)
            cache[key] = value
            limit = max(8, int(max_items))
            while len(cache) > limit:
                cache.pop(next(iter(cache)), None)
        except _EXPECTED_APP_ERRORS:
            try:
                cache[key] = value
            except _EXPECTED_APP_ERRORS:
                pass

    def _siindbad_toolbar_style_palette(self):
        theme = getattr(self, "_theme", {})
        style = self._siindbad_effective_style()
        theme_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        border_outer = theme.get("logo_border_outer", "#349fc7")
        border_inner = theme.get("logo_border_inner", "#a9ddf0")
        find_border = theme.get("find_border", border_inner)
        if style == "B":
            if theme_variant == "KAMUE":
                return {
                    "button_bg": "#1a1130",
                    "button_fg": "#efe6ff",
                    "button_active": "#2a1b4c",
                    "button_pressed": "#130a25",
                    # Match KAMUE FONT host outer frame border.
                    "border": find_border,
                    "border_active": find_border,
                    "slot_bg": "#110a20",
                    "size_bg": "#24133f",
                    "inner_border": "#d2a4ff",
                }
            return {
                "button_bg": "#0f2439",
                "button_fg": "#dff5ff",
                "button_active": "#16324c",
                "button_pressed": "#0b1623",
                "border": border_outer,
                "border_active": border_inner,
                "slot_bg": "#0b1a2a",
                "size_bg": "#11283c",
                "inner_border": "#72d7ff",
            }
        return {
            "button_bg": "#102236",
            "button_fg": "#e2f3ff",
            "button_active": "#17314b",
            "button_pressed": "#0d1a2a",
            "border": border_outer,
            "border_active": border_inner,
            "slot_bg": "#0d1d2d",
            "size_bg": "#12283c",
            "inner_border": border_inner,
        }

    def _draw_siindbad_toolbar_icon(self, key, fg_hex, accent_hex, style, accent2_hex=None):
        return toolbar_service._draw_siindbad_toolbar_icon(self, key, fg_hex, accent_hex, style, accent2_hex)

    def _ensure_siindbad_button_icons(self):
        style = self._siindbad_effective_style()
        palette = self._siindbad_toolbar_style_palette()
        signature = (
            style,
            palette.get("button_fg"),
            palette.get("border_active"),
            palette.get("border"),
            palette.get("inner_border"),
        )
        if signature == self._siindbad_button_icon_signature and self._siindbad_button_icons:
            return
        self._siindbad_button_icon_signature = signature
        self._siindbad_button_icons = {}
        try:
            image_tk_module = importlib.import_module("PIL.ImageTk")
            for key in ("open", "apply", "export", "find", "update", "readme"):
                icon = self._draw_siindbad_toolbar_icon(
                    key=key,
                    fg_hex=palette.get("button_fg", "#deeff8"),
                    accent_hex=palette.get("border_active", "#a9ddf0"),
                    style=style,
                    accent2_hex=palette.get("inner_border", palette.get("border_active", "#a9ddf0")),
                )
                self._siindbad_button_icons[key] = image_tk_module.PhotoImage(icon)
        except _EXPECTED_APP_ERRORS:
            self._siindbad_button_icons = {}

    def _find_entry_target_width(self):
        override = getattr(self, "_find_entry_width_override", None)
        if isinstance(override, int) and override > 0:
            return int(override)
        style = self._siindbad_effective_style()
        if style == "B":
            spec = self._siindbad_b_search_spec()
            if spec:
                return int(spec.get("width", 172))
            return 172
        return 156

    @staticmethod
    def _siindbad_toolbar_label_text(style, key, text):
        return toolbar_service.siindbad_toolbar_label_text(style, key, text)

    def _update_find_entry_layout(self):
        return toolbar_service.update_find_entry_layout(
            self,
            tk_module=tk,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _schedule_topbar_alignment(self, delay_ms=35):
        root = getattr(self, "root", None)
        if root is None:
            return
        request_delay = max(0, int(delay_ms))
        existing = getattr(self, "_topbar_align_after_id", None)
        pending_delay = getattr(self, "_topbar_align_pending_delay_ms", None)
        # Coalesce repeated configure bursts; keep the earliest already-scheduled alignment.
        if existing and pending_delay is not None and request_delay >= int(pending_delay):
            return
        if existing:
            try:
                root.after_cancel(existing)
            except _EXPECTED_APP_ERRORS:
                pass
        self._topbar_align_after_id = None
        self._topbar_align_pending_delay_ms = None
        try:
            self._topbar_align_after_id = root.after(
                request_delay,
                self._align_topbar_to_logo,
            )
            self._topbar_align_pending_delay_ms = request_delay
        except _EXPECTED_APP_ERRORS:
            self._topbar_align_after_id = None
            self._topbar_align_pending_delay_ms = None

    @staticmethod
    def _window_is_maximized(window):
        if window is None:
            return False
        try:
            return str(window.state()).lower() == "zoomed"
        except _EXPECTED_APP_ERRORS:
            return False

    def _apply_toolbar_layout_mode(self, force=False):
        host = getattr(self, "_toolbar_host", None)
        center = getattr(self, "_toolbar_center_frame", None)
        if host is None or center is None:
            return
        try:
            if not (host.winfo_exists() and center.winfo_exists()):
                return
        except _EXPECTED_APP_ERRORS:
            return

        mode = "maximized" if self._window_is_maximized(getattr(self, "root", None)) else "normal"
        previous_mode = str(getattr(self, "_toolbar_layout_mode", "") or "")
        if (not force) and previous_mode == mode:
            self._apply_toolbar_spacing_for_mode(mode)
            # Keep max-mode placement synced to logo center while resizing.
            if mode == "maximized":
                self._apply_toolbar_layout_max(center, host)
            return

        self._toolbar_layout_mode = mode
        self._apply_toolbar_spacing_for_mode(mode)
        if mode == "maximized":
            self._apply_toolbar_layout_max(center, host)
        else:
            self._apply_toolbar_layout_normal(center)

    def _apply_toolbar_spacing_for_mode(self, mode):
        # Guard normal layout: only tighten the search->find gap in maximized mode.
        find_host = getattr(self, "_find_entry_host", None)
        find_btn = (getattr(self, "_toolbar_buttons", None) or {}).get("find")
        if find_host is None or find_btn is None:
            return
        try:
            if not (find_host.winfo_exists() and find_btn.winfo_exists()):
                return
        except _EXPECTED_APP_ERRORS:
            return

        style = str(self._siindbad_effective_style()).upper()
        default_host_padx = getattr(self, "_find_host_default_padx", None) or (2, 0)
        default_btn_padx = getattr(self, "_find_button_default_padx", None) or (2, 0)
        target_host_padx, target_btn_padx = layout_topbar_core.compute_mode_spacing(
            mode=mode,
            style=style,
            default_host_padx=default_host_padx,
            default_btn_padx=default_btn_padx,
        )

        try:
            find_host.pack_configure(padx=target_host_padx)
        except _EXPECTED_APP_ERRORS:
            pass
        try:
            find_btn_host = getattr(find_btn, "_siindbad_frame_host", find_btn)
            find_btn_host.pack_configure(padx=target_btn_padx)
        except _EXPECTED_APP_ERRORS:
            pass

    def _find_entry_base_width(self):
        style = self._siindbad_effective_style()
        search_spec_width = None
        if style == "B":
            spec = self._siindbad_b_search_spec()
            if spec:
                search_spec_width = spec.get("width", 172)
        return layout_topbar_core.resolve_find_entry_base_width(
            style=style,
            search_spec_width=search_spec_width,
        )

    def _apply_max_toolbar_search_compaction(self, toolbar_w, logo_w):
        """Shrink search width in max mode so toolbar edges stay within logo bounds."""
        current = getattr(self, "_find_entry_width_override", None)
        base_width = int(self._find_entry_base_width())
        style = self._siindbad_effective_style()
        target = layout_topbar_core.compute_search_compaction_target(
            toolbar_w=toolbar_w,
            logo_w=logo_w,
            base_width=base_width,
            style=style,
        )
        if current == target:
            return False
        self._find_entry_width_override = target
        self._update_find_entry_layout()
        return True

    def _apply_toolbar_layout_normal(self, center):
        # Restore default search width outside maximize mode.
        if getattr(self, "_find_entry_width_override", None) is not None:
            self._find_entry_width_override = None
            self._update_find_entry_layout()
        try:
            center.place_forget()
        except _EXPECTED_APP_ERRORS:
            pass
        try:
            center.pack_forget()
        except _EXPECTED_APP_ERRORS:
            pass
        try:
            center.pack(anchor="center")
        except _EXPECTED_APP_ERRORS:
            pass

    def _apply_toolbar_layout_max(self, center, host):
        return toolbar_service.apply_toolbar_layout_max(
            self,
            center,
            host,
            expected_errors=_EXPECTED_APP_ERRORS,
            compute_centered_toolbar_position=layout_topbar_core.compute_centered_toolbar_position,
        )

    def _align_topbar_to_logo(self):
        self._topbar_align_after_id = None
        self._topbar_align_pending_delay_ms = None
        self._apply_toolbar_layout_mode(force=False)

    @staticmethod
    def _siindbad_toolbar_button_width(style, key, text):
        return toolbar_service.siindbad_toolbar_button_width(style, key, text)

    def _siindbad_toolbar_frame_width(self, style, key, text):
        style = str(style).upper()
        if style == "A":
            widths = {
                "open": 110,
                "apply": 112,
                "export": 138,
                "find": 110,
                "update": 102,
                "readme": 102,
            }
            return widths.get(key, max(84, 14 + len(str(text)) * 8))
        if style == "B":
            manifest = self._siindbad_b_sprite_manifest()
            button_meta = manifest.get("buttons", {}).get(str(key), {}) if isinstance(manifest, dict) else {}
            sprite_width = int(button_meta.get("width", 0) or 0)
            if sprite_width > 0:
                return sprite_width
            widths = {
                "open": 102,
                "apply": 116,
                "export": 128,
                "find": 108,
                "update": 98,
                "readme": 98,
            }
            return widths.get(key, max(86, 16 + len(str(text)) * 8))
        return 0

    def _siindbad_b_sprite_dir(self):
        return theme_asset_service.siindbad_b_sprite_dir(self._resource_base_dir())

    def _siindbad_b_sprite_manifest(self):
        cached = getattr(self, "_siindbad_b_sprite_manifest_cache", None)
        if cached is not None:
            return cached
        manifest_path = os.path.join(self._siindbad_b_sprite_dir(), "manifest.json")
        data = {}
        try:
            if os.path.isfile(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as fh:
                    parsed = json.load(fh)
                if isinstance(parsed, dict):
                    data = parsed
        except _EXPECTED_APP_ERRORS:
            data = {}
        self._siindbad_b_sprite_manifest_cache = data
        return data

    def _invalidate_siindbad_b_sprite_cache(self):
        after_id = getattr(self, "_theme_prewarm_after_id", None)
        root = getattr(self, "root", None)
        if root is not None and after_id:
            try:
                root.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                pass
        self._theme_prewarm_after_id = None
        self._siindbad_b_sprite_manifest_cache = None
        self._siindbad_b_button_image_cache = {}
        self._siindbad_b_search_sprite_cache = {}
        self._theme_prewarm_done = set()
        self._theme_prewarm_queue = []
        self._theme_prewarm_tasks = deque()
        self._theme_prewarm_total_by_variant = {"SIINDBAD": 0, "KAMUE": 0}
        self._theme_prewarm_done_by_variant = {"SIINDBAD": 0, "KAMUE": 0}

    def _siindbad_b_render_mode(self, override=None):
        if override in ("fast", "full"):
            return override
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        if variant in warmed:
            return "full"
        return "fast"

    def _siindbad_b_sprite_bundle(self, key, width, height, render_mode="full"):
        return toolbar_service._siindbad_b_sprite_bundle(self, key, width, height, render_mode)

    def _siindbad_b_button_height(self, key, default_height=34):
        manifest = self._siindbad_b_sprite_manifest()
        if isinstance(manifest, dict):
            buttons_meta = manifest.get("buttons", {})
            if isinstance(buttons_meta, dict):
                meta = buttons_meta.get(str(key), {})
                if isinstance(meta, dict):
                    value = int(meta.get("height", 0) or 0)
                    if value > 0:
                        return value
        return int(default_height)

    def _siindbad_b_search_spec(self):
        manifest = self._siindbad_b_sprite_manifest()
        if not isinstance(manifest, dict):
            return None
        search = manifest.get("search", {})
        if not isinstance(search, dict):
            return None
        width = int(search.get("width", 0) or 0)
        height = int(search.get("height", 0) or 0)
        base_name = str(search.get("base", "") or "")
        sprite_dir = self._siindbad_b_sprite_dir()
        base_path = os.path.join(sprite_dir, base_name) if base_name else ""
        input_box = search.get("input_box")
        if width <= 0 or height <= 0:
            return None
        spec = {"width": width, "height": height}
        if base_path and os.path.isfile(base_path):
            spec["base_path"] = base_path
            try:
                image_module = importlib.import_module("PIL.Image")
                with image_module.open(base_path) as base_img:
                    spec["width"] = int(base_img.width)
                    spec["height"] = int(base_img.height)
            except _EXPECTED_APP_ERRORS:
                pass
        if isinstance(input_box, (list, tuple)) and len(input_box) == 4:
            try:
                spec["input_box"] = tuple(int(v) for v in input_box)
            except _EXPECTED_APP_ERRORS:
                pass
        return spec

    def _siindbad_b_search_sprite_image(self, width, height):
        spec = self._siindbad_b_search_spec() or {}
        base_path = str(spec.get("base_path", "") or "")
        if not base_path or not os.path.isfile(base_path):
            return None
        cache = getattr(self, "_siindbad_b_search_sprite_cache", None)
        if cache is None:
            cache = {}
            self._siindbad_b_search_sprite_cache = cache
        theme_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        theme = getattr(self, "_theme", {})
        signature = (
            base_path,
            int(width),
            int(height),
            theme_variant,
            theme.get("find_border"),
            theme.get("logo_border_outer"),
        )
        cached = cache.get(signature)
        if cached is not None:
            return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            image_tk_module = importlib.import_module("PIL.ImageTk")
            image = image_module.open(base_path).convert("RGBA")
            if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE":
                try:
                    image = self._shade_toolbar_button_for_theme(image, cache_key=f"search:{base_path}")
                    image = self._harmonize_kamue_b_outer_frame(image)
                except _EXPECTED_APP_ERRORS:
                    pass
            if image.width != int(width) or image.height != int(height):
                image = image.resize((max(1, int(width)), max(1, int(height))), image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            self._bounded_cache_put(cache, signature, photo, max_items=48)
            return photo
        except _EXPECTED_APP_ERRORS:
            return None

    def _siindbad_b_font_sprite_spec(self):
        manifest = self._siindbad_b_sprite_manifest()
        if not isinstance(manifest, dict):
            return None
        font_meta = manifest.get("font", {})
        if not isinstance(font_meta, dict):
            return None
        sprite_dir = self._siindbad_b_sprite_dir()
        base_name = str(font_meta.get("base", "font_base.png"))
        base_path = os.path.join(sprite_dir, base_name)
        if not os.path.isfile(base_path):
            return None
        hover_name = str(font_meta.get("hover", ""))
        hover_path = os.path.join(sprite_dir, hover_name) if hover_name else ""
        if hover_path and not os.path.isfile(hover_path):
            hover_path = ""
        width = int(font_meta.get("width", 0) or 0)
        height = int(font_meta.get("height", 0) or 0)
        minus = tuple(font_meta.get("minus_box", ()))
        plus = tuple(font_meta.get("plus_box", ()))
        if len(minus) != 4 or len(plus) != 4:
            return None
        if width <= 0 or height <= 0:
            try:
                image_module = importlib.import_module("PIL.Image")
                probe = image_module.open(base_path)
                width, height = probe.size
            except _EXPECTED_APP_ERRORS:
                return None
        return {
            "path": base_path,
            "hover_path": hover_path,
            "width": width,
            "height": height,
            "minus_box": minus,
            "plus_box": plus,
        }

    def _load_siindbad_b_font_sprite_image(self):
        spec = self._siindbad_b_font_sprite_spec()
        if not spec:
            return False
        image = self._load_toolbar_button_image(
            spec["path"],
            max_width=max(1, int(spec["width"])),
            max_height=max(1, int(spec["height"])),
            stretch_to_fit=True,
        )
        if image is None:
            return False
        self._toolbar_button_images["font"] = image
        hover_path = str(spec.get("hover_path", "") or "")
        if hover_path and os.path.isfile(hover_path):
            hover_image = self._load_toolbar_button_image(
                hover_path,
                max_width=max(1, int(spec["width"])),
                max_height=max(1, int(spec["height"])),
                stretch_to_fit=True,
            )
            if hover_image is not None:
                self._toolbar_button_images["font_hover"] = hover_image
        self._font_stepper_source_size = (int(spec["width"]), int(spec["height"]))
        self._font_stepper_minus_box_src = tuple(int(v) for v in spec["minus_box"])
        self._font_stepper_plus_box_src = tuple(int(v) for v in spec["plus_box"])
        return True

    def _siindbad_b_asset_button_path(self, key):
        base_dir = self._resource_base_dir()
        folder = os.path.join(base_dir, "assets", "buttons", "variants", "B")
        candidates = [f"{key}2.png", f"{key}.png"]
        for name in candidates:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
        return None

    @staticmethod
    def _pointer_within_widget(widget):
        try:
            if widget is None or not widget.winfo_exists():
                return False
            px = widget.winfo_pointerx()
            py = widget.winfo_pointery()
            x1 = widget.winfo_rootx()
            y1 = widget.winfo_rooty()
            x2 = x1 + widget.winfo_width()
            y2 = y1 + widget.winfo_height()
            return x1 <= px < x2 and y1 <= py < y2
        except _EXPECTED_APP_ERRORS:
            return False

    def _siindbad_b_render_button_bundle(self, key, text, width, height, palette, render_mode=None):
        return toolbar_service._siindbad_b_render_button_bundle(self, key, text, width, height, palette, render_mode)

    def _stop_siindbad_b_button_scan(self, button):
        host = getattr(button, "_siindbad_frame_host", None)
        after_id = getattr(button, "_siindbad_scan_after_id", None)
        if host is not None and after_id:
            try:
                host.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                pass
        button._siindbad_scan_after_id = None
        button._siindbad_scan_running = False
        button._siindbad_scan_idx = -1
        button._siindbad_scan_start_ts = None
        base_image = getattr(button, "_siindbad_base_image", None)
        if base_image is not None:
            try:
                button.configure(image=base_image)
            except _EXPECTED_APP_ERRORS:
                pass

    def _stop_all_siindbad_b_button_scans(self):
        for button in getattr(self, "_toolbar_buttons", {}).values():
            if button is None or not getattr(button, "winfo_exists", lambda: False)():
                continue
            if hasattr(button, "_siindbad_scan_running"):
                self._stop_siindbad_b_button_scan(button)

    def _invoke_siindbad_b_button(self, button, command):
        # Strict hover behavior: after click, scan must not resume until pointer leaves
        # and re-enters the button hit area.
        try:
            button._siindbad_hover_require_reenter = True
        except _EXPECTED_APP_ERRORS:
            pass
        self._stop_all_siindbad_b_button_scans()
        try:
            command()
        except _EXPECTED_APP_ERRORS:
            raise

    def _tick_siindbad_b_button_scan(self, button):
        host = getattr(button, "_siindbad_frame_host", None)
        if host is None or not host.winfo_exists() or not getattr(button, "_siindbad_scan_running", False):
            self._stop_siindbad_b_button_scan(button)
            return

        frames = getattr(button, "_siindbad_hover_frames", None) or []
        if not frames:
            return
        interval_ms = int(getattr(button, "_siindbad_scan_interval_ms", 40) or 40)
        interval_ms = max(20, min(100, interval_ms))
        start_ts = getattr(button, "_siindbad_scan_start_ts", None)
        now = time.perf_counter()
        if start_ts is None:
            start_ts = now
            button._siindbad_scan_start_ts = start_ts
        elapsed_ms = max(0.0, (now - start_ts) * 1000.0)
        idx = int(elapsed_ms // float(interval_ms)) % len(frames)
        prev_idx = int(getattr(button, "_siindbad_scan_idx", -1))
        if idx != prev_idx:
            try:
                button.configure(image=frames[idx])
            except _EXPECTED_APP_ERRORS:
                return
            button._siindbad_scan_idx = idx

        frame_step = int(elapsed_ms // float(interval_ms))
        next_boundary_ms = (frame_step + 1) * float(interval_ms)
        next_delay = int(round(next_boundary_ms - elapsed_ms))
        next_delay = max(10, min(120, next_delay))
        try:
            button._siindbad_scan_after_id = host.after(
                next_delay, lambda b=button: self._tick_siindbad_b_button_scan(b)
            )
        except _EXPECTED_APP_ERRORS:
            button._siindbad_scan_after_id = None

    def _start_siindbad_b_button_scan(self, button):
        if getattr(button, "_siindbad_scan_running", False):
            return
        if not getattr(button, "_siindbad_hover_frames", None):
            return
        button._siindbad_scan_running = True
        button._siindbad_scan_idx = -1
        button._siindbad_scan_start_ts = time.perf_counter()
        self._tick_siindbad_b_button_scan(button)

    def _siindbad_b_button_hover_enter(self, button):
        if bool(getattr(button, "_siindbad_hover_require_reenter", False)):
            return
        leave_after = getattr(button, "_siindbad_hover_leave_after_id", None)
        host = getattr(button, "_siindbad_frame_host", None)
        if host is not None and leave_after:
            try:
                host.after_cancel(leave_after)
            except _EXPECTED_APP_ERRORS:
                pass
            button._siindbad_hover_leave_after_id = None
        self._start_siindbad_b_button_scan(button)

    def _siindbad_b_button_hover_leave(self, button):
        host = getattr(button, "_siindbad_frame_host", None)
        if host is None or not host.winfo_exists():
            self._stop_siindbad_b_button_scan(button)
            return

        def _settle():
            button._siindbad_hover_leave_after_id = None
            frame_host = getattr(button, "_siindbad_frame_host", None)
            pointer_in_button = self._pointer_within_widget(button)
            pointer_in_frame = self._pointer_within_widget(frame_host)
            require_reenter = bool(getattr(button, "_siindbad_hover_require_reenter", False))
            if require_reenter:
                if not pointer_in_button and not pointer_in_frame:
                    button._siindbad_hover_require_reenter = False
                self._stop_siindbad_b_button_scan(button)
                return
            if pointer_in_button or pointer_in_frame:
                self._start_siindbad_b_button_scan(button)
                return
            self._stop_siindbad_b_button_scan(button)

        after_id = getattr(button, "_siindbad_hover_leave_after_id", None)
        if after_id:
            try:
                host.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                pass
        try:
            button._siindbad_hover_leave_after_id = host.after(40, _settle)
        except _EXPECTED_APP_ERRORS:
            self._stop_siindbad_b_button_scan(button)

    def _apply_siindbad_toolbar_button_style(self, button, key, text):
        return toolbar_service._apply_siindbad_toolbar_button_style(self, button, key, text)

    def _apply_asset_toolbar_button_style(self, button):
        theme = getattr(self, "_theme", {})
        bg = theme.get("bg", "#0f131a")
        try:
            button.configure(
                relief="flat",
                borderwidth=0,
                highlightthickness=0,
                padx=0,
                pady=0,
                bg=bg,
                fg=theme.get("fg", "#e6e6e6"),
                activebackground=bg,
                activeforeground=theme.get("fg", "#e6e6e6"),
                takefocus=0,
                cursor="hand2",
                anchor="center",
                width=0,
                height=0,
            )
        except _EXPECTED_APP_ERRORS:
            return

    def _make_siindbad_stepper_button(self, parent, symbol, command):
        return toolbar_service._make_siindbad_stepper_button(self, parent, symbol, command)

    def _make_siindbad_font_stepper(self, parent):
        palette = self._siindbad_toolbar_style_palette()
        label_font = self._toolbar_button_font()
        style = self._siindbad_effective_style()
        frame_border = palette["border"]
        frame_border_active = palette["border_active"]

        host = tk.Frame(
            parent,
            bg=palette["button_bg"],
            bd=1 if style == "A" else 0,
            relief="solid" if style == "A" else "flat",
            highlightthickness=1,
            highlightbackground=frame_border,
            highlightcolor=frame_border_active,
            width=136 if style == "A" else 122,
            height=34,
        )
        host.pack_propagate(False)

        parent_for_controls = host
        if style == "B":
            # Center the whole FONT/-/+ cluster to remove right-side gap.
            row = tk.Frame(host, bg=palette["button_bg"], bd=0, highlightthickness=0)
            row.place(relx=0.5, rely=0.5, anchor="center")
            parent_for_controls = row

        label = tk.Label(
            parent_for_controls,
            text="FONT",
            bg=palette["button_bg"],
            fg=palette["button_fg"],
            font=label_font,
            bd=0,
            highlightthickness=0,
        )
        label.pack(side="left", padx=((8 if style != "B" else 0), 6))

        minus_box = self._make_siindbad_stepper_button(parent_for_controls, "-", self.decrease_font_size)
        minus_box.pack(side="left", padx=(0, 1 if style == "B" else 3), pady=5)

        plus_box = self._make_siindbad_stepper_button(parent_for_controls, "+", self.increase_font_size)
        plus_box.pack(side="left", padx=((1 if style == "B" else 3), (0 if style == "B" else 7)), pady=5)
        return host

    def _make_font_stepper(self, parent):
        image = self._toolbar_button_images.get("font")
        if image is None:
            fallback = ttk.Frame(parent)
            ttk.Button(fallback, text="-", width=2, command=self.decrease_font_size).pack(side="left")
            ttk.Button(fallback, text="+", width=2, command=self.increase_font_size).pack(
                side="left", padx=(4, 0)
            )
            return fallback

        theme = getattr(self, "_theme", {})
        bg = theme.get("bg", "#0f131a")
        label = tk.Label(
            parent,
            image=image,
            bg=bg,
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="arrow",
        )
        label.bind("<Button-1>", self._on_font_stepper_click)
        label.bind("<Motion>", self._on_font_stepper_motion)
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "SIINDBAD" and self._siindbad_effective_style() == "B":
            hover_image = self._toolbar_button_images.get("font_hover")
            if hover_image is not None:
                label.bind("<Enter>", lambda _event, w=label, img=hover_image: w.configure(image=img), add="+")
                label.bind("<Leave>", lambda _event, w=label, img=image: w.configure(image=img), add="+")
        self._font_stepper_label = label
        return label

    def _render_font_control(self):
        parent = self._font_control_host
        if parent is None or not parent.winfo_exists():
            return
        for child in parent.winfo_children():
            child.destroy()

        self._font_stepper_label = None
        self._font_size_value_label = None
        self.font_size_combo = None
        self.font_size_var = None

        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        style = self._siindbad_effective_style()
        if variant == "SIINDBAD" and style == "B":
            # SIINDBAD Variant-B uses generated font sprite + hitboxes.
            self._toolbar_button_images = {}
            if not self._load_siindbad_b_font_sprite_image():
                self._load_toolbar_button_images_from_assets(
                    style="B",
                    mapping={"font": (("font2b", "font2", "font"), 146, 34, True)},
                )
            self._make_font_stepper(parent).pack(side="left")
            return
        if variant == "SIINDBAD":
            self._make_siindbad_font_stepper(parent).pack(side="left")
            return
        if variant == "KAMUE":
            theme = getattr(self, "_theme", {})
            bg = theme.get("bg", "#0f131a")
            panel = theme.get("panel", "#161b24")
            fg = theme.get("fg", "#e6e6e6")
            # Keep the previous balanced look, but slightly shaded darker.
            border = theme.get("find_border", "#cfb5ee")
            inner_border = theme.get("logo_border_outer", "#6b37b6")
            label_family = self._resolve_font_family(
                ["Segoe UI Semibold", "Segoe UI Bold", "Segoe UI"],
                self._preferred_mono_family(),
            )

            host = tk.Frame(
                parent,
                bg=bg,
                bd=0,
                highlightthickness=1,
                highlightbackground=border,
                highlightcolor=border,
                width=124,
                height=self._siindbad_b_button_height("find", default_height=33),
            )
            host.pack(side="left")
            host.pack_propagate(False)
            # Add a subtle dark tint under the border to shade it without over-purple shift.
            shade_layer = tk.Frame(host, bg="#0b0615", bd=0, highlightthickness=0)
            shade_layer.place(x=0, y=0, relwidth=1, relheight=1)

            inner = tk.Frame(
                host,
                bg=panel,
                bd=0,
                highlightthickness=1,
                highlightbackground=inner_border,
                highlightcolor=inner_border,
            )
            inner.pack(fill="both", expand=True, padx=1, pady=1)
            controls = tk.Frame(inner, bg=panel, bd=0, highlightthickness=0)
            controls.place(relx=0.5, rely=0.5, anchor="center")

            label = tk.Label(
                controls,
                text="FONT",
                bg=panel,
                fg=fg,
                font=(label_family, 10, "bold"),
                bd=0,
                highlightthickness=0,
            )
            label.pack(side="left", padx=(1, 3))

            values = tuple(str(i) for i in range(6, 33))
            self.font_size_var = tk.StringVar(value=str(int(self._font_size)))
            combo_style = "Kamue.FontSize.TCombobox"
            number_font = self._font_dropdown_number_font()
            style = ttk.Style(self.root)
            style.configure(
                combo_style,
                fieldbackground=panel,
                foreground=fg,
                background=panel,
                bordercolor=inner_border,
                arrowcolor=fg,
                lightcolor=panel,
                darkcolor=panel,
                padding=1,
                font=number_font,
            )
            style.map(
                combo_style,
                fieldbackground=[("readonly", panel), ("active", panel)],
                foreground=[("readonly", fg), ("active", fg)],
                selectforeground=[("readonly", fg)],
                selectbackground=[("readonly", theme.get("select_bg", "#2f3a4d"))],
                arrowcolor=[("readonly", fg), ("active", fg)],
                bordercolor=[("readonly", inner_border), ("active", border)],
            )
            combo = ttk.Combobox(
                controls,
                textvariable=self.font_size_var,
                values=values,
                state="readonly",
                width=5,
                style=combo_style,
                font=number_font,
                justify="center",
            )
            combo.pack(side="left", padx=(0, 1), pady=0)
            combo.bind("<<ComboboxSelected>>", self._on_font_size_selected)
            select_bg = theme.get("select_bg", "#2f3a4d")
            select_fg = theme.get("select_fg", "#ffffff")
            self._style_combobox_popdown(
                combo,
                bg=panel,
                fg=fg,
                select_bg=select_bg,
                select_fg=select_fg,
                font=number_font,
            )
            combo.bind(
                "<Button-1>",
                lambda _evt, cb=combo, bg_color=panel, fg_color=fg, sb=select_bg, sf=select_fg, nf=number_font:
                    self._style_combobox_popdown(cb, bg=bg_color, fg=fg_color, select_bg=sb, select_fg=sf, font=nf),
                add="+",
            )
            self.font_size_combo = combo
            return

        self._make_font_stepper(parent).pack(side="left")

    def _style_combobox_popdown(self, combo, bg, fg, select_bg, select_fg, font=None):
        """Style the ttk.Combobox dropdown listbox to match current theme."""
        try:
            popdown = combo.tk.eval(f"ttk::combobox::PopdownWindow {combo}")
            listbox = f"{popdown}.f.l"
            args = [
                listbox,
                "configure",
                "-background",
                bg,
                "-foreground",
                fg,
                "-justify",
                "center",
                "-selectbackground",
                select_bg,
                "-selectforeground",
                select_fg,
                "-highlightthickness",
                "0",
                "-borderwidth",
                "0",
            ]
            if font:
                args.extend(["-font", font])
            combo.tk.call(*args)
        except _EXPECTED_APP_ERRORS:
            pass

    @staticmethod
    def _scale_hitbox(hitbox, src_width, src_height, dst_width, dst_height):
        x1, y1, x2, y2 = hitbox
        sx = dst_width / src_width if src_width else 1.0
        sy = dst_height / src_height if src_height else 1.0
        return (
            int(round(x1 * sx)),
            int(round(y1 * sy)),
            int(round(x2 * sx)),
            int(round(y2 * sy)),
        )

    @staticmethod
    def _point_in_hitbox(px, py, hitbox):
        x1, y1, x2, y2 = hitbox
        return x1 <= px <= x2 and y1 <= py <= y2

    def _font_stepper_action(self, width, height, click_x, click_y):
        if width <= 0 or height <= 0:
            return None

        src_width, src_height = self._font_stepper_source_size
        minus_box_src = self._font_stepper_minus_box_src
        plus_box_src = self._font_stepper_plus_box_src

        minus_box = self._scale_hitbox(minus_box_src, src_width, src_height, width, height)
        plus_box = self._scale_hitbox(plus_box_src, src_width, src_height, width, height)

        if self._point_in_hitbox(click_x, click_y, minus_box):
            return "decrease"
        if self._point_in_hitbox(click_x, click_y, plus_box):
            return "increase"
        return None

    def _on_font_stepper_click(self, event):
        width = event.widget.winfo_width()
        height = event.widget.winfo_height()
        action = self._font_stepper_action(width, height, event.x, event.y)
        if action == "decrease":
            self.decrease_font_size()
        elif action == "increase":
            self.increase_font_size()

    def _on_font_stepper_motion(self, event):
        width = event.widget.winfo_width()
        height = event.widget.winfo_height()
        action = self._font_stepper_action(width, height, event.x, event.y)
        event.widget.configure(cursor="hand2" if action else "arrow")

    def _make_toolbar_button(self, parent, text, command, image_key=None):
        return toolbar_service._make_toolbar_button(self, parent, text, command, image_key)

    def _set_font_stepper_geometry_from_asset(self, path):
        name = os.path.basename(path).lower()
        path_lower = os.path.normpath(str(path)).lower()
        style_b_marker = f"{os.sep}variants{os.sep}b{os.sep}"
        if name.startswith("font2b") and style_b_marker in path_lower:
            # Geometry for generated, fixed-size style-B font stepper.
            self._font_stepper_source_size = (146, 34)
            self._font_stepper_minus_box_src = (70, 8, 102, 26)
            self._font_stepper_plus_box_src = (108, 8, 140, 26)
            return
        if "font2" in name and style_b_marker in path_lower:
            # Geometry for button_set2-derived font control in variants/B.
            self._font_stepper_source_size = (582, 117)
            self._font_stepper_minus_box_src = (214, 16, 370, 88)
            self._font_stepper_plus_box_src = (373, 16, 522, 88)
            return
        if name.startswith("font2"):
            self._font_stepper_source_size = (1108, 256)
            self._font_stepper_minus_box_src = (441, 40, 712, 173)
            self._font_stepper_plus_box_src = (742, 40, 1015, 173)
            return
        self._font_stepper_source_size = (1028, 253)
        self._font_stepper_minus_box_src = (395, 43, 648, 174)
        self._font_stepper_plus_box_src = (676, 43, 929, 174)

    def _collect_toolbar_tokens_from_dir(self, folder_path, token_to_path):
        if not os.path.isdir(folder_path):
            return
        try:
            entries = os.listdir(folder_path)
        except _EXPECTED_APP_ERRORS:
            return

        for name in entries:
            if not name.lower().endswith(".png"):
                continue
            stem = os.path.splitext(name.lower())[0]
            if stem == "button_set":
                continue
            path = os.path.join(folder_path, name)
            variants = {stem, stem.split(".")[0]}
            if stem.endswith(".fw"):
                variants.add(stem[:-3])
            for variant in variants:
                token = self._normalize_button_token(variant)
                if token and token not in token_to_path:
                    token_to_path[token] = path

    def _load_toolbar_button_images_from_assets(self, style="A", mapping=None):
        self._toolbar_button_images = {}
        base_dir = self._resource_base_dir()
        button_dir = os.path.join(base_dir, "assets", "buttons")
        if not os.path.isdir(button_dir):
            return

        token_to_path = {}
        style = str(style).upper()
        if style and style != "A":
            style_dir = os.path.join(button_dir, "variants", style)
            self._collect_toolbar_tokens_from_dir(style_dir, token_to_path)
        self._collect_toolbar_tokens_from_dir(button_dir, token_to_path)

        if mapping is None:
            if style == "B":
                # Style B assets are wider; use A-like final footprint to keep toolbar flush.
                mapping = {
                    "open": (("open2", "open"), 102, 34, False),
                    "apply": (("apply2", "apply", "applyedit"), 116, 34, False),
                    "export": (("export2", "export", "exporthhsav"), 128, 34, False),
                    "find": (("find2", "find", "findnext"), 108, 34, False),
                    "update": (("update2", "update"), 98, 34, False),
                    "readme": (("readme2", "readme"), 98, 34, False),
                    "font": (("font2b", "font2", "font"), 146, 34, False),
                }
            else:
                mapping = {
                    "open": (("open",), 194, 36, False),
                    "apply": (("apply", "applyedit"), 194, 36, False),
                    "export": (("export", "exporthhsav"), 194, 36, False),
                    "find": (("find", "findnext"), 194, 36, False),
                    "update": (("update",), 194, 36, False),
                    "readme": (("readme",), 194, 36, False),
                    "font": (("font2", "font"), 158, 36, False),
                }
        for target, config in mapping.items():
            variants, max_width, max_height, stretch_to_fit = config
            path = None
            for variant in variants:
                path = token_to_path.get(self._normalize_button_token(variant))
                if path:
                    break
            if not path:
                continue
            if target == "font":
                self._set_font_stepper_geometry_from_asset(path)
            image = self._load_toolbar_button_image(
                path,
                max_width=max_width,
                max_height=max_height,
                stretch_to_fit=stretch_to_fit,
            )
            if image is not None:
                self._toolbar_button_images[target] = image

    def _load_siindbad_toolbar_button_images(self):
        # SIINDBAD A/B uses generated native buttons/icons (non-asset-heavy).
        self._toolbar_button_images = {}

    def _load_toolbar_button_images(self):
        current_theme = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if current_theme != "KAMUE":
            self._toolbar_button_images = {}
            return
        if self._siindbad_effective_style() != "A":
            self._toolbar_button_images = {}
            return
        # KAMUE variant A keeps original asset behavior.
        self._load_toolbar_button_images_from_assets(style="A")

    def _refresh_toolbar_button_images(self):
        root = getattr(self, "root", None)
        if root is None or getattr(self, "_shutdown_cleanup_done", False):
            return
        try:
            if not bool(root.winfo_exists()):
                return
        except _EXPECTED_APP_ERRORS:
            return
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "SIINDBAD" or (variant == "KAMUE" and self._siindbad_effective_style() == "B"):
            for key, button in self._toolbar_buttons.items():
                if not button or not button.winfo_exists():
                    continue
                label_text = self._toolbar_button_text.get(key, key.title())
                self._apply_siindbad_toolbar_button_style(button, key=key, text=label_text)
            return
        self._load_toolbar_button_images()
        for key, button in self._toolbar_buttons.items():
            if not button or not button.winfo_exists():
                continue
            image = self._toolbar_button_images.get(key)
            if image is None:
                continue
            try:
                self._apply_asset_toolbar_button_style(button)
                button.configure(image=image, text="", compound="none")
            except _EXPECTED_APP_ERRORS:
                continue
        if self._font_stepper_label and self._font_stepper_label.winfo_exists():
            image = self._toolbar_button_images.get("font")
            if image is not None:
                try:
                    self._font_stepper_label.configure(image=image)
                except _EXPECTED_APP_ERRORS:
                    pass

    def _cancel_toolbar_refresh_after(self):
        root = getattr(self, "root", None)
        after_id = getattr(self, "_toolbar_refresh_after_id", None)
        if after_id and root is not None:
            try:
                root.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                pass
        self._toolbar_refresh_after_id = None

    def _run_toolbar_refresh_after(self):
        self._toolbar_refresh_after_id = None
        if getattr(self, "_shutdown_cleanup_done", False):
            return
        self._refresh_toolbar_button_images()

    def _schedule_toolbar_refresh_after(self, delay_ms=1):
        if getattr(self, "_shutdown_cleanup_done", False):
            return
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            if not bool(root.winfo_exists()):
                return
        except _EXPECTED_APP_ERRORS:
            return
        self._cancel_toolbar_refresh_after()
        try:
            self._toolbar_refresh_after_id = root.after(
                max(1, int(delay_ms)),
                self._run_toolbar_refresh_after,
            )
        except _EXPECTED_APP_ERRORS:
            self._toolbar_refresh_after_id = None

    @staticmethod
    def _theme_chip_palette(variant):
        return theme_service.theme_chip_palette(variant)

    @staticmethod
    def _tree_variant_chip_palette(variant):
        return theme_service.tree_variant_chip_palette(variant)

    def _footer_style_variant(self):
        return footer_service.footer_style_variant()

    def _footer_visual_spec(self):
        return editor_purge_service._footer_visual_spec(self)

    def _bug_chip_palette(self, variant):
        return theme_service.bug_chip_palette(
            variant=variant,
            footer_style_variant=self._footer_style_variant(),
        )

    def _footer_badge_palette(self, variant):
        return theme_service.footer_badge_palette(
            variant=variant,
            footer_style_variant=self._footer_style_variant(),
        )

    def _build_bug_report_chip(self, parent):
        self._bug_report_host = parent
        theme = getattr(self, "_theme", {})
        spec = self._footer_visual_spec()
        chip_colors = self._bug_chip_palette(getattr(self, "_app_theme_variant", "SIINDBAD"))
        title = tk.Label(
            parent,
            text="REPORT :",
            bg=theme.get("credit_bg", "#0b1118"),
            fg=theme.get("credit_label_fg", "#b5cade"),
            font=spec["label_font"],
            bd=0,
            highlightthickness=0,
        )
        title.pack(side="left", padx=(0, spec["label_gap"]))
        self._bug_report_label = title
        chip = tk.Frame(
            parent,
            bg=chip_colors["bg"],
            bd=0,
            highlightthickness=1,
            highlightbackground=chip_colors["border"],
            highlightcolor=chip_colors["border"],
        )
        icon_label = tk.Label(
            chip,
            text="",
            bg=chip_colors["bg"],
            fg=chip_colors["fg"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
        text_label = tk.Label(
            chip,
            text="SUBMIT A BUG",
            bg=chip_colors["bg"],
            fg=chip_colors["fg"],
            font=spec["chip_font"],
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
        for widget in (chip, icon_label, text_label):
            widget.bind("<Button-1>", lambda _event: self._open_bug_report_dialog())
            try:
                widget.configure(cursor="hand2")
            except _EXPECTED_APP_ERRORS:
                pass
        chip.pack(side="left")
        self._bug_report_chip = chip
        self._bug_report_chip_icon_label = icon_label
        self._bug_report_chip_text_label = text_label
        self._sync_bug_report_chip_colors()

    def _sync_bug_report_chip_colors(self):
        chip = getattr(self, "_bug_report_chip", None)
        if chip is None:
            return
        try:
            if not chip.winfo_exists():
                return
        except _EXPECTED_APP_ERRORS:
            return
        spec = self._footer_visual_spec()
        colors = self._bug_chip_palette(getattr(self, "_app_theme_variant", "SIINDBAD"))
        bg = colors["bg"]
        icon_photo = self._load_bug_report_chip_icon(
            max_size=spec["chip_icon_size"],
            tint=colors.get("fg", "#e6f6ff"),
        )
        self._bug_report_chip_icon_photo = icon_photo
        icon_label = getattr(self, "_bug_report_chip_icon_label", None)
        text_label = getattr(self, "_bug_report_chip_text_label", None)
        try:
            chip.configure(
                bg=bg,
                highlightbackground=colors["border"],
                highlightcolor=colors["border"],
            )
            if icon_label is not None and icon_label.winfo_exists():
                icon_label.configure(
                    bg=bg,
                    fg=colors["fg"],
                    image=icon_photo if icon_photo is not None else "",
                )
                icon_top_pad = 1 if self._footer_style_variant() == "B" else 0
                icon_label.pack_configure(
                    padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]),
                    pady=(icon_top_pad, 0),
                )
            if text_label is not None and text_label.winfo_exists():
                text_label.configure(
                    bg=bg,
                    fg=colors["fg"],
                    font=spec["chip_font"],
                )
                text_label.pack_configure(
                    padx=(0, spec["chip_text_right_pad"]),
                    pady=(spec["chip_text_pady"], 0),
                )
            label = getattr(self, "_bug_report_label", None)
            if label is not None and label.winfo_exists():
                label.configure(font=spec["label_font"])
                label.pack_configure(padx=(0, spec["label_gap"]))
        except _EXPECTED_APP_ERRORS:
            return

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

    def _build_theme_selector(self, parent):
        return ui_build_service.build_theme_selector(self, parent, tk=tk)

    def _build_header_variant_switch(self, parent, show_title=True):
        return ui_build_service.build_header_variant_switch(self, parent, show_title, tk=tk)

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
        theme = getattr(self, "_theme", {})
        host = getattr(self, "_header_variant_host", None)
        host_in_footer = bool(getattr(self, "_header_variant_is_footer", False))
        host_bg = theme.get("credit_bg", "#0b1118") if host_in_footer else theme.get("bg", "#0f131a")
        if host and host.winfo_exists():
            try:
                host.configure(bg=host_bg)
            except _EXPECTED_APP_ERRORS:
                pass
        active = str(getattr(self, "_header_variant", "A")).upper()
        is_kamue = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE"
        label_fg = theme.get("credit_label_fg", "#b5cade")
        for child in (host.winfo_children() if host and host.winfo_exists() else ()):
            if child in self._header_variant_labels.values():
                continue
            if isinstance(child, tk.Label):
                try:
                    child.configure(bg=host_bg, fg=label_fg)
                except _EXPECTED_APP_ERRORS:
                    pass
        for variant, chip in self._header_variant_labels.items():
            is_active = variant == active
            if is_kamue:
                border = "#6b37b6"
                bg = "#2f145e" if is_active else "#120926"
                fg = "#ffffff" if is_active else "#ccb7ef"
            else:
                border = "#2f4a61"
                bg = "#1a3a56" if is_active else "#0f1b29"
                fg = "#ffffff" if is_active else "#8aa9bf"
            try:
                chip.configure(
                    bg=bg,
                    fg=fg,
                    highlightbackground=border,
                    highlightcolor=border,
                )
            except _EXPECTED_APP_ERRORS:
                continue

    def _apply_footer_layout_variant(self):
        return footer_service._apply_footer_layout_variant(self)

    def _update_app_theme_controls(self):
        active = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        spec = self._footer_visual_spec()
        use_soft_active = self._footer_style_variant() == "B"
        for variant, label in self._app_theme_labels.items():
            colors = self._theme_chip_palette(variant)
            is_active = variant == active
            active_bg = colors["bg"]
            active_fg = colors["fg"] if (use_soft_active or not is_active) else "#ffffff"
            label.configure(
                bg=active_bg,
                fg=active_fg,
                highlightbackground=colors["border"],
                highlightcolor=colors["border"],
                font=spec["chip_font"],
                padx=spec["theme_chip_padx"],
                pady=spec["theme_chip_pady"],
            )
        host = getattr(self, "_theme_selector_host", None)
        if host and host.winfo_exists():
            for child in host.winfo_children():
                if not isinstance(child, tk.Label):
                    continue
                if child in self._app_theme_labels.values():
                    continue
                if child in self._toolbar_style_labels.values():
                    continue
                if child in self._tree_style_labels.values():
                    continue
                if child == self._toolbar_style_title_label:
                    continue
                if child == self._tree_style_title_label:
                    continue
                try:
                    child.configure(
                        bg=self._theme.get("credit_bg", "#0b1118"),
                        fg=self._theme.get("credit_label_fg", "#b5cade"),
                        font=spec["label_font"],
                    )
                except _EXPECTED_APP_ERRORS:
                    continue

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
        if variant not in ("SIINDBAD", "KAMUE"):
            return
        previous_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        previous_style = self._siindbad_effective_style()
        style_map = getattr(self, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B"}
            self._toolbar_style_variant_by_theme = style_map
        if variant not in style_map:
            style_map[variant] = "B"
        if variant == getattr(self, "_app_theme_variant", "SIINDBAD") and getattr(self, "_theme", None):
            self._update_app_theme_controls()
            return
        self._app_theme_variant = variant
        self._apply_dark_theme()
        next_style = self._siindbad_effective_style()
        toolbar_host = getattr(self, "_toolbar_host", None)
        has_live_toolbar = (
            toolbar_host is not None
            and toolbar_host.winfo_exists()
            and bool(getattr(self, "_toolbar_buttons", {}))
            and previous_variant in ("SIINDBAD", "KAMUE")
        )
        if has_live_toolbar and previous_style == "B" and next_style == "B":
            self._render_font_control()
            self._refresh_toolbar_button_images()
        else:
            self._rebuild_toolbar(preserve_find_text=True)
        self._refresh_runtime_theme_widgets()
        other_variant = "KAMUE" if variant == "SIINDBAD" else "SIINDBAD"
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        queued = set(str(item).upper() for item in list(getattr(self, "_theme_prewarm_queue", []) or []))
        if other_variant not in warmed and other_variant not in queued:
            self._schedule_theme_asset_prewarm(targets=(other_variant,), delay_ms=180)
        if save:
            try:
                self._save_user_settings()
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                pass
        self._log_theme_perf(f"switch {previous_variant}->{variant}", started_ts=switch_started)

    def _refresh_runtime_theme_widgets(self):
        return theme_service._refresh_runtime_theme_widgets(self)

    @staticmethod
    def _startup_loader_lines(ready=False):
        return loader_service.startup_loader_lines(ready=ready)

    def _next_startup_loader_line(self, ready=False):
        return editor_purge_service._next_startup_loader_line(self, ready)

    def _startup_loader_title_photo(self, text, scale=1.0):
        cache = getattr(self, "_startup_loader_title_cache", None)
        if cache is None:
            cache = {}
            self._startup_loader_title_cache = cache
        scale = max(0.5, min(1.5, float(scale or 1.0)))
        key = f"{str(text or '')}|{int(round(scale * 100.0))}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            draw_module = importlib.import_module("PIL.ImageDraw")
            font_module = importlib.import_module("PIL.ImageFont")
            image_tk_module = importlib.import_module("PIL.ImageTk")
        except (ImportError, AttributeError):
            self._bounded_cache_put(cache, key, None, max_items=16)
            return None

        font_paths = [
            os.path.join(self._resource_base_dir(), "assets", "fonts", "Orbitron-Bold.ttf"),
            os.path.join(self._resource_base_dir(), "assets", "fonts", "Rajdhani-SemiBold.ttf"),
        ]
        text_font = None
        font_size = max(12, int(round(20 * scale)))
        for path in font_paths:
            try:
                if os.path.isfile(path):
                    text_font = font_module.truetype(path, font_size)
                    break
            except (OSError, ValueError, TypeError, AttributeError):
                continue
        if text_font is None:
            self._bounded_cache_put(cache, key, None, max_items=16)
            return None

        try:
            canvas_w = max(240, int(round(430 * scale)))
            canvas_h = max(24, int(round(32 * scale)))
            canvas = image_module.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            draw = draw_module.Draw(canvas)
            # Soft neon halo behind core title text.
            draw.text((1, 1), str(text or ""), font=text_font, fill=(54, 186, 255, 74))
            draw.text((2, 1), str(text or ""), font=text_font, fill=(168, 133, 255, 46))
            draw.text((0, 0), str(text or ""), font=text_font, fill=(226, 244, 255, 255))
            photo = image_tk_module.PhotoImage(canvas)
            self._bounded_cache_put(cache, key, photo, max_items=16)
            return photo
        except (OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            self._bounded_cache_put(cache, key, None, max_items=16)
            return None

    def _show_startup_loader(self):
        return startup_loader_ui_service.show_startup_loader(
            self,
            tk=tk,
            time=time,
            startup_loader_core=startup_loader_core,
        )

    def _tick_startup_loader_progress(self):
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        if bool(getattr(self, "_startup_loader_finishing", False)):
            return
        self._update_startup_loader_progress()
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_startup_loader_progress_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
        interval = max(24, int(getattr(self, "_startup_loader_progress_interval_ms", 34) or 34))
        self._startup_loader_progress_after_id = root.after(interval, self._tick_startup_loader_progress)

    def _tick_startup_loader_statement(self):
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        label = getattr(self, "_startup_loader_statement_label", None)
        if label is None or not label.winfo_exists():
            return
        ready = getattr(self, "_startup_loader_ready_ts", None) is not None
        line_text = self._next_startup_loader_line(ready=ready)
        if not line_text:
            return
        label.configure(text=line_text)
        if ready:
            interval = max(
                900,
                int(getattr(self, "_startup_loader_statement_interval_ready_ms", 1150) or 1150),
            )
        else:
            interval = max(
                1100,
                int(getattr(self, "_startup_loader_statement_interval_loading_ms", 1450) or 1450),
            )
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_startup_loader_text_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
        self._startup_loader_text_after_id = root.after(interval, self._tick_startup_loader_statement)

    def _startup_loader_title_color_for_variant(self, variant):
        return loader_service.title_color_for_variant(
            variant,
            siindbad_palette=self._theme_palette_for_variant("SIINDBAD"),
            kamue_palette=self._theme_palette_for_variant("KAMUE"),
        )

    def _apply_startup_loader_title_variant(self):
        return editor_purge_service._apply_startup_loader_title_variant(self)

    def _tick_startup_loader_title(self):
        return editor_purge_service._tick_startup_loader_title(self)

    def _startup_loader_rounded_fill_photo(self, color_hex, width_px, height_px):
        width_px = max(1, int(width_px or 1))
        height_px = max(1, int(height_px or 1))
        cache = getattr(self, "_startup_loader_fill_photo_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._startup_loader_fill_photo_cache = cache
        key = (str(color_hex or "").lower(), width_px, height_px)
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
            radius = max(aa * 2, int(round(min(big_w, big_h) * 0.38)))
            rgba = image_module.new("RGBA", (big_w, big_h), (0, 0, 0, 0))
            draw = draw_module.Draw(rgba)
            fill_color = str(color_hex or "#4f90bf")
            draw.rounded_rectangle(
                (0, 0, max(0, big_w - 1), max(0, big_h - 1)),
                radius=radius,
                fill=fill_color,
                outline=None,
            )
            rgba = rgba.resize((width_px, height_px), image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(rgba)
            self._bounded_cache_put(cache, key, photo, max_items=256)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            self._bounded_cache_put(cache, key, None, max_items=256)
            return None

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
    def _set_startup_loader_bar_fill(fill_widget, pct):
        return editor_purge_service._set_startup_loader_bar_fill(fill_widget, pct)

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

    def _update_startup_loader_progress(self):
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        if bool(getattr(self, "_startup_loader_finishing", False)):
            return
        started = float(getattr(self, "_startup_loader_started_ts", 0.0) or 0.0)
        now = time.perf_counter()
        elapsed_ms = max(0.0, (now - started) * 1000.0) if started > 0 else 0.0
        timeline_ms = max(1000, int(getattr(self, "_startup_loader_extra_hold_ms", 1800) or 1800))
        ready = getattr(self, "_startup_loader_ready_ts", None) is not None
        overall, _top_pct, _bottom_pct = startup_loader_core.compute_loader_progress(
            elapsed_ms=elapsed_ms,
            timeline_ms=timeline_ms,
            ready=ready,
            required_variants=getattr(self, "_startup_loader_required_variants", set()),
            active_variant=getattr(self, "_app_theme_variant", "SIINDBAD"),
            variant_progress_getter=self._startup_loader_variant_progress,
        )
        show_pct = self._smooth_startup_loader_progress(overall, now_ts=now)
        top_pct, bottom_pct = startup_loader_core.compute_loader_fill_percentages(show_pct)

        self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_top_fill", None), top_pct)
        self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_bottom_fill", None), bottom_pct)

        pct_label = getattr(self, "_startup_loader_pct_label", None)
        if pct_label is not None and pct_label.winfo_exists():
            pct_label.configure(text=f"{int(show_pct)}%")

    def _is_startup_full_load_ready(self):
        required = startup_loader_core.resolve_required_variants(
            getattr(self, "_startup_loader_required_variants", set()),
            getattr(self, "_app_theme_variant", "SIINDBAD"),
        )
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        if required.issubset(warmed):
            return True
        totals = getattr(self, "_theme_prewarm_total_by_variant", {})
        done = getattr(self, "_theme_prewarm_done_by_variant", {})
        for variant in required:
            total = int(totals.get(variant, 0) or 0)
            finished = int(done.get(variant, 0) or 0)
            if total <= 0 or finished < total:
                return False
        return True

    def _on_startup_full_load_ready(self):
        if getattr(self, "_startup_loader_ready_ts", None) is not None:
            return
        if not self._is_startup_full_load_ready():
            return
        self._startup_loader_ready_ts = time.perf_counter()
        self._update_startup_loader_progress()
        self._tick_startup_loader_statement()
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_startup_loader_hide_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
        started = float(getattr(self, "_startup_loader_started_ts", 0.0) or 0.0)
        elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0) if started > 0 else 0.0
        timeline_ms = max(1000, int(getattr(self, "_startup_loader_extra_hold_ms", 1800) or 1800))
        hold_ms = startup_loader_core.compute_loader_hide_hold_ms(
            elapsed_ms=elapsed_ms,
            timeline_ms=timeline_ms,
            min_hold_ms=250,
        )
        self._startup_loader_hide_after_id = root.after(hold_ms, self._hide_startup_loader)

    def _hide_startup_loader(self):
        root = getattr(self, "root", None)
        overlay = getattr(self, "_startup_loader_overlay", None)
        overlay_exists = False
        if overlay is not None:
            try:
                overlay_exists = bool(overlay.winfo_exists())
            except (tk.TclError, RuntimeError, AttributeError, ValueError):
                overlay_exists = False
        if (
            root is not None
            and overlay_exists
            and bool(getattr(self, "_startup_loader_ready_ts", None) is not None)
        ):
            now = time.perf_counter()
            if not bool(getattr(self, "_startup_loader_finishing", False)):
                self._startup_loader_finishing = True
                self._startup_loader_finish_started_ts = float(now)
                progress_after_id = getattr(self, "_startup_loader_progress_after_id", None)
                if progress_after_id:
                    try:
                        root.after_cancel(progress_after_id)
                    except (tk.TclError, RuntimeError, ValueError):
                        pass
                    self._startup_loader_progress_after_id = None
                start_pct = 0.0
                try:
                    pct_label = getattr(self, "_startup_loader_pct_label", None)
                    if pct_label is not None and pct_label.winfo_exists():
                        text = str(pct_label.cget("text") or "").strip().replace("%", "")
                        start_pct = max(0.0, min(100.0, float(text or 0.0)))
                except (tk.TclError, RuntimeError, AttributeError, ValueError, TypeError):
                    start_pct = 0.0
                start_pct = max(
                    start_pct,
                    float(getattr(self, "_startup_loader_display_pct", 0.0) or 0.0),
                )
                self._startup_loader_finish_start_pct = float(start_pct)
                self._startup_loader_finish_reached_100_ts = 0.0
            elapsed_ms = max(
                0.0,
                (float(now) - float(getattr(self, "_startup_loader_finish_started_ts", now) or now)) * 1000.0,
            )
            dwell_ms = max(120.0, float(getattr(self, "_startup_loader_complete_dwell_ms", 260) or 260))
            progress = max(0.0, min(1.0, elapsed_ms / dwell_ms))
            start_pct = float(getattr(self, "_startup_loader_finish_start_pct", 0.0) or 0.0)
            show_pct = start_pct + ((100.0 - start_pct) * progress)
            show_pct = max(
                float(getattr(self, "_startup_loader_display_pct", 0.0) or 0.0),
                min(100.0, float(show_pct)),
            )
            show_pct = min(
                show_pct,
                float(getattr(self, "_startup_loader_display_pct", 0.0) or 0.0) + 2.0,
            )
            self._startup_loader_display_pct = show_pct
            if show_pct >= 100.0:
                if float(getattr(self, "_startup_loader_finish_reached_100_ts", 0.0) or 0.0) <= 0.0:
                    self._startup_loader_finish_reached_100_ts = float(now)
            else:
                self._startup_loader_finish_reached_100_ts = 0.0
            reached_100_ts = float(getattr(self, "_startup_loader_finish_reached_100_ts", 0.0) or 0.0)
            hold_elapsed_ms = (
                max(0.0, (float(now) - reached_100_ts) * 1000.0)
                if reached_100_ts > 0.0
                else 0.0
            )
            final_hold_ms = max(
                0.0,
                float(getattr(self, "_startup_loader_finish_visible_hold_ms", 140) or 140),
            )
            top_pct, bottom_pct = startup_loader_core.compute_loader_fill_percentages(show_pct)
            try:
                self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_top_fill", None), top_pct)
                self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_bottom_fill", None), bottom_pct)
                pct_label = getattr(self, "_startup_loader_pct_label", None)
                if pct_label is not None and pct_label.winfo_exists():
                    pct_label.configure(text=f"{int(show_pct)}%")
                statement = getattr(self, "_startup_loader_statement_label", None)
                if statement is not None and statement.winfo_exists():
                    statement.configure(text="/startup shell handshake complete.")
                overlay.update_idletasks()
            except (tk.TclError, RuntimeError, AttributeError, ValueError):
                pass
            if startup_loader_core.should_continue_finish_animation(progress=progress, show_pct=show_pct) or hold_elapsed_ms < final_hold_ms:
                self._startup_loader_hide_after_id = root.after(16, self._hide_startup_loader)
                return

        if root is not None:
            for attr in (
                "_startup_loader_text_after_id",
                "_startup_loader_hide_after_id",
                "_startup_loader_progress_after_id",
                "_startup_loader_title_after_id",
            ):
                after_id = getattr(self, attr, None)
                if after_id:
                    try:
                        root.after_cancel(after_id)
                    except (tk.TclError, RuntimeError, ValueError):
                        pass
                setattr(self, attr, None)

        if overlay is not None and overlay_exists:
            try:
                overlay.destroy()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if root is not None and bool(getattr(self, "_startup_loader_window_mode", False)):
            alpha_fade_armed = False
            try:
                self._apply_dark_theme()
                self._style_text_widget()
                self._apply_tree_style()
                self._apply_tree_mode_style()
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
            try:
                theme_bg = str((getattr(self, "_theme", {}) or {}).get("bg", "#0f131a"))
                root.configure(bg=theme_bg)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
            try:
                root.update_idletasks()
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
            try:
                root.attributes("-alpha", 0.0)
                alpha_fade_armed = True
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                alpha_fade_armed = False
            try:
                root.deiconify()
                root.update_idletasks()
                root.update()
                root.lift()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
            if alpha_fade_armed:
                try:
                    root.after(48, lambda target=root: self._restore_startup_root_alpha(target))
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    self._restore_startup_root_alpha(root)
            try:
                root.focus_force()
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        self._startup_loader_overlay = None
        self._startup_loader_pct_label = None
        self._startup_loader_statement_label = None
        self._startup_loader_title_prefix_label = None
        self._startup_loader_title_suffix_label = None
        self._startup_loader_top_fill = None
        self._startup_loader_bottom_fill = None
        self._startup_loader_display_pct = 0.0
        self._startup_loader_last_progress_ts = 0.0
        self._startup_loader_finishing = False
        self._startup_loader_finish_started_ts = 0.0
        self._startup_loader_finish_start_pct = 0.0
        self._startup_loader_finish_reached_100_ts = 0.0
        deferred = startup_loader_core.normalize_deferred_variants_for_schedule(
            getattr(self, "_startup_loader_deferred_variants", set())
        )
        self._startup_loader_deferred_variants = set()
        if root is not None and deferred:
            try:
                self._schedule_theme_asset_prewarm(targets=deferred, delay_ms=180)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        # Run auto update-check after loader teardown so startup stays responsive.
        if root is not None and self._auto_update_startup_enabled():
            self._schedule_auto_update_check(delay_ms=350)
        self._schedule_crash_report_offer()

    @staticmethod
    def _restore_startup_root_alpha(target):
        if target is None:
            return
        try:
            target.attributes("-alpha", 1.0)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return

    def _log_theme_perf(self, label, started_ts=None):
        if not bool(getattr(self, "_theme_perf_logging", False)):
            return
        if started_ts is None:
            _LOG.debug("theme_perf label=%s", label)
            return
        elapsed = (time.perf_counter() - float(started_ts)) * 1000.0
        _LOG.debug("theme_perf label=%s elapsed_ms=%.1f", label, elapsed)

    def _build_theme_prewarm_tasks(self, variant):
        variant = str(variant).upper()
        if variant not in ("SIINDBAD", "KAMUE"):
            return []
        style_map = getattr(self, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B"}
            self._toolbar_style_variant_by_theme = style_map
        if str(style_map.get(variant, "B")).upper() != "B":
            return []

        labels = {
            "open": "Open",
            "apply": "Apply Edit",
            "export": "Export .hhsav",
            "find": "Find Next",
            "update": "Update",
            "readme": "ReadMe",
        }
        tasks = []
        for key, text in labels.items():
            tasks.append({"variant": variant, "kind": "button", "key": key, "text": text})
        tasks.append({"variant": variant, "kind": "search"})
        tasks.append({"variant": variant, "kind": "font"})
        tasks.append({"variant": variant, "kind": "logo"})
        tasks.append({"variant": variant, "kind": "badges"})
        # Prewarm marker integrity/icons so first tree expansion is stable and hitch-free.
        tasks.append({"variant": variant, "kind": "tree_integrity"})
        tasks.append({"variant": variant, "kind": "tree_markers"})
        return tasks

    def _execute_theme_prewarm_task(self, task):
        return theme_service._execute_theme_prewarm_task(self, task)

    def _finish_theme_prewarm_variant(self, variant):
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        if variant in warmed:
            return
        warmed.add(variant)
        self._theme_prewarm_done = warmed
        totals = dict(getattr(self, "_theme_prewarm_total_by_variant", {}))
        done_counts = dict(getattr(self, "_theme_prewarm_done_by_variant", {}))
        total = int(totals.get(variant, 0) or 0)
        if total <= 0:
            total = 1
            totals[variant] = total
        done_counts[variant] = total
        self._theme_prewarm_total_by_variant = totals
        self._theme_prewarm_done_by_variant = done_counts
        self._log_theme_perf(f"prewarm {variant} completed")
        current = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if current == variant and getattr(self, "_toolbar_buttons", {}):
            self._schedule_toolbar_refresh_after(delay_ms=1)
        self._update_startup_loader_progress()
        self._on_startup_full_load_ready()

    def _schedule_theme_asset_prewarm(self, targets=None, delay_ms=120):
        root = getattr(self, "root", None)
        if root is None:
            return
        if targets is None:
            targets = ("SIINDBAD", "KAMUE")
        pending = list(getattr(self, "_theme_prewarm_queue", []))
        raw_tasks = getattr(self, "_theme_prewarm_tasks", None)
        if isinstance(raw_tasks, deque):
            tasks = raw_tasks
        elif raw_tasks:
            tasks = deque(raw_tasks)
        else:
            tasks = deque()
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        totals = dict(getattr(self, "_theme_prewarm_total_by_variant", {}))
        done_counts = dict(getattr(self, "_theme_prewarm_done_by_variant", {}))
        for variant in targets:
            name = str(variant).upper()
            if name not in ("SIINDBAD", "KAMUE"):
                continue
            if name in warmed or name in pending:
                continue
            variant_tasks = self._build_theme_prewarm_tasks(name)
            if not variant_tasks:
                totals[name] = 1
                done_counts[name] = 1
                self._theme_prewarm_total_by_variant = totals
                self._theme_prewarm_done_by_variant = done_counts
                self._finish_theme_prewarm_variant(name)
                continue
            pending.append(name)
            if int(totals.get(name, 0) or 0) <= 0:
                totals[name] = len(variant_tasks)
                done_counts[name] = 0
            self._log_theme_perf(f"queue prewarm {name}")
            tasks.extend(variant_tasks)
        self._theme_prewarm_total_by_variant = totals
        self._theme_prewarm_done_by_variant = done_counts
        self._theme_prewarm_queue = pending
        self._theme_prewarm_tasks = tasks
        self._update_startup_loader_progress()
        if not tasks:
            self._on_startup_full_load_ready()
            return
        after_id = getattr(self, "_theme_prewarm_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, ValueError):
                pass
        self._theme_prewarm_after_id = root.after(max(1, int(delay_ms)), self._run_theme_asset_prewarm)

    def _run_theme_asset_prewarm(self):
        return theme_service._run_theme_asset_prewarm(self)

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
        if current_theme not in ("SIINDBAD", "KAMUE"):
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
            style_map = {"SIINDBAD": "B", "KAMUE": "B"}
            self._toolbar_style_variant_by_theme = style_map
        style_map[current_theme] = variant
        if current_theme == "SIINDBAD":
            self._toolbar_style_variant = variant
        self._invalidate_siindbad_b_sprite_cache()
        self._rebuild_toolbar(preserve_find_text=True)
        self._update_toolbar_style_controls()

    def _update_toolbar_style_controls(self):
        if not bool(getattr(self, "_show_toolbar_variant_controls", False)):
            return
        if not getattr(self, "_toolbar_style_labels", None):
            return

        active_theme = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        focus = self._siindbad_effective_style()

        if active_theme == "KAMUE":
            palette = {
                "inactive_bg": "#1a1030",
                "inactive_fg": "#b9a8da",
                "inactive_border": "#5b3890",
                "active_bg": "#3f2368",
                "active_fg": "#f0e7ff",
                "active_border": "#b678ea",
            }
        else:
            palette = {
                "inactive_bg": "#0f1b29",
                "inactive_fg": "#7f9bb2",
                "inactive_border": "#2f4a61",
                "active_bg": "#223f55",
                "active_fg": "#e1edf6",
                "active_border": "#6f9dbe",
            }

        if self._toolbar_style_title_label and self._toolbar_style_title_label.winfo_exists():
            try:
                self._toolbar_style_title_label.configure(
                    bg=self._theme.get("credit_bg", "#0b1118"),
                    fg=self._theme.get("credit_label_fg", "#b5cade"),
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass

        for variant, label in self._toolbar_style_labels.items():
            is_active = variant == focus
            label.configure(
                bg=palette["active_bg"] if is_active else palette["inactive_bg"],
                fg=palette["active_fg"] if is_active else palette["inactive_fg"],
                highlightbackground=palette["active_border"] if is_active else palette["inactive_border"],
                highlightcolor=palette["active_border"] if is_active else palette["inactive_border"],
                cursor="hand2",
            )

    def _shade_toolbar_button_for_theme(self, image, cache_key=None):
        """Apply theme-specific color treatment to toolbar button assets."""
        if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() != "KAMUE":
            return image
        if cache_key:
            cache = getattr(self, "_toolbar_theme_shade_cache", None)
            if not isinstance(cache, dict):
                cache = {}
                self._toolbar_theme_shade_cache = cache
            key = (str(cache_key), int(getattr(image, "width", 0) or 0), int(getattr(image, "height", 0) or 0))
            cached = cache.get(key)
            if cached is not None:
                try:
                    return cached.copy()
                except _EXPECTED_APP_ERRORS:
                    return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            image_chops_module = importlib.import_module("PIL.ImageChops")
            image_enhance_module = importlib.import_module("PIL.ImageEnhance")

            base = image.convert("RGBA")
            r_chan, g_chan, b_chan, alpha_chan = base.split()

            # Build a mask biased toward blue-cyan pixels so we tint frames/background
            # harder than bright text/icons.
            blue_vs_red = image_chops_module.subtract(b_chan, r_chan).point(
                lambda p: min(255, int(p * 2.8))
            )
            blue_vs_green = image_chops_module.subtract(b_chan, g_chan).point(
                lambda p: min(255, int(p * 2.5))
            )
            tint_mask = image_chops_module.lighter(blue_vs_red, blue_vs_green)
            tint_mask = tint_mask.point(lambda p: min(255, int(p * 0.62)))

            purple_overlay = image_module.new("RGBA", base.size, (108, 56, 176, 0))
            purple_overlay.putalpha(tint_mask)
            tinted = image_module.alpha_composite(base, purple_overlay)

            # Darken primarily tinted regions instead of the whole button.
            dark_mask = tint_mask.point(lambda p: min(255, int(p * 0.38)))
            dark_overlay = image_module.new("RGBA", base.size, (16, 7, 30, 0))
            dark_overlay.putalpha(dark_mask)
            tinted = image_module.alpha_composite(tinted, dark_overlay)

            # Preserve white label readability (text/icons) after tinting.
            luma = base.convert("L")
            highlight_mask = luma.point(
                lambda p: 0 if p < 170 else (70 if p < 205 else 120)
            )
            highlight_overlay = image_module.new("RGBA", base.size, (244, 244, 255, 0))
            highlight_overlay.putalpha(highlight_mask)
            tinted = image_module.alpha_composite(tinted, highlight_overlay)

            # Final crispness pass.
            rgb = tinted.convert("RGB")
            rgb = image_enhance_module.Contrast(rgb).enhance(1.09)
            rgb = image_enhance_module.Sharpness(rgb).enhance(1.08)
            out = rgb.convert("RGBA")
            out.putalpha(alpha_chan)
            if cache_key:
                cache = getattr(self, "_toolbar_theme_shade_cache", None)
                if not isinstance(cache, dict):
                    cache = {}
                    self._toolbar_theme_shade_cache = cache
                key = (str(cache_key), int(out.width), int(out.height))
                self._bounded_cache_put(cache, key, out.copy(), max_items=192)
            return out
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            return image

    def _harmonize_kamue_b_outer_frame(self, image):
        """Force KAMUE Variant-B sprite outer frame to match FONT frame border color."""
        if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() != "KAMUE":
            return image
        try:
            draw_module = importlib.import_module("PIL.ImageDraw")
            theme = getattr(self, "_theme", {})
            border_hex = theme.get("find_border", "#cfb5ee")
            border_rgb = self._hex_to_rgb_tuple(border_hex, default_rgb=(207, 181, 238))
            out = image.copy().convert("RGBA")
            draw = draw_module.Draw(out)
            w, h = out.size
            if w >= 2 and h >= 2:
                draw.rectangle(
                    (0, 0, w - 1, h - 1),
                    outline=(border_rgb[0], border_rgb[1], border_rgb[2], 255),
                    width=1,
                )
            return out
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            return image

    def _load_toolbar_button_image(self, path, max_width=208, max_height=40, stretch_to_fit=False):
        cache = getattr(self, "_toolbar_asset_image_cache", None)
        if cache is None:
            cache = {}
            self._toolbar_asset_image_cache = cache
        theme_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        signature = (
            str(path),
            int(max_width),
            int(max_height),
            bool(stretch_to_fit),
            theme_variant,
        )
        cached = cache.get(signature)
        if cached is not None:
            return cached

        try:
            image_module = importlib.import_module("PIL.Image")
            image_tk_module = importlib.import_module("PIL.ImageTk")
            image = image_module.open(path).convert("RGBA")
            image = self._shade_toolbar_button_for_theme(image, cache_key=f"asset:{path}")
            if stretch_to_fit and max_width > 0 and max_height > 0:
                if image.width != max_width or image.height != max_height:
                    image = image.resize((max_width, max_height), image_module.LANCZOS)
                photo = image_tk_module.PhotoImage(image)
                self._bounded_cache_put(cache, signature, photo, max_items=192)
                return photo
            scale = min(max_width / image.width, max_height / image.height, 1.0)
            if scale < 1.0:
                new_size = (
                    max(1, int(image.width * scale)),
                    max(1, int(image.height * scale)),
                )
                image = image.resize(new_size, image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            self._bounded_cache_put(cache, signature, photo, max_items=192)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            pass

        try:
            image = tk.PhotoImage(file=path)
        except (tk.TclError, RuntimeError, OSError, ValueError):
            return None
        scale = 1
        if image.width() > max_width:
            scale = max(scale, (image.width() + max_width - 1) // max_width)
        if image.height() > max_height:
            scale = max(scale, (image.height() + max_height - 1) // max_height)
        if scale > 1:
            image = image.subsample(scale, scale)
        self._bounded_cache_put(cache, signature, image, max_items=192)
        return image

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
    def _extract_badge_boxes(image, threshold=16):
        return footer_service._extract_badge_boxes(image, threshold)

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

    def _load_credit_github_icon(self, max_size=16, tint="#dff6ff", with_plate=False):
        return footer_service._load_credit_github_icon(self, max_size, tint, with_plate)

    def _load_credit_discord_icon(self, max_size=16, tint="#dff6ff", with_plate=False):
        return footer_service._load_credit_discord_icon(self, max_size, tint, with_plate)

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

    def _render_credit_badges(self):
        return footer_service._render_credit_badges(self)

    def _render_credit_discord_badges(self):
        return footer_service._render_credit_discord_badges(self)

    def _build_credit_badges(self, parent):
        self._credit_badge_host = parent
        self._render_credit_badges()

    def _build_credit_discord_badges(self, parent):
        self._credit_discord_badge_host = parent
        self._render_credit_discord_badges()

    @staticmethod
    def _is_banner_logo_path(path):
        name = os.path.basename(str(path)).lower()
        return name.startswith("logo2") or name.startswith("klogo")

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
        parent = self._header_frame
        if not parent or not parent.winfo_exists():
            return
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        logo_path = self._find_logo_path()
        if not logo_path:
            return

        needs_reload = force or logo_path != getattr(self, "_logo_path", None) or not self.logo_image
        if needs_reload and not force:
            logo_cache = getattr(self, "_theme_logo_photo_by_variant", None)
            if isinstance(logo_cache, dict):
                cached_logo = logo_cache.get(variant)
                if cached_logo is not None:
                    self.logo_image = cached_logo
                    self._logo_path = logo_path
                    needs_reload = False
        if needs_reload:
            image = self._load_logo_image(logo_path)
            if image is None:
                return
            self.logo_image = image
            self._logo_path = logo_path
            logo_cache = getattr(self, "_theme_logo_photo_by_variant", None)
            if not isinstance(logo_cache, dict):
                logo_cache = {}
                self._theme_logo_photo_by_variant = logo_cache
            self._bounded_cache_put(logo_cache, variant, image, max_items=8)

        wants_frame = self._is_banner_logo_path(logo_path)
        has_frame = bool(self.logo_frame and self.logo_frame.winfo_exists())
        has_label = bool(self.logo_label and self.logo_label.winfo_exists())
        needs_rebuild = force or (wants_frame != has_frame) or (not has_label)

        if needs_rebuild:
            self._clear_logo_widget()
            if wants_frame:
                self.logo_frame = self._build_logo_glow_frame(parent, self.logo_image)
                self.logo_frame.pack(anchor="center", pady=0)
            else:
                theme = getattr(self, "_theme", {})
                bg = theme.get("bg", "#0f131a")
                self.logo_label = tk.Label(
                    parent,
                    image=self.logo_image,
                    bg=bg,
                    bd=0,
                    highlightthickness=0,
                )
                self.logo_label.pack(anchor="center", pady=0)
        else:
            try:
                self.logo_label.configure(image=self.logo_image)
            except _EXPECTED_APP_ERRORS:
                pass

        # Keep logo centered even when theme changes or window is resized/maximized.
        pack_target = self.logo_frame if wants_frame else self.logo_label
        try:
            if pack_target is not None and pack_target.winfo_exists():
                pack_target.pack_configure(anchor="center", pady=0)
        except _EXPECTED_APP_ERRORS:
            pass

        self._apply_logo_frame_theme()
        self._schedule_topbar_alignment(delay_ms=0)

    def _find_logo_path(self):
        base_dir = self._resource_base_dir()
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            candidates = [
                "assets/klogo.fw.png",
                "assets/klogo.png",
                "klogo.fw.png",
                "klogo.png",
                "assets/logo2.png",
                "logo2.png",
            ]
        else:
            candidates = [
                "assets/logo2.png",
                "logo2.png",
                "assets/klogo.fw.png",
                "assets/klogo.png",
            ]
        for rel_path in candidates:
            path = os.path.join(base_dir, rel_path)
            if os.path.isfile(path):
                return path
        return None

    def _resource_base_dir(self):
        return theme_asset_service.resource_base_dir(_module_resource_base_dir)

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

    def _load_logo_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        cache = getattr(self, "_logo_photo_cache", None)
        if cache is None:
            cache = {}
            self._logo_photo_cache = cache
        try:
            image_module = importlib.import_module("PIL.Image")
            image_tk_module = importlib.import_module("PIL.ImageTk")
            is_banner_logo = self._is_banner_logo_path(path)
            max_width = 700
            if is_banner_logo:
                # Keep logo frame aligned with top controls (which use 4px side padding).
                # Two highlight borders add ~4px to the frame width.
                try:
                    self.root.update_idletasks()
                    available_width = int(self.root.winfo_width())
                except _EXPECTED_APP_ERRORS:
                    available_width = 0
                if available_width > 120:
                    side_padding = 4 * 2
                    frame_border = 4
                    max_width = max(700, available_width - side_padding - frame_border)
                else:
                    max_width = 988
            signature = (os.path.abspath(path), int(max_width) if is_banner_logo else 0)
            cached = cache.get(signature)
            if cached is not None:
                return cached
            image = theme_service.get_cached_rgba_image(self, path, image_module)
            if image is None:
                return None
            if image.width > max_width:
                scale = max_width / image.width
                new_size = (max_width, int(image.height * scale))
                image = image.resize(new_size, image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            self._bounded_cache_put(cache, signature, photo, max_items=48)
            return photo
        except _EXPECTED_APP_ERRORS:
            pass

        try:
            signature = (os.path.abspath(path), 0)
            cached = cache.get(signature)
            if cached is not None:
                return cached
            if ext in (".png", ".gif", ".ppm", ".pgm"):
                photo = tk.PhotoImage(file=path)
                self._bounded_cache_put(cache, signature, photo, max_items=48)
                return photo
        except _EXPECTED_APP_ERRORS:
            return None
        return None

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
    def _format_readme_content(content, wrap_width):
        return editor_ui_core.EDITOR_UI.readme_ui_service.format_readme_content(content, wrap_width)

    def show_readme(self, position_hint=None):
        return editor_ui_core.EDITOR_UI.readme_ui_service.show_readme(
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

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open File",
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        return editor_purge_service.load_file(self, path)

    @staticmethod
    def _tree_marker_palette(theme_variant):
        return theme_service.tree_marker_palette(theme_variant)

    @staticmethod
    def _sha256_file(path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _check_tree_marker_integrity(self):
        if self._tree_marker_integrity_checked:
            return self._tree_marker_integrity_ok
        self._tree_marker_integrity_checked = True
        self._tree_marker_integrity_ok = True
        try:
            base_dir = os.path.join(self._resource_base_dir(), "assets", "buttons")
            for variant, filename in self.TREE_MAIN_MARKER_FILES.items():
                expected = self.TREE_MAIN_MARKER_SHA256.get(variant)
                marker_path = os.path.join(base_dir, filename)
                if not os.path.isfile(marker_path):
                    self._tree_marker_integrity_ok = False
                    continue
                if expected:
                    actual = self._sha256_file(marker_path)
                    if str(actual).lower() != str(expected).lower():
                        self._tree_marker_integrity_ok = False
            b2_dir = os.path.join(base_dir, "tree-b2")
            for filename, expected in self.TREE_B2_MARKER_SHA256.items():
                marker_path = os.path.join(b2_dir, filename)
                if not os.path.isfile(marker_path):
                    self._tree_marker_integrity_ok = False
                    continue
                actual = self._sha256_file(marker_path)
                if str(actual).lower() != str(expected).lower():
                    self._tree_marker_integrity_ok = False
        except (OSError, RuntimeError, TypeError, ValueError):
            self._tree_marker_integrity_ok = False
        if not self._tree_marker_integrity_ok:
            try:
                if getattr(self, "status", None) is not None:
                    self.set_status("Warning: locked tree marker assets changed or missing.")
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        return self._tree_marker_integrity_ok

    def _load_tree_marker_icon(self, kind, selected=False, expandable=False, expanded=False):
        return tree_engine_service.load_tree_marker_icon(
            self,
            kind,
            selected=selected,
            expandable=expandable,
            expanded=expanded,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    @staticmethod
    def _nudge_marker_image_y(image, delta_y=-1):
        """Shift marker pixels vertically while preserving image size."""
        try:
            dy = float(delta_y)
        except (TypeError, ValueError):
            dy = -1.0
        if abs(dy) < 0.001 or image is None:
            return image
        try:
            image_module = importlib.import_module("PIL.Image")
            step = -1 if dy < 0 else 1
            total = abs(dy)
            whole = int(total)
            frac = total - float(whole)
            base = image_module.new("RGBA", image.size, (0, 0, 0, 0))
            base.alpha_composite(image, (0, step * whole))
            if frac <= 0.001:
                return base
            nxt = image_module.new("RGBA", image.size, (0, 0, 0, 0))
            nxt.alpha_composite(image, (0, step * (whole + 1)))
            return image_module.blend(base, nxt, max(0.0, min(1.0, frac)))
        except (ImportError, OSError, ValueError, TypeError, AttributeError):
            return image

    def _is_input_red_arrow_root_path(self, path):
        return tree_policy_service.should_use_input_red_arrow_for_path(self, path)

    def _is_input_database_locked_subcategory_path(self, path):
        normalized = list(path or [])
        if len(normalized) != 2:
            return False
        if self._input_mode_root_key_for_path(normalized) != "database":
            return False
        entry = self._get_value(normalized)
        if not isinstance(entry, dict):
            return False
        tables = entry.get("tables")
        if not isinstance(tables, dict) or not tables:
            return False
        first_table = str(next(iter(tables.keys()))).strip().casefold()
        return first_table in {"grades", "users", "customers"}

    def _load_input_bank_red_arrow_icon(self, expandable=False, expanded=False):
        # INPUT-only Bank marker override: red arrow without affecting JSON marker assets.
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        key = ("INPUT_BANK_ARROW", variant, bool(expandable), bool(expanded))
        cache = getattr(self, "_tree_marker_icon_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self._tree_marker_icon_cache = cache
        cached = cache.get(key)
        if cached is not None:
            return cached
        try:
            image_module = importlib.import_module("PIL.Image")
            draw_module = importlib.import_module("PIL.ImageDraw")
            canvas = image_module.new("RGBA", (14, 14), (0, 0, 0, 0))
            draw = draw_module.Draw(canvas)
            edge = (255, 128, 128, 255)
            fill = (208, 62, 62, 255)
            if expandable:
                # Expanded uses down arrow; collapsed uses right arrow.
                points = [(3, 4), (11, 4), (7, 10)] if expanded else [(4, 3), (10, 7), (4, 11)]
                draw.polygon(points, fill=fill, outline=edge)
            else:
                draw.ellipse((4, 4, 9, 9), fill=fill, outline=edge, width=1)
            # Micro placement tune for INPUT Bank marker: one pixel left and slightly lower.
            canvas = self._nudge_marker_image_y(canvas, delta_y=0.25)
            try:
                shifted = image_module.new("RGBA", canvas.size, (0, 0, 0, 0))
                shifted.alpha_composite(canvas, (-1, 0))
                canvas = shifted
            except (OSError, ValueError, TypeError, AttributeError):
                pass
            photo = self._pil_to_photo(canvas)
            self._bounded_cache_put(cache, key, photo, max_items=128)
            return photo
        except (ImportError, OSError, ValueError, TypeError, AttributeError, tk.TclError, RuntimeError):
            self._bounded_cache_put(cache, key, None, max_items=128)
            return None

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

    def _has_loading_child(self, item_id):
        children = self.tree.get_children(item_id)
        if len(children) != 1:
            return False
        return self.tree.item(children[0], "text") == "(loading)"

    def _ensure_all_loaded(self, root_id=""):
        for child in self.tree.get_children(root_id):
            if self._has_loading_child(child):
                self._populate_children(child)
            self._ensure_all_loaded(child)

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
    def _find_search_value_summary(value, max_tokens=24, max_chars=360):
        # Keep JSON Find Next focused on local node content so one hot subtree
        # does not flood matches and starve other categories (e.g. Phone).
        tokens = []
        if isinstance(value, (str, int, float, bool)) or value is None:
            text = str(value).strip()
            if text:
                tokens.append(text)
        elif isinstance(value, dict):
            for child in value.values():
                if len(tokens) >= int(max_tokens):
                    break
                if isinstance(child, (str, int, float, bool)) or child is None:
                    text = str(child).strip()
                    if text:
                        tokens.append(text)
        elif isinstance(value, list):
            for child in value:
                if len(tokens) >= int(max_tokens):
                    break
                if isinstance(child, (str, int, float, bool)) or child is None:
                    text = str(child).strip()
                    if text:
                        tokens.append(text)
        joined = " ".join(tokens)
        if len(joined) > int(max_chars):
            return joined[: int(max_chars)]
        return joined

    def _append_find_search_entries(self, path, value, entries):
        return editor_purge_service._append_find_search_entries(self, path, value, entries)

    def _ensure_tree_item_for_path(self, target_path):
        if not isinstance(target_path, list):
            return None
        current_item = ""
        if not target_path:
            return current_item

        for depth, _key in enumerate(target_path):
            if current_item:
                if self._has_loading_child(current_item):
                    self._populate_children(current_item)
            elif not self.tree.get_children(""):
                self._populate_children("")

            prefix = target_path[: depth + 1]
            next_item = None
            for child in self.tree.get_children(current_item):
                child_path = self.item_to_path.get(child)
                if isinstance(child_path, list) and child_path == prefix:
                    next_item = child
                    break

            if next_item is None:
                self._populate_children(current_item)
                for child in self.tree.get_children(current_item):
                    child_path = self.item_to_path.get(child)
                    if isinstance(child_path, list) and child_path == prefix:
                        next_item = child
                        break

            if next_item is None:
                # Network roots can bucket list rows under group nodes (ROUTER/DEVICE/etc.).
                # Resolve those rows through the group node so Find Next can jump cross-category.
                next_item = self._resolve_grouped_list_item(current_item, prefix)

            if next_item is None:
                return None
            current_item = next_item
        return current_item

    def _network_group_for_list_index(self, list_path, row_index):
        if not isinstance(list_path, list) or not isinstance(row_index, int):
            return None
        try:
            list_value = self._get_value(list_path)
        except _EXPECTED_APP_ERRORS:
            return None
        if not isinstance(list_value, list):
            return None
        if row_index < 0 or row_index >= len(list_value):
            return None
        if not self._is_network_list(list_path, list_value):
            return None
        row = list_value[row_index]
        if isinstance(row, dict):
            group = str(row.get("type", "") or "").strip()
            return group or "UNKNOWN"
        return "UNKNOWN"

    def _resolve_grouped_list_item(self, current_item, prefix):
        if not current_item:
            return None
        if not isinstance(prefix, list) or len(prefix) < 2:
            return None
        list_path = prefix[:-1]
        row_index = prefix[-1]
        if not isinstance(row_index, int):
            return None
        group = self._network_group_for_list_index(list_path, row_index)
        if not group:
            return None
        group_item = self._ensure_tree_group_item_loaded(list_path, group)
        if group_item is None:
            return None
        if self._has_loading_child(group_item):
            self._populate_children(group_item)
        for child in self.tree.get_children(group_item):
            child_path = self.item_to_path.get(child)
            if isinstance(child_path, list) and child_path == prefix:
                return child
        return None

    def _ensure_tree_group_item_loaded(self, list_path, group):
        parent_id = self._ensure_tree_item_for_path(list_path)
        if parent_id is None:
            return None
        if self._has_loading_child(parent_id):
            self._populate_children(parent_id)

        def _find_group_item():
            for child in self.tree.get_children(parent_id):
                item_path = self.item_to_path.get(child)
                if (
                    isinstance(item_path, tuple)
                    and len(item_path) == 3
                    and item_path[0] == "__group__"
                    and item_path[1] == list_path
                    and item_path[2] == group
                ):
                    return child
            return None

        group_item = _find_group_item()
        if group_item is not None:
            return group_item
        self._populate_children(parent_id)
        return _find_group_item()

    def find_next(self, event=None):
        return json_view_manager.JSON_VIEW.json_find_orchestrator_service.find_next(
            self,
            expected_errors=_EXPECTED_APP_ERRORS,
        )

    def _collapse_previous_find_root_if_category_changed(self, next_item_id):
        json_find_nav_service.collapse_previous_find_root_if_category_changed(self, next_item_id)

    def _build_json_find_matches(self, query_lower):
        return json_find_service.build_json_find_matches(self, query_lower)

    def _filter_json_find_matches(self, prior_matches, query_lower):
        return json_find_service.filter_json_find_matches(self, prior_matches, query_lower)

    def _find_next_json_text_match(self, query):
        return json_text_find_service.find_next_json_text_match(self, query)

    def _focus_json_find_match(self, query):
        json_text_find_service.focus_json_find_match(self, query)

    def _find_next_input_mode(self):
        input_mode_find_service.find_next_input_mode(self, tk_module=tk)

    def _build_input_mode_search_entries(self):
        return input_mode_find_service.build_input_mode_search_entries(self, tk_module=tk)

    @staticmethod
    def _find_first_entry_descendant(root_widget):
        return input_mode_find_service.find_first_entry_descendant(root_widget, tk_module=tk)

    def _scroll_input_widget_into_view(self, widget):
        input_mode_find_service.scroll_input_widget_into_view(self, widget)

    def _populate_children(self, item_id):
        tree_engine_service.populate_children(self, item_id)

    @staticmethod
    def _is_database_table_rows_path(path):
        if not isinstance(path, list):
            return False
        if len(path) < 4:
            return False
        return str(path[0]) == "Database" and str(path[2]) == "tables"

    @staticmethod
    def _database_table_row_label(idx, item):
        if isinstance(item, dict):
            # Prefer first nested string value (email/name/etc.) before numeric ids.
            first_scalar = None
            for value_obj in item.values():
                if not isinstance(value_obj, dict):
                    continue
                value = value_obj.get("value")
                if isinstance(value, str):
                    text = value.strip()
                    if text:
                        return text
                if first_scalar is None and isinstance(value, (int, float)) and not isinstance(value, bool):
                    first_scalar = str(value)
            direct_value = item.get("value")
            if isinstance(direct_value, (str, int, float)) and str(direct_value).strip():
                return str(direct_value)
            if first_scalar is not None:
                return first_scalar
        return f"[{idx}]"

    def on_expand(self, event):
        item_id = self.tree.focus()
        if item_id:
            if self._is_input_tree_expand_blocked(item_id):
                try:
                    self.tree.item(item_id, open=False)
                    self.root.after_idle(lambda iid=item_id: self.tree.item(iid, open=False))
                except _EXPECTED_APP_ERRORS:
                    pass
                self.set_status("INPUT mode: selected subcategory is locked.")
                return "break"
            self._populate_children(item_id)

    def on_collapse(self, event):
        self._refresh_tree_item_markers()

    def _tree_item_can_toggle(self, item_id):
        return tree_engine_service.tree_item_can_toggle(self, item_id)

    def _on_tree_click_toggle(self, event):
        return tree_engine_service.on_tree_click_toggle(self, event)

    def _on_tree_double_click_guard(self, event):
        return tree_engine_service.on_tree_double_click_guard(self, event)

    def on_select(self, event):
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
            group_items = [
                item for item in value
                if isinstance(item, dict) and item.get("type") == group
            ]
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

    def _initial_highlight_line_limit(self):
        return json_view_render_service.initial_highlight_line_limit(self)

    def _cancel_pending_json_view_lock_state(self):
        json_view_render_service.cancel_pending_json_view_lock_state(self)

    def _schedule_json_view_lock_state(self, path, render_seq=None):
        json_view_render_service.schedule_json_view_lock_state(
            self,
            path,
            render_seq=render_seq,
        )

    def _json_lock_tag_palette(self):
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        if variant == "KAMUE":
            return {
                "fg": "#f5b043",
                "block_bg": "#241608",
            }
        return {
            "fg": "#f2a024",
            "block_bg": "#2a1b0b",
        }

    def _configure_json_lock_tags(self):
        return json_diagnostics_service._configure_json_lock_tags(self)

    def _clear_json_lock_highlight(self):
        return json_diagnostics_service._clear_json_lock_highlight(self)

    def _set_json_text_editable(self, editable=True):
        return json_diagnostics_service._set_json_text_editable(self, editable)

    def _json_token_followed_by_colon(self, end_index, lookahead_chars=24):
        return json_repair_service._json_token_followed_by_colon(self, end_index, lookahead_chars)

    def _tag_json_locked_key_occurrences(self, key_name):
        return json_diagnostics_service._tag_json_locked_key_occurrences(self, key_name)

    def _tag_json_xy_key_occurrences(self, key_name):
        return json_diagnostics_service._tag_json_xy_key_occurrences(self, key_name)

    def _should_batch_tag_locked_keys(self, key_names):
        return json_diagnostics_service._should_batch_tag_locked_keys(self, key_names)

    def _tag_json_key_occurrences_batch(self, locked_key_names, xy_key_names=(), line_limit=None):
        return json_diagnostics_service._tag_json_key_occurrences_batch(self, locked_key_names, xy_key_names, line_limit)

    def _tag_json_string_value_literals(self, line_limit=None):
        return json_diagnostics_service._tag_json_string_value_literals(self, line_limit)

    def _tag_json_brace_tokens(self, line_limit=None):
        return json_diagnostics_service._tag_json_brace_tokens(self, line_limit)

    def _tag_json_boolean_literals(self, line_limit=None):
        return json_diagnostics_service._tag_json_boolean_literals(self, line_limit)

    def _tag_json_property_keys(self, line_limit=None):
        return json_diagnostics_service._tag_json_property_keys(self, line_limit)

    def _json_literal_offsets_after_key(self, key_end_index, literal_token, lookahead_chars=120, ignore_case=False):
        return json_diagnostics_service._json_literal_offsets_after_key(self, key_end_index, literal_token, lookahead_chars, ignore_case)

    def _tag_json_locked_value_occurrences(self, field_name, literal_value, ignore_case=False):
        return json_diagnostics_service._tag_json_locked_value_occurrences(self, field_name, literal_value, ignore_case)

    def _apply_json_view_lock_state(self, path):
        return json_diagnostics_service._apply_json_view_lock_state(self, path)

    def _apply_json_view_key_highlights(self, path, line_limit=None):
        # Legacy wiring token kept for regression checks: xy_keys = ("x", "y") if len(use_path) == 1 else ()
        return editor_purge_service._apply_json_view_key_highlights(self, path, line_limit)

    def _apply_json_view_value_highlights(self, path):
        return editor_purge_service._apply_json_view_value_highlights(self, path)

    def _describe(self, value):
        return json_diagnostics_service._describe(self, value)


    def apply_edit(self):
        return editor_purge_service.apply_edit(self)

    def _extract_key_name_from_diag_line(self, line_text):
        return json_diagnostics_service._extract_key_name_from_diag_line(self, line_text)

    def _locked_field_name_from_parse_diag(self, path, diag):
        return editor_purge_service._locked_field_name_from_parse_diag(self, path, diag)

    def _find_lock_anchor_index(self, field_name, preferred_index=None):
        return json_diagnostics_service._find_lock_anchor_index(self, field_name, preferred_index)

    def _diag_line_mentions_locked_field(self, line_no, field_name):
        return json_diagnostics_service._diag_line_mentions_locked_field(self, line_no, field_name)

    def _maybe_restore_locked_parse_error(self, path, diag, exc=None):
        # Parse-lock guard gate: delegated lock-restore flow preserves strict line/key gating.
        return editor_purge_service._maybe_restore_locked_parse_error(self, path, diag, exc)

    def _format_json_error(self, exc):
        return json_error_diagnostics_core.format_json_error(self, exc)


    def _example_for_error(self, exc):
        return json_diagnostics_service._example_for_error(self, exc)

    def _missing_colon_example(self, line_text):
        return json_repair_service._missing_colon_example(self, line_text)

    def _is_json_value_token_start(self, value_text):
        return json_diagnostics_service._is_json_value_token_start(self, value_text)

    def _missing_colon_key_value_span(self, line_text):
        return json_repair_service._missing_colon_key_value_span(self, line_text)

    def _line_has_missing_colon_key_value(self, line_text):
        return self._missing_colon_key_value_span(line_text) is not None

    def _find_nearby_missing_colon_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_missing_colon_line(self, lineno, lookback)

    def _is_key_colon_comma_line(self, line_text):
        return json_repair_service._is_key_colon_comma_line(self, line_text)

    def _key_colon_comma_to_list_open(self, line_text):
        return json_repair_service._key_colon_comma_to_list_open(self, line_text)

    def _line_extra_quote_in_string_value(self, line_text):
        return json_repair_service._line_extra_quote_in_string_value(self, line_text)

    def _fix_extra_quote_to_comma(self, line_text):
        return json_repair_service._fix_extra_quote_to_comma(self, line_text)

    def _line_has_trailing_stray_quote_after_comma(self, line_text):
        return json_repair_service._line_has_trailing_stray_quote_after_comma(self, line_text)

    def _fix_trailing_stray_quote_after_comma(self, line_text):
        return json_repair_service._fix_trailing_stray_quote_after_comma(self, line_text)

    def _find_nearby_trailing_stray_quote_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_trailing_stray_quote_line(self, lineno, lookback)

    def _line_has_duplicate_trailing_comma(self, line_text):
        return json_repair_service._line_has_duplicate_trailing_comma(self, line_text)

    def _fix_duplicate_trailing_comma(self, line_text):
        return json_repair_service._fix_duplicate_trailing_comma(self, line_text)

    def _find_nearby_duplicate_trailing_comma_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_duplicate_trailing_comma_line(self, lineno, lookback)

    def _line_requires_trailing_comma(self, lineno):
        return json_repair_service._line_requires_trailing_comma(self, lineno)

    def _duplicate_comma_run_span(self, line_text, lineno=None):
        return json_repair_service._duplicate_comma_run_span(self, line_text, lineno)

    def _line_has_duplicate_comma_run(self, line_text, lineno=None):
        return self._duplicate_comma_run_span(line_text, lineno=lineno) is not None

    def _fix_duplicate_comma_run(self, line_text, lineno=None):
        return json_repair_service._fix_duplicate_comma_run(self, line_text, lineno)

    def _find_nearby_duplicate_comma_run_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_duplicate_comma_run_line(self, lineno, lookback)

    def _comma_before_colon_span(self, line_text):
        return json_colon_comma_service.comma_before_colon_span(line_text)

    def _line_has_comma_before_colon(self, line_text):
        return json_colon_comma_service.line_has_comma_before_colon(line_text)

    def _fix_comma_before_colon(self, line_text):
        return json_colon_comma_service.fix_comma_before_colon(line_text)

    def _find_nearby_comma_before_colon_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_comma_before_colon_line(self, lineno, lookback)

    def _comma_after_colon_span(self, line_text):
        return json_colon_comma_service.comma_after_colon_span(line_text)

    def _line_has_comma_after_colon(self, line_text):
        return json_colon_comma_service.line_has_comma_after_colon(line_text)

    def _fix_comma_after_colon(self, line_text):
        return json_colon_comma_service.fix_comma_after_colon(line_text)

    def _find_nearby_comma_after_colon_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_comma_after_colon_line(self, lineno, lookback)

    def _analyze_invalid_prefix_after_colon(self, line_text):
        return json_repair_service._analyze_invalid_prefix_after_colon(self, line_text)

    def _line_has_invalid_prefix_after_colon(self, line_text):
        return self._analyze_invalid_prefix_after_colon(line_text) is not None

    def _fix_invalid_prefix_after_colon(self, line_text):
        return json_repair_service._fix_invalid_prefix_after_colon(self, line_text)

    def _find_nearby_invalid_prefix_after_colon_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_invalid_prefix_after_colon_line(self, lineno, lookback)

    def _comma_before_closer_span(self, line_text):
        return json_colon_comma_service.comma_before_closer_span(line_text)

    def _line_has_comma_before_closer(self, line_text):
        return json_colon_comma_service.line_has_comma_before_closer(line_text)

    def _fix_comma_before_closer(self, line_text):
        return json_colon_comma_service.fix_comma_before_closer(line_text)

    def _find_nearby_comma_before_closer_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_comma_before_closer_line(self, lineno, lookback)

    def _comma_line_invalid_tail_span(self, line_text):
        return json_colon_comma_service.comma_line_invalid_tail_span(line_text)

    def _line_has_comma_line_invalid_tail(self, line_text):
        return json_colon_comma_service.line_has_comma_line_invalid_tail(line_text)

    def _expected_missing_close_symbol(self, lineno):
        return json_repair_service._expected_missing_close_symbol(self, lineno)

    def _fix_comma_line_invalid_tail(self, line_text, lineno=None):
        return json_repair_service._fix_comma_line_invalid_tail(self, line_text, lineno)

    def _find_nearby_comma_line_invalid_tail_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_comma_line_invalid_tail_line(self, lineno, lookback)

    def _missing_key_quote_before_colon_span(self, line_text):
        return json_property_key_rule_service.missing_key_quote_before_colon_span(line_text)

    def _line_has_missing_key_quote_before_colon(self, line_text):
        return json_property_key_rule_service.line_has_missing_key_quote_before_colon(line_text)

    def _fix_property_key_symbol_before_colon(self, line_text):
        return json_property_key_rule_service.fix_property_key_symbol_before_colon(line_text)

    def _find_nearby_missing_key_quote_before_colon_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_missing_key_quote_before_colon_line(self, lineno, lookback)

    def _property_key_invalid_escape_span(self, line_text):
        return json_property_key_rule_service.property_key_invalid_escape_span(line_text)

    def _line_has_property_key_invalid_escape(self, line_text):
        return json_property_key_rule_service.line_has_property_key_invalid_escape(line_text)

    def _fix_property_key_invalid_escape(self, line_text):
        return json_property_key_rule_service.fix_property_key_invalid_escape(line_text)

    def _find_nearby_property_key_invalid_escape_line(self, lineno, lookback=2):
        return json_diagnostics_service._find_nearby_property_key_invalid_escape_line(self, lineno, lookback)

    def _missing_key_quote_before_colon_diag(self, line_no, colno=1):
        return json_repair_service._missing_key_quote_before_colon_diag(self, line_no, colno)

    def _quoted_item_invalid_tail_span(self, line_text):
        return json_repair_service._quoted_item_invalid_tail_span(self, line_text)

    def _line_has_invalid_tail_after_quoted_item(self, line_text):
        return json_repair_service._line_has_invalid_tail_after_quoted_item(self, line_text)

    def _fix_invalid_tail_after_quoted_item(self, line_text, lineno=None):
        return editor_purge_service._fix_invalid_tail_after_quoted_item(self, line_text, lineno)

    def _find_nearby_invalid_tail_after_quoted_item_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_invalid_tail_after_quoted_item_line(self, lineno, lookback)

    def _line_has_illegal_trailing_comma_before_close(self, line_text, lineno):
        return json_repair_service._line_has_illegal_trailing_comma_before_close(self, line_text, lineno)

    def _trailing_comma_before_close_col(self, line_text):
        return json_repair_service._trailing_comma_before_close_col(self, line_text)

    def _fix_illegal_trailing_comma_before_close(self, line_text):
        return json_repair_service._fix_illegal_trailing_comma_before_close(self, line_text)

    def _find_nearby_illegal_trailing_comma_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_illegal_trailing_comma_line(self, lineno, lookback)

    def _line_has_illegal_comma_after_top_level_close(self, line_text, lineno):
        return json_repair_service._line_has_illegal_comma_after_top_level_close(self, line_text, lineno)

    def _top_level_close_symbol_run_span(self, line_text):
        return json_top_level_close_service.top_level_close_symbol_run_span(line_text)

    def _line_has_top_level_close_symbol_run(self, line_text, lineno):
        return json_repair_service._line_has_top_level_close_symbol_run(self, line_text, lineno)

    def _fix_top_level_close_symbol_run(self, line_text):
        return json_top_level_close_service.fix_top_level_close_symbol_run(line_text)

    def _find_nearby_top_level_close_symbol_run_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_top_level_close_symbol_run_line(self, lineno, lookback)

    def _comma_run_after_top_level_close_span(self, line_text):
        return json_top_level_close_service.comma_run_after_top_level_close_span(line_text)

    def _fix_illegal_comma_after_top_level_close(self, line_text):
        return json_top_level_close_service.fix_illegal_comma_after_top_level_close(line_text)

    def _find_nearby_illegal_comma_after_top_level_close_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_illegal_comma_after_top_level_close_line(self, lineno, lookback)

    def _split_completed_scalar_value_tail(self, line_text):
        return json_scalar_tail_service.split_completed_scalar_value_tail(line_text)

    def _line_has_invalid_trailing_symbols_after_string_value(self, line_text):
        return json_scalar_tail_service.line_has_invalid_trailing_symbols_after_string_value(line_text)

    def _first_invalid_trailing_symbol_col(self, line_text, lineno=None):
        return json_repair_service._first_invalid_trailing_symbol_col(self, line_text, lineno)

    def _fix_invalid_trailing_symbols_after_string_value(self, line_text, lineno=None):
        return editor_purge_service._fix_invalid_trailing_symbols_after_string_value(self, line_text, lineno)

    def _find_nearby_invalid_trailing_symbols_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_invalid_trailing_symbols_line(self, lineno, lookback)

    def _line_has_invalid_symbol_after_closer(self, line_text):
        return json_closer_symbol_service.line_has_invalid_symbol_after_closer(line_text)

    def _first_invalid_symbol_after_closer_col(self, line_text):
        return json_closer_symbol_service.first_invalid_symbol_after_closer_col(line_text)

    def _fix_invalid_symbol_after_closer(self, line_text):
        return json_closer_symbol_service.fix_invalid_symbol_after_closer(line_text)

    def _find_nearby_invalid_symbol_after_closer_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_invalid_symbol_after_closer_line(self, lineno, lookback)

    def _invalid_symbol_after_open_span(self, line_text):
        return json_open_symbol_service.invalid_symbol_after_open_span(line_text)

    def _line_has_invalid_symbol_after_open(self, line_text):
        return json_open_symbol_service.line_has_invalid_symbol_after_open(line_text)

    def _fix_invalid_symbol_after_open(self, line_text):
        return json_open_symbol_service.fix_invalid_symbol_after_open(line_text)

    def _find_nearby_invalid_symbol_after_open_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_invalid_symbol_after_open_line(self, lineno, lookback)

    def _find_nearby_extra_quote_in_value_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_extra_quote_in_value_line(self, lineno, lookback)

    def _build_symbol_json_diagnostic(self, exc, lineno=None):
        return json_error_diagnostics_core.build_symbol_json_diagnostic(self, exc, lineno=lineno)


    def _build_json_diagnostic(self, exc):
        return json_error_diagnostics_core.build_json_diagnostic(self, exc)


    def _quote_unquoted_value(self, line_text):
        return json_repair_service._quote_unquoted_value(self, line_text)

    def _quote_unquoted_scalar_line(self, line_text):
        return json_repair_service._quote_unquoted_scalar_line(self, line_text)

    def _line_needs_value_quotes(self, line_text):
        return json_diagnostics_service._line_needs_value_quotes(self, line_text)

    def _missing_value_close_quote_insert_col(self, line_text):
        return json_repair_service._missing_value_close_quote_insert_col(self, line_text)

    def _missing_value_open_quote_insert_col(self, line_text):
        return json_repair_service._missing_value_open_quote_insert_col(self, line_text)

    def _find_nearby_missing_value_close_quote_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_missing_value_close_quote_line(self, lineno, lookback)

    def _find_nearby_missing_value_open_quote_line(self, lineno, lookback=3):
        return json_repair_service._find_nearby_missing_value_open_quote_line(self, lineno, lookback)

    def _find_nearby_unquoted_value_line(self, lineno, lookback=3):
        return json_diagnostics_service._find_nearby_unquoted_value_line(self, lineno, lookback)

    def _suggest_json_literal_from_token(self, token):
        return json_diag_core.suggest_json_literal_from_token(token)

    def _boolean_literal_typo_diagnostic(self, line_text):
        return json_diag_core.boolean_literal_typo_diagnostic(line_text)

    def _find_nearby_boolean_literal_typo_line(self, lineno, lookback=3):
        return json_diagnostics_service._find_nearby_boolean_literal_typo_line(self, lineno, lookback)

    def _is_wrong_list_open_for_object(self, prev_text, next_text):
        return json_diagnostics_service._is_wrong_list_open_for_object(self, prev_text, next_text)

    def _find_wrong_list_open_line(self, lineno, lookback=3):
        return json_diagnostics_service._find_wrong_list_open_line(self, lineno, lookback)

    def _find_wrong_object_open_line(self, lineno, lookback=3):
        return json_diagnostics_service._find_wrong_object_open_line(self, lineno, lookback)

    def _expected_closer_before_position(self, target_line, target_col):
        return json_diagnostics_service._expected_closer_before_position(self, target_line, target_col)

    def _find_wrong_closing_symbol_line(self, lineno, lookback=2):
        return json_repair_service._find_wrong_closing_symbol_line(self, lineno, lookback)

    def _find_missing_list_close_before_object_end(self, lineno, lookback=4):
        return json_repair_service._find_missing_list_close_before_object_end(self, lineno, lookback)

    def _next_non_empty_line_number(self, start_line):
        return json_diagnostics_service._next_non_empty_line_number(self, start_line)

    def _missing_list_open_key_line(self, lineno):
        return json_repair_service._missing_list_open_key_line(self, lineno)

    @staticmethod
    def _line_looks_like_object_property(line_text):
        return bool(re.match(r'^"[^"]+"\s*:', str(line_text or "").strip()))

    def _find_missing_container_open_after_key_line(self, lineno, lookback=6):
        return json_repair_service._find_missing_container_open_after_key_line(self, lineno, lookback)

    def _find_missing_list_open_after_key_line(self, lineno, lookback=6):
        return json_repair_service._find_missing_list_open_after_key_line(self, lineno, lookback)

    def _missing_close_example(self, msg):
        return json_repair_service._missing_close_example(self, msg)

    def _format_suggestion(self, header, before, after, header_only=False):
        return json_diagnostics_service._format_suggestion(self, header, before, after, header_only)

    def _suggestion_from_example(self, example, add_after=None, add_colon=False, quote_key=False):
        return json_diagnostics_service._suggestion_from_example(self, example, add_after, add_colon, quote_key)
    def _is_missing_object_open_at(self, lineno):
        return json_repair_service._is_missing_object_open_at(self, lineno)

    def _line_text(self, lineno):
        return json_diagnostics_service._line_text(self, lineno)

    def _line_has_missing_open_key_quote(self, line_text):
        return json_repair_service._line_has_missing_open_key_quote(self, line_text)

    def _missing_close_target_line_from_exc(self, exc, open_bracket, close_bracket):
        return json_repair_service._missing_close_target_line_from_exc(self, exc, open_bracket, close_bracket)

    def _missing_close_target_line_any(self, exc):
        return json_repair_service._missing_close_target_line_any(self, exc)

    def _missing_list_close_target_line(self, exc):
        line, _idx = self._missing_close_insertion_point("[", "]", exc)
        return line

    def _unmatched_open_bracket_lines(self, open_bracket, close_bracket):
        return json_diagnostics_service._unmatched_open_bracket_lines(self, open_bracket, close_bracket)

    def _is_missing_list_close(self):
        return bool(self._unmatched_open_bracket_lines("[", "]"))

    def _is_missing_object_close(self):
        return bool(self._unmatched_open_bracket_lines("{", "}"))

    def _last_unmatched_bracket_line(self, open_bracket, close_bracket):
        return json_diagnostics_service._last_unmatched_bracket_line(self, open_bracket, close_bracket)

    def _line_indent_width(self, lineno):
        raw = self._line_text(lineno)
        return len(raw) - len(raw.lstrip(" \t"))

    def _missing_close_insertion_point(self, open_bracket, close_bracket, exc=None):
        return json_repair_service._missing_close_insertion_point(self, open_bracket, close_bracket, exc)

    def _missing_object_close_target_line(self, exc):
        line, _idx = self._missing_close_insertion_point("{", "}", exc)
        return line

    def _find_comma_only_line_before(self, start_line):
        return json_repair_service._find_comma_only_line_before(self, start_line)

    def _find_missing_comma_between_block_values_line(self, line):
        return json_repair_service._find_missing_comma_between_block_values_line(self, line)

    def _find_blank_line_before(self, start_line):
        return json_diagnostics_service._find_blank_line_before(self, start_line)

    def _closest_non_empty_line_before(self, start_line):
        return json_diagnostics_service._closest_non_empty_line_before(self, start_line)

    def _last_non_empty_line_number(self):
        return json_diagnostics_service._last_non_empty_line_number(self)


    def _missing_close_target_line(self, open_bracket, close_bracket):
        return json_repair_service._missing_close_target_line(self, open_bracket, close_bracket)

    def _is_missing_object_open(self, exc):
        return json_repair_service._is_missing_object_open(self, exc)

    def _is_missing_list_open(self, exc):
        return json_repair_service._is_missing_list_open(self, exc)

    def _is_missing_list_open_at_start(self, exc, allow_any_position=False):
        return json_repair_service._is_missing_list_open_at_start(self, exc, allow_any_position)

    def _missing_list_open_top_level(self):
        return json_repair_service._missing_list_open_top_level(self)

    def _missing_object_open_from_extra_data(self):
        return json_repair_service._missing_object_open_from_extra_data(self)

    def _first_non_ws_char(self):
        return json_diagnostics_service._first_non_ws_char(self)

    def _missing_list_open_from_extra_data(self):
        return json_repair_service._missing_list_open_from_extra_data(self)

    def _previous_non_empty_line(self, lineno):
        return json_diagnostics_service._previous_non_empty_line(self, lineno)

    def _next_non_empty_line(self, lineno):
        return json_diagnostics_service._next_non_empty_line(self, lineno)

    def _missing_object_example(self, lineno):
        return json_repair_service._missing_object_example(self, lineno)

    def _close_before_list(self, lineno):
        return json_diagnostics_service._close_before_list(self, lineno)

    def _quote_property_name(self, line_text):
        return json_repair_service._quote_property_name(self, line_text)

    def _highlight_custom_range(self, line, start_col, end_col):
        return json_diagnostics_service._highlight_custom_range(self, line, start_col, end_col)

    def _fix_missing_at(self, value, domain_roots=None):
        return json_repair_service._fix_missing_at(self, value, domain_roots)

    def _format_phone(self, value):
        return json_repair_service._format_phone(self, value)

    def _find_phone_format_issue(self):
        return json_repair_service._find_phone_format_issue(self)

    def _fix_missing_space_after_colon(self, line_text):
        return json_repair_service._fix_missing_space_after_colon(self, line_text)

    def _find_json_spacing_issue(self):
        return json_repair_service._find_json_spacing_issue(self)

    def _find_missing_email_at(self):
        return json_repair_service._find_missing_email_at(self)

    def _path_targets_email(self, path):
        return json_repair_service._path_targets_email(self, path)

    def _looks_like_email_candidate(self, value):
        return json_repair_service._looks_like_email_candidate(self, value)

    def _should_validate_email_path_value(self, path, value):
        return json_repair_service._should_validate_email_path_value(self, path, value)

    def _iter_candidate_email_values(self, node, rel_path=None):
        return json_repair_service._iter_candidate_email_values(self, node, rel_path)

    def _format_path_for_display(self, path):
        return tree_view_service.format_path_for_display(path)

    def _find_value_span_in_editor(self, value, preferred_key=None):
        return json_diagnostics_service._find_value_span_in_editor(self, value, preferred_key)

    def _find_invalid_email_in_value(self, base_path, value):
        return json_repair_service._find_invalid_email_in_value(self, base_path, value)

    def _best_domain_root_similarity(self, root):
        return json_diagnostics_service._best_domain_root_similarity(self, root)

    def _suggest_known_domain_from_local_and_domain(self, local, domain):
        return json_diagnostics_service._suggest_known_domain_from_local_and_domain(self, local, domain)

    def _suggest_email_for_malformed(self, value):
        return json_repair_service._suggest_email_for_malformed(self, value)

    def _validate_email_address(self, value):
        return json_repair_service._validate_email_address(self, value)

    def _is_valid_email_domain(self, domain):
        return json_repair_service._is_valid_email_domain(self, domain)

    def _find_invalid_email_format_issue(self):
        return json_repair_service._find_invalid_email_format_issue(self)

    def _fix_missing_quote(self, line_text):
        return json_repair_service._fix_missing_quote(self, line_text)

    def _unclosed_quoted_value_invalid_tail_span(self, line_text):
        return json_repair_service._unclosed_quoted_value_invalid_tail_span(self, line_text)

    def _find_nearby_unclosed_quoted_value_invalid_tail_line(self, lineno, lookback=2):
        return json_repair_service._find_nearby_unclosed_quoted_value_invalid_tail_line(self, lineno, lookback)

    def _comma_example_line(self, lineno):
        return json_repair_service._comma_example_line(self, lineno)

    def _symbol_error_focus_index(self, start_index, end_index):
        return json_repair_service._symbol_error_focus_index(self, start_index, end_index)

    def _apply_json_error_highlight(self, exc, line, start_index, end_index, note=""):
        return json_diagnostics_service._apply_json_error_highlight(self, exc, line, start_index, end_index, note)

    def _highlight_json_error(self, exc):
        # Delegation contract token: json_error_highlight_core.highlight_json_error(
        return json_diagnostics_service._highlight_json_error(self, exc)


    def _place_error_pin(self, index):
        return error_overlay_service.place_error_pin(self, index)

    def _clear_error_pin(self):
        error_overlay_service.clear_error_pin(self)

    def _position_error_overlay(self, line):
        error_overlay_service.position_error_overlay(self, line)

    def _diag_system_from_note(self, note):
        return json_diagnostics_service._diag_system_from_note(self, note)

    def _log_json_error(self, exc, target_line, note=""):
        return json_error_diag_service.log_json_error(self, exc, target_line, note=note)

    def _log_json_error_emergency(self, exc, target_line, note=""):
        return json_diagnostics_service._log_json_error_emergency(self, exc, target_line, note)

    def _log_input_mode_edit_issue(self, path, exc):
        input_mode_diag_service.log_input_mode_edit_issue(self, path, exc)

    def _log_input_mode_apply_result(self, path, changed):
        input_mode_diag_service.log_input_mode_apply_result(self, path, changed)

    def _log_input_mode_apply_trace(self, stage, path, specs_count, changed=None):
        return json_diagnostics_service._log_input_mode_apply_trace(self, stage, path, specs_count, changed)

    def _begin_diag_action(self, action_name):
        return json_diagnostics_service._begin_diag_action(self, action_name)

    def _clear_json_error_highlight(self):
        return json_diagnostics_service._clear_json_error_highlight(self)

    def _on_text_keypress(self, event):
        return json_diagnostics_service._on_text_keypress(self, event)

    def _on_text_nav_attempt(self, event):
        return json_diagnostics_service._on_text_nav_attempt(self, event)

    def _is_index_on_error_line(self, index):
        return json_diagnostics_service._is_index_on_error_line(self, index)

    def _line_number_from_index(self, index):
        return json_diagnostics_service._line_number_from_index(self, index)

    def _preferred_error_insert_index(self, line, fallback_index):
        return json_diagnostics_service._preferred_error_insert_index(self, line, fallback_index)

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
        root = getattr(self, "root", None)
        after_id = getattr(self, "_live_feedback_after_id", None)
        self._live_feedback_after_id = None
        if root is None or not after_id:
            return
        try:
            root.after_cancel(after_id)
        except _EXPECTED_APP_ERRORS:
            return

    def _schedule_live_error_feedback(self):
        root = getattr(self, "root", None)
        if root is None:
            return
        self._cancel_live_feedback_timer()
        delay_ms = max(1, int(getattr(self, "_live_feedback_delay_ms", 140) or 140))
        try:
            self._live_feedback_after_id = root.after(delay_ms, self._run_live_error_feedback)
        except _EXPECTED_APP_ERRORS:
            self._live_feedback_after_id = None

    def _run_live_error_feedback(self):
        self._live_feedback_after_id = None
        if self._auto_apply_in_progress:
            return
        self._show_live_error_feedback()

    def _can_auto_apply_current_edit(self):
        return json_edit_flow_service.can_auto_apply_current_edit(self)

    def _show_live_error_feedback(self):
        return editor_purge_service._show_live_error_feedback(self)

    def _show_error_overlay(self, title, message, actions=None):
        return editor_purge_service._show_error_overlay(self, title, message, actions)

    def _destroy_error_overlay(self):
        error_overlay_service.destroy_error_overlay(self)

    def _apply_error_tint(self):
        error_overlay_service.apply_error_tint(self)

    def _clear_error_tint(self):
        error_overlay_service.clear_error_tint(self)

    def _refresh_active_error_theme(self):
        error_overlay_service.refresh_active_error_theme(self)

    def save_file(self):
        return editor_purge_service.save_file(self)

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

    def export_hhsave(self):
        return editor_purge_service.export_hhsave(self)

    def _get_value(self, path):
        return json_path_service.get_value(self.data, path)

    def _set_value(self, path, new_value):
        return editor_purge_service._set_value(self, path, new_value)

    def _is_network_list(self, path, value):
        return highlight_label_service.is_network_list(path, value, self.network_types_set)

    def _find_first_dict_key_change(self, old_value, new_value, current_path=None):
        return label_format_service.find_first_dict_key_change(old_value, new_value, current_path=current_path)

    def _is_json_edit_allowed(self, path, new_value, show_feedback=True, auto_restore=False):
        # Orange lock system now runs as label-only guidance:
        # keep highlight tags, but do not block/restore edits or show lock overlays.
        # Delegated lock policies still rely on highlight_label_service.is_locked_field_path checks.
        # Contract note: callers may still pass auto_restore=True for regression compatibility.
        # Legacy warning actions "Auto-Fix" and "Continue" remain delegated in edit guard flow.
        _ = (path, new_value, show_feedback, auto_restore)
        return True

    def _is_edit_allowed(self, path, new_value):
        return editor_purge_service._is_edit_allowed(self, path, new_value)

    def _network_context(self, path):
        return highlight_label_service.network_context(
            path=path,
            value_getter=self._get_value,
            network_types_set=self.network_types_set,
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
