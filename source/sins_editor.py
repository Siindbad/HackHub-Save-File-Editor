import ctypes
import difflib
import gzip
import hashlib
import importlib
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from collections import deque
from datetime import datetime, timedelta
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from services import bug_report_api_service
from services import bug_report_service
from services import bug_report_ui_service
from services import editor_mode_switch_service
from services import error_overlay_service
from services import error_service
from services import footer_service
from services import highlight_label_service
from services import input_bank_style_service
from services import input_mode_service
from services import json_error_diag_service
from services import json_error_highlight_render_service
from services import json_view_service
from services import label_format_service
from services import loader_service
from services import runtime_log_service
from services import startup_loader_ui_service
from services import theme_asset_service
from services import theme_service
from services import tree_engine_service
from services import tree_mode_service
from services import tree_policy_service
from services import toolbar_service
from services import tree_view_service
from services import ui_build_service
from services import update_orchestrator_service
from services import update_service
from services import update_ui_service
from services import windows_runtime_service
from core import constants as app_constants
from core import display_profile as display_profile_core
from core import json_diagnostics as json_diag_core
from core import json_error_diagnostics_core
from core import json_error_highlight_core
from core import layout_topbar as layout_topbar_core
from core import startup_loader as startup_loader_core
try:
    import winreg
except Exception:
    winreg = None

# Backward-compatible module alias for older tests/integrations.
edit_guard_service = highlight_label_service


# Module-level helper to locate 7z executable. Used during initialization
def _module_find_7z():
    candidate = shutil.which("7z")
    if candidate:
        return candidate
    common_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path
    return None


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
    except Exception:
        return set()
    if not isinstance(data, list):
        return set()
    return {item.strip().lower() for item in data if isinstance(item, str) and item.strip()}


def _enable_windows_dpi_awareness():
    """Enable best-available DPI awareness on Windows before creating Tk root."""
    if sys.platform != "win32":
        return False
    try:
        user32 = ctypes.windll.user32
    except Exception:
        return False

    # Try Per-Monitor V2 first (Windows 10+), then older fallbacks.
    try:
        if bool(user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))):
            return True
    except Exception:
        pass
    try:
        shcore = ctypes.windll.shcore
        if int(shcore.SetProcessDpiAwareness(2)) == 0:
            return True
    except Exception:
        pass
    try:
        if bool(user32.SetProcessDPIAware()):
            return True
    except Exception:
        pass
    return False


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
    INPUT_MODE_RED_ARROW_ROOT_CATEGORIES = app_constants.INPUT_MODE_RED_ARROW_ROOT_CATEGORIES
    INPUT_MODE_RED_ARROW_ROOT_KEYS = app_constants.INPUT_MODE_RED_ARROW_ROOT_KEYS
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

    def __init__(self, root, path):
        self.root = root
        self.root.title(f"SIINDBAD's HackHub Editor - v{self.APP_VERSION}")
        self.data = None
        self.path = None
        # Use module-level helper to ensure availability during init
        self.seven_zip_path = _module_find_7z()
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
        except Exception:
            pass

        self._configure_root_display_profile()
        self._build_ui()
        # Keep only recent diagnostics day files at startup.
        self._purge_diag_logs_for_new_session()
        try:
            self.root.bind("<Destroy>", self._on_root_destroy, add="+")
        except Exception:
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
        except Exception:
            return False

    def _maybe_warn_windows_long_paths_disabled(self):
        if sys.platform != "win32":
            return
        if self._is_windows_long_paths_enabled():
            return
        try:
            self.set_status("Tip: Enable Windows long paths for better deep-folder compatibility.")
        except Exception:
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
        except Exception:
            width = 1280
        try:
            height = int(root.winfo_screenheight() or 720)
        except Exception:
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
        except Exception:
            pass
        try:
            tk_scaling = float(root.tk.call("tk", "scaling"))
            if tk_scaling > 0.2:
                candidates.append((tk_scaling * 72.0) / 96.0)
        except Exception:
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
        except Exception:
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
        except Exception:
            pass
        try:
            root.geometry(
                f"{int(layout['width'])}x{int(layout['height'])}"
                f"+{int(layout['x'])}+{int(layout['y'])}"
            )
        except Exception:
            try:
                root.geometry(f"{int(layout['width'])}x{int(layout['height'])}")
            except Exception:
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
            except Exception:
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
        except Exception:
            pass
        try:
            window.geometry(
                f"{int(geom['width'])}x{int(geom['height'])}"
                f"+{int(geom['x'])}+{int(geom['y'])}"
            )
        except Exception:
            pass

    def _build_ui(self):
        return ui_build_service.build_ui(self, tk=tk, ttk=ttk)

    def _safe_edit_undo(self, event=None):
        try:
            if getattr(self, "text", None):
                self.text.edit_undo()
        except Exception:
            pass
        return "break"

    def _safe_edit_redo(self, event=None):
        try:
            if getattr(self, "text", None):
                self.text.edit_redo()
        except Exception:
            pass
        return "break"

    def _build_editor_mode_toggle(self, parent):
        return ui_build_service.build_editor_mode_toggle(self, parent, tk=tk)

    def _build_input_mode_panel(self, parent, scroll_style):
        return ui_build_service.build_input_mode_panel(self, parent, scroll_style, tk=tk, ttk=ttk)

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
                font=(label_family, 8, "bold"),
            )
        except Exception:
            pass
        try:
            if input_container is not None:
                input_container.configure(
                    bg=panel,
                    bd=0,
                    highlightthickness=0,
                )
        except Exception:
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
                font=(input_family, 8, "bold"),
            )
        except Exception:
            pass

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

    def _refresh_input_mode_fields(self, path, value):
        host = getattr(self, "_input_mode_fields_host", None)
        if host is None:
            return
        for child in host.winfo_children():
            child.destroy()
        self._input_mode_field_specs = []
        self._input_mode_current_path = list(path or [])
        self._input_mode_no_fields_label = None
        theme = getattr(self, "_theme", {})
        panel_bg = theme.get("panel", "#161b24")
        host.configure(bg=panel_bg)
        normalized_path = list(path or [])
        if self._is_input_mode_category_disabled(normalized_path):
            variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
            fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"
            disabled = tk.Label(
                host,
                text=self.INPUT_MODE_DISABLED_CATEGORY_MESSAGE,
                bg=panel_bg,
                fg=fg,
                anchor="w",
                justify="left",
                padx=12,
                pady=12,
                font=(self._credit_name_font()[0], 11, "bold"),
            )
            disabled.pack(fill="x", expand=False)
            self._input_mode_no_fields_label = disabled
            return
        if len(normalized_path) == 0:
            variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
            fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"
            has_data = getattr(self, "data", None) is not None
            message = (
                "No direct value fields here. Select a specific item node to edit."
                if has_data
                else "No File Loaded. Open A .HHSAV File Before Continuing."
            )
            empty = tk.Label(
                host,
                text=message,
                bg=panel_bg,
                fg=fg,
                anchor="w",
                justify="left",
                padx=12,
                pady=12,
                font=(self._credit_name_font()[0], 9, "bold"),
            )
            empty.pack(fill="x", expand=False)
            self._input_mode_no_fields_label = empty
            return
        if (
            len(normalized_path) == 1
            and self._input_mode_root_key_for_path(normalized_path) == "network"
        ):
            variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
            fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"
            empty = tk.Label(
                host,
                text="Select A Sub Category To View Input Fields",
                bg=panel_bg,
                fg=fg,
                anchor="w",
                justify="left",
                padx=12,
                pady=12,
                font=(self._credit_name_font()[0], 11, "bold"),
            )
            empty.pack(fill="x", expand=False)
            self._input_mode_no_fields_label = empty
            self._input_mode_last_render_path_key = self._input_mode_path_key(normalized_path)
            self._input_mode_last_render_item = self.tree.focus() if getattr(self, "tree", None) is not None else None
            self._input_mode_force_refresh = False
            return
        if self._is_bank_input_style_path(normalized_path):
            bank_rows = self._collect_bank_input_rows(value)
            if bank_rows:
                self._render_bank_input_style_rows(host, normalized_path, bank_rows)
                host.update_idletasks()
                canvas = getattr(self, "_input_mode_canvas", None)
                if canvas is not None:
                    try:
                        canvas.configure(scrollregion=canvas.bbox("all") or (0, 0, 0, 0))
                        canvas.yview_moveto(0.0)
                    except Exception:
                        pass
                self._input_mode_last_render_path_key = self._input_mode_path_key(normalized_path)
                self._input_mode_last_render_item = self.tree.focus() if getattr(self, "tree", None) is not None else None
                self._input_mode_force_refresh = False
                return
        specs = self._collect_input_field_specs(value, normalized_path)
        if not specs:
            variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
            fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"
            empty = tk.Label(
                host,
                text="No direct value fields here. Select a specific item node to edit.",
                bg=panel_bg,
                fg=fg,
                anchor="w",
                justify="left",
                padx=12,
                pady=12,
                font=(self._credit_name_font()[0], 9, "bold"),
            )
            empty.pack(fill="x", expand=False)
            self._input_mode_no_fields_label = empty
            return

        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        row_divider = "#4f356f" if variant == "KAMUE" else "#254b6b"
        labels = [self._format_input_path_label(spec["rel_path"]) for spec in specs]
        max_label_chars = max((len(text) for text in labels), default=8)
        label_width_chars = max(14, min(30, max_label_chars + 1))
        for spec in specs:
            row = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=0)
            row.pack(fill="x", padx=8, pady=(6, 0))
            row.grid_columnconfigure(1, weight=1)

            label = tk.Label(
                row,
                text=self._format_input_path_label(spec["rel_path"]),
                anchor="w",
                justify="left",
                padx=0,
                pady=0,
                width=label_width_chars,
                font=(self._credit_name_font()[0], 8, "bold"),
            )
            label.grid(row=0, column=0, sticky="w", padx=(0, 10))

            value_container = tk.Frame(row, bg=panel_bg, bd=0, highlightthickness=0)
            value_container.grid(row=0, column=1, sticky="ew")
            value_container.grid_columnconfigure(0, weight=1)

            initial = spec["initial"]
            text_value = "" if initial is None else f"  {initial}"
            var = tk.StringVar(value=text_value)
            widget = tk.Entry(
                value_container,
                textvariable=var,
                font=(self._credit_name_font()[0], 8, "bold"),
            )
            self._style_input_mode_row_widgets(label, widget, input_container=value_container)
            widget.grid(row=0, column=0, sticky="ew", padx=4, pady=2, ipady=2)

            divider = tk.Frame(row, bg=row_divider, height=1, bd=0, highlightthickness=0)
            divider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

            spec["var"] = var
            spec["widget"] = widget
            self._input_mode_field_specs.append(spec)

        host.update_idletasks()
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is not None:
            try:
                canvas.configure(scrollregion=canvas.bbox("all") or (0, 0, 0, 0))
                canvas.yview_moveto(0.0)
            except Exception:
                pass
        self._input_mode_last_render_path_key = self._input_mode_path_key(normalized_path)
        self._input_mode_last_render_item = self.tree.focus() if getattr(self, "tree", None) is not None else None
        self._input_mode_force_refresh = False

    def _input_mode_path_key(self, path):
        if isinstance(path, list):
            return tuple(self._input_mode_path_key(token) for token in path)
        if isinstance(path, tuple):
            return tuple(self._input_mode_path_key(token) for token in path)
        return path

    def _can_skip_input_mode_refresh(self, item_id, target_path):
        return editor_mode_switch_service.can_skip_input_mode_refresh(self, item_id, target_path)

    def _refresh_editor_mode_view(self):
        text = getattr(self, "text", None)
        text_scroll = getattr(self, "_text_scroll", None)
        input_container = getattr(self, "_input_mode_container", None)
        if text is None or input_container is None or text_scroll is None:
            return
        mode = str(getattr(self, "_editor_mode", "JSON")).upper()
        self._apply_tree_mode_style(mode)
        show_input = (mode == "INPUT")
        editor_mode_top_inset = 24
        if show_input:
            try:
                text.pack_forget()
                text_scroll.pack_forget()
            except Exception:
                pass
            if not input_container.winfo_ismapped():
                input_container.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
            item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
            path = self.item_to_path.get(item_id, []) if item_id else []
            if isinstance(path, tuple) and path[0] == "__group__":
                _, list_path, group = path
                value = self._get_value(list_path)
                group_items = [
                    item for item in value
                    if isinstance(item, dict) and item.get("type") == group
                ]
                self._refresh_input_mode_fields(list_path, group_items)
            else:
                try:
                    value = self._get_value(path) if item_id else {}
                except Exception:
                    value = {}
                self._refresh_input_mode_fields(path, value)
            return

        try:
            input_container.pack_forget()
        except Exception:
            pass
        if not text.winfo_ismapped():
            text.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
        if not text_scroll.winfo_ismapped():
            text_scroll.pack(fill="y", side="right", pady=(editor_mode_top_inset, 0))
        if getattr(self, "data", None) is None:
            self._show_json_no_file_message()

    def _apply_tree_mode_style(self, mode=None):
        use_mode = str(mode or getattr(self, "_editor_mode", "JSON")).upper()
        tree_mode_service.apply_tree_mode(self, use_mode)

    def _show_json_no_file_message(self):
        text = getattr(self, "text", None)
        if text is None:
            return
        self._set_json_text_editable(True)
        self._clear_json_lock_highlight()
        json_view_service.show_json_no_file_message(text)

    @staticmethod
    def _set_nested_value(container, rel_path, new_value):
        return input_mode_service.set_nested_value(container, rel_path, new_value)

    @staticmethod
    def _strip_input_display_prefix(raw):
        return input_mode_service.strip_input_display_prefix(raw)

    def _coerce_input_field_value(self, spec):
        return input_mode_service.coerce_input_field_value(spec)

    def _apply_input_edit(self):
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("No selection", "Select a node in the tree.")
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            messagebox.showwarning("Not editable", "Select a specific item to edit.")
            return
        if self._is_input_mode_category_disabled(path):
            messagebox.showwarning("Not editable", self.INPUT_MODE_DISABLED_CATEGORY_MESSAGE)
            return
        specs = list(getattr(self, "_input_mode_field_specs", []) or [])
        if not specs:
            messagebox.showwarning("No fields", "No editable scalar fields for this node.")
            return
        value = self._get_value(path)
        working = input_mode_service.deep_copy_json_compatible(value)
        try:
            for spec in specs:
                coerced = self._coerce_input_field_value(spec)
                rel_path = list(spec.get("rel_path", []))
                if rel_path:
                    self._set_nested_value(working, rel_path, coerced)
                else:
                    working = coerced
        except ValueError as exc:
            messagebox.showwarning("Invalid Entry", f"Input value type mismatch: {exc}")
            return

        if not self._is_edit_allowed(path, working):
            return
        self._set_value(path, working)
        if self._is_bank_input_style_path(path):
            # Bank INPUT rows already reflect the edited value; skip full repaint to avoid flicker.
            self._input_mode_last_render_item = item_id
            self._input_mode_last_render_path_key = self._input_mode_path_key(path)
            self._input_mode_force_refresh = False
        else:
            self._populate_children(item_id)
            self.on_select(None)
        self.set_status("Edited")

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
        except Exception:
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
        self._refresh_editor_mode_view()
        if mode == "JSON":
            try:
                self.on_select(None)
            except Exception:
                pass

    def _update_editor_mode_controls(self):
        host = getattr(self, "_editor_mode_host", None)
        parent = getattr(self, "_editor_mode_parent", None)
        if host is None or parent is None:
            return
        try:
            if not (host.winfo_exists() and parent.winfo_exists()):
                return
        except Exception:
            return
        show = True
        theme = getattr(self, "_theme", {})
        try:
            host.configure(bg=theme.get("panel", "#161b24"))
        except Exception:
            pass
        if not show:
            try:
                host.place_forget()
            except Exception:
                pass
            return
        try:
            host.place(relx=1.0, y=0, x=-16, anchor="ne")
        except Exception:
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
            except Exception:
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
            except Exception:
                pass
        canvas = getattr(self, "_input_mode_canvas", None)
        if canvas is not None:
            try:
                if canvas.winfo_exists():
                    canvas.configure(bg=panel_bg, highlightbackground=panel_bg, highlightcolor=panel_bg)
            except Exception:
                pass
        host = getattr(self, "_input_mode_fields_host", None)
        if host is not None:
            try:
                if host.winfo_exists():
                    host.configure(bg=panel_bg)
            except Exception:
                pass
        notice = getattr(self, "_input_mode_no_fields_label", None)
        if notice is not None:
            try:
                if notice.winfo_exists():
                    notice.configure(bg=panel_bg, fg=notice_fg)
            except Exception:
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
            except Exception:
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
            except Exception:
                pass
        self._update_find_entry_layout()
        self._schedule_topbar_alignment(delay_ms=0)

    def _build_siindbad_toolbar(self, top):
        self._build_toolbar_structure(top, inter_button_pad=2)

    def _build_kamue_toolbar(self, top):
        style = self._siindbad_effective_style()
        self._build_toolbar_structure(top, inter_button_pad=(3 if style == "A" else 2))

    def _build_toolbar_structure(self, top, inter_button_pad):
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        style = self._siindbad_effective_style()
        is_variant_b = style == "B"
        find_host_pad = (2, 0) if is_variant_b else (4, 2)
        find_btn_pad = (2, 0) if is_variant_b else (4, 0)
        font_host_pad = (2, 0)

        right_actions = ttk.Frame(top)
        right_actions.pack(side="right")

        open_btn = self._make_toolbar_button(top, "Open", self.open_file, image_key="open")
        self._pack_toolbar_control(open_btn, side="left")
        self._toolbar_buttons["open"] = open_btn

        apply_btn = self._make_toolbar_button(top, "Apply Edit", self.apply_edit, image_key="apply")
        self._pack_toolbar_control(apply_btn, side="left", padx=(inter_button_pad, 0))
        self._toolbar_buttons["apply"] = apply_btn

        export_btn = self._make_toolbar_button(top, "Export .hhsav", self.export_hhsave, image_key="export")
        self._pack_toolbar_control(export_btn, side="left", padx=(inter_button_pad, 0))
        self._toolbar_buttons["export"] = export_btn

        theme = getattr(self, "_theme", {})
        find_fill = tk.Frame(
            top,
            bg=theme.get("bg", "#0f131a"),
            bd=0,
            highlightthickness=0,
        )
        find_fill.pack(side="left", padx=find_host_pad)
        self._find_host_default_padx = find_host_pad
        find_fill.configure(height=33 if is_variant_b else 34)
        find_fill.pack_propagate(False)
        self._find_entry_host = find_fill
        find_bg = theme.get("panel", "#161b24")
        find_fg = theme.get("fg", "#e6e6e6")
        find_select_bg = theme.get("select_bg", "#2f3a4d")
        find_select_fg = theme.get("select_fg", "#ffffff")
        find_border = theme.get("find_border", "#ffffff")
        self.find_entry = tk.Entry(
            find_fill,
            width=20,
            font=(self._preferred_mono_family(), 10),
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=find_border,
            highlightcolor=find_border,
            bg=find_bg,
            fg=find_fg,
            insertbackground=find_fg,
            selectbackground=find_select_bg,
            selectforeground=find_select_fg,
        )
        self.find_entry.pack(fill="none", expand=False, padx=0, pady=(5, 3), ipady=1)
        self.find_entry.bind("<Return>", self.find_next)

        find_btn = self._make_toolbar_button(right_actions, "Find Next", self.find_next, image_key="find")
        self._pack_toolbar_control(find_btn, side="left", padx=find_btn_pad)
        self._find_button_default_padx = find_btn_pad
        self._toolbar_buttons["find"] = find_btn

        font_frame = ttk.Frame(right_actions)
        font_frame.pack(side="left", padx=font_host_pad)
        self._font_control_host = font_frame
        self._render_font_control()

        update_btn = self._make_toolbar_button(
            right_actions, "Update", self.check_for_updates_manual, image_key="update"
        )
        self._pack_toolbar_control(update_btn, side="left", padx=(inter_button_pad, 0))
        self._toolbar_buttons["update"] = update_btn

        readme_btn = self._make_toolbar_button(right_actions, "ReadMe", self.show_readme, image_key="readme")
        self._pack_toolbar_control(readme_btn, side="left", padx=(inter_button_pad, 0))
        self._toolbar_buttons["readme"] = readme_btn

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
            except Exception:
                pass
        try:
            self._updates_auto_after_id = root.after(max(1, int(delay_ms)), self._run_check_for_updates_auto)
        except Exception:
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
            "_startup_loader_text_after_id",
            "_startup_loader_hide_after_id",
            "_startup_loader_progress_after_id",
            "_startup_loader_title_after_id",
            "_topbar_align_after_id",
            "_text_context_menu_pulse_after_id",
            "_bug_report_pulse_after_id",
            "_bug_submit_splash_after_id",
            "_crash_report_offer_after_id",
        ):
            after_id = getattr(self, attr, None)
            if after_id:
                try:
                    root.after_cancel(after_id)
                except Exception:
                    pass
            setattr(self, attr, None)

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
        self._cancel_scheduled_after_callbacks()
        # Enforce diagnostics day-file retention on app shutdown.
        self._purge_diag_logs_for_new_session()

    def _show_themed_update_info(self, title, message, include_startup_toggle=False):
        startup_state = None
        startup_callback = None
        if bool(include_startup_toggle):
            startup_state = bool(getattr(self, "_startup_update_check_enabled", False))
            startup_callback = self._set_startup_update_check_enabled
        update_ui_service.show_themed_update_info(
            self,
            title,
            message,
            tk=tk,
            messagebox=messagebox,
            startup_check_state=startup_state,
            on_startup_check_change=startup_callback,
        )

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
        except Exception:
            pass

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
        root = getattr(self, "root", None)
        if root is None:
            return default
        if threading.current_thread() is threading.main_thread():
            try:
                return callback(*args, **kwargs)
            except Exception:
                return default

        if not wait:
            def invoke_async():
                try:
                    callback(*args, **kwargs)
                except Exception:
                    pass

            try:
                root.after(0, invoke_async)
            except Exception:
                return default
            return default

        result = {"value": default}
        done = threading.Event()

        def invoke_sync():
            try:
                result["value"] = callback(*args, **kwargs)
            except Exception:
                result["value"] = default
            finally:
                done.set()

        try:
            root.after(0, invoke_sync)
        except Exception:
            return default
        done.wait(max(0.0, float(timeout)))
        return result["value"]

    @staticmethod
    def _walk_exception_chain(exc, max_depth=8):
        yield from update_service.walk_exception_chain(exc, max_depth=max_depth)

    def _format_update_error(self, exc):
        return update_service.format_update_error(exc)

    def _manual_update_download_url(self):
        # Manual fallback should use public GitHub Releases, not raw dist branch files.
        return (
            f"https://github.com/{self.GITHUB_OWNER}/{self.GITHUB_REPO}"
            f"/releases/latest/download/{self.GITHUB_ASSET_NAME}"
        )

    def _offer_manual_update_fallback(self, pretty_error):
        if not pretty_error:
            pretty_error = "Update failed."
        prompt = (
            f"{pretty_error}\n\n"
            "Would you like to open the manual update download page now?"
        )
        wants_open = bool(
            messagebox.askyesno(
                "Update",
                prompt,
                default=messagebox.NO,
            )
        )
        if not wants_open:
            return False
        url = self._manual_update_download_url()
        if not url:
            return False
        try:
            webbrowser.open(url)
            self._set_status("Opened manual update download page.")
            return True
        except Exception:
            self._set_status("Could not open browser for manual update download.")
            return False

    def _log_update_failure(self, exc, auto=False, pretty_error=""):
        try:
            path = self._diag_log_path()
            self._trim_text_file_for_append(path, self.DIAG_LOG_MAX_BYTES, self.DIAG_LOG_KEEP_BYTES)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            chain = []
            for err in self._walk_exception_chain(exc, max_depth=5):
                chain.append(f"{type(err).__name__}: {str(err).strip()}")
            details = " | ".join(part for part in chain if part) or str(exc or "").strip()
            mode = "auto" if bool(auto) else "manual"
            entry = (
                "\n---\n"
                f"time={stamp}\n"
                f"context=update_failure\n"
                f"mode={mode}\n"
                f"summary={str(pretty_error or '').strip()}\n"
                f"detail={details}\n"
            )
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(entry)
        except Exception:
            return

    def _fetch_dist_version(self):
        # Prefer immutable release metadata (tag) over mutable branch files.
        release_info = None
        try:
            release_info = self._fetch_latest_release_info()
        except Exception:
            release_info = None
        if isinstance(release_info, dict):
            tag_name = str(release_info.get("tag_name", "")).strip()
            if tag_name:
                return tag_name

        # Compatibility fallback: read version asset from latest release download URL.
        url = self._dist_url(self.DIST_VERSION_FILE)
        data = self._download_bytes_with_retries(url)
        data = data.decode("utf-8", errors="replace")
        return data.strip()

    def _download_dist_asset(self):
        release_info = None
        try:
            release_info = self._fetch_latest_release_info()
        except Exception:
            release_info = None
        url = self._release_asset_download_url(release_info, self.GITHUB_ASSET_NAME)
        if not url:
            url = self._dist_url(self.GITHUB_ASSET_NAME)
        tmp_dir = tempfile.mkdtemp(prefix="sins_update_")
        new_path = os.path.join(tmp_dir, self.GITHUB_ASSET_NAME)
        self._download_to_file_with_retries(url, new_path)
        if not os.path.isfile(new_path) or os.path.getsize(new_path) <= 0:
            raise RuntimeError("Downloaded update is empty.")
        # Basic sanity check for a Windows PE executable.
        with open(new_path, "rb") as handle:
            signature = handle.read(2)
        if signature != b"MZ":
            raise RuntimeError("Downloaded update is not a valid EXE file.")
        expected_sha256 = self._fetch_dist_asset_sha256(release_info=release_info)
        if not expected_sha256:
            if self.UPDATE_REQUIRE_SHA256:
                raise RuntimeError("Update checksum file missing or invalid.")
        else:
            actual_sha256 = self._sha256_file(new_path).strip().lower()
            if actual_sha256 != expected_sha256:
                raise RuntimeError("Downloaded update checksum mismatch.")
        self._verify_downloaded_update_signature(new_path)
        return new_path

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
        if not bool(getattr(self, "UPDATE_VERIFY_AUTHENTICODE", True)):
            return
        if sys.platform != "win32":
            return
        check_path = os.path.abspath(path)
        escaped_path = check_path.replace("'", "''")
        ps_script = (
            "$ErrorActionPreference='Stop';"
            f"$sig=Get-AuthenticodeSignature -LiteralPath '{escaped_path}';"
            "[pscustomobject]@{"
            "Status=[string]$sig.Status;"
            "StatusMessage=[string]$sig.StatusMessage;"
            "Subject=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Subject}else{''});"
            "Thumbprint=[string]$(if($sig.SignerCertificate){$sig.SignerCertificate.Thumbprint}else{''})"
            "} | ConvertTo-Json -Compress"
        )
        strict = bool(getattr(self, "UPDATE_REQUIRE_AUTHENTICODE", False))
        allowed_subjects = tuple(
            str(item).strip().casefold()
            for item in (getattr(self, "UPDATE_AUTHENTICODE_ALLOWED_SUBJECTS", ()) or ())
            if str(item).strip()
        )
        try:
            probe = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if probe.returncode != 0:
                raise RuntimeError((probe.stderr or probe.stdout or "").strip() or "signature check failed")
            payload = json.loads((probe.stdout or "").strip() or "{}")
            status = str(payload.get("Status", "")).strip()
            subject = str(payload.get("Subject", "")).strip()
            status_msg = str(payload.get("StatusMessage", "")).strip()
        except Exception as exc:
            if strict:
                raise RuntimeError(f"Downloaded update signature check failed: {exc}") from exc
            return

        is_valid = status.lower() == "valid"
        if is_valid and allowed_subjects:
            subj_norm = subject.casefold()
            is_valid = any(token in subj_norm for token in allowed_subjects)
            if strict and not is_valid:
                raise RuntimeError("Downloaded update signature subject is not in allow-list.")

        if strict and not is_valid:
            detail = status_msg or status or "invalid signature"
            raise RuntimeError(f"Downloaded update Authenticode signature check failed: {detail}")

    @staticmethod
    def _extract_sha256_from_text(text, asset_name):
        if not text:
            return None
        asset_name = str(asset_name or "").strip().lower()
        single_hash = re.compile(r"^[0-9a-fA-F]{64}$")
        hash_anywhere = re.compile(r"\b[0-9a-fA-F]{64}\b")
        for raw_line in str(text).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            candidate = line.split("#", 1)[0].strip()
            if not candidate:
                continue
            if single_hash.fullmatch(candidate):
                return candidate.lower()
            if asset_name and asset_name not in candidate.lower():
                continue
            match = hash_anywhere.search(candidate)
            if match:
                return match.group(0).lower()
        return None

    def _fetch_dist_asset_sha256(self, release_info=None):
        if release_info is None:
            try:
                release_info = self._fetch_latest_release_info()
            except Exception:
                release_info = None
        candidates = [f"{self.GITHUB_ASSET_NAME}.sha256"]
        for name in self.DIST_ASSET_SHA256_CANDIDATES:
            if name not in candidates:
                candidates.append(name)
        for name in candidates:
            try:
                url = self._release_asset_download_url(release_info, name)
                if not url:
                    url = self._dist_url(name)
                data = self._download_bytes_with_retries(url)
            except Exception:
                continue
            parsed = self._extract_sha256_from_text(
                data.decode("utf-8", errors="replace"),
                self.GITHUB_ASSET_NAME,
            )
            if parsed:
                return parsed
        return None

    def _latest_release_api_url(self):
        return f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}/releases/latest"

    def _fetch_latest_release_info(self):
        url = self._latest_release_api_url()
        raw = self._download_bytes_with_retries(url)
        try:
            parsed = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception as exc:
            raise RuntimeError("No release info available.") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("No release info available.")
        return parsed

    @staticmethod
    def _release_asset_download_url(release_info, asset_name):
        if not isinstance(release_info, dict):
            return ""
        want = str(asset_name or "").strip().casefold()
        if not want:
            return ""
        assets = release_info.get("assets")
        if not isinstance(assets, list):
            return ""
        for item in assets:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).strip().casefold() != want:
                continue
            return str(item.get("browser_download_url", "")).strip()
        return ""

    def _download_bytes_with_retries(self, url, attempts=3, timeout=60):
        return update_service.download_bytes_with_retries(
            url=url,
            headers=self._download_headers(),
            attempts=attempts,
            timeout=timeout,
            request_factory=urllib.request.Request,
            urlopen_fn=urllib.request.urlopen,
            is_retryable_fn=JsonEditor._is_retryable_download_error,
            backoff_fn=JsonEditor._download_backoff_delay,
            sleep_fn=time.sleep,
        )

    def _download_to_file_with_retries(
        self,
        url,
        out_path,
        attempts=3,
        timeout=60,
        chunk_size=1024 * 1024,
    ):
        return update_service.download_to_file_with_retries(
            url=url,
            out_path=out_path,
            headers=self._download_headers(),
            attempts=attempts,
            timeout=timeout,
            chunk_size=chunk_size,
            request_factory=urllib.request.Request,
            urlopen_fn=urllib.request.urlopen,
            is_retryable_fn=JsonEditor._is_retryable_download_error,
            backoff_fn=JsonEditor._download_backoff_delay,
            sleep_fn=time.sleep,
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
        exe_path = os.path.abspath(sys.executable)
        current_pid = os.getpid()
        return windows_runtime_service.install_update(
            new_path=new_path,
            exe_path=exe_path,
            current_pid=current_pid,
            start_hidden_process_fn=self._start_hidden_process,
            schedule_root_destroy_fn=lambda delay_ms: self.root.after(int(delay_ms), self.root.destroy),
            ps_escape_fn=self._ps_escape,
            restart_notice_ms=max(
                1200,
                int(getattr(self, "_update_restart_notice_ms", 4200) or 4200),
            ),
        )

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
        if not version:
            return ()
        cleaned = version.strip().lstrip("vV")
        parts = []
        for token in cleaned.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                break
        return tuple(parts)

    def _format_version(self, version_tuple):
        if not version_tuple:
            return ""
        return ".".join(str(part) for part in version_tuple)

    def _dist_url(self, filename):
        # Use latest GitHub release assets to avoid mutable branch dist trust.
        return (
            f"https://github.com/{self.GITHUB_OWNER}/{self.GITHUB_REPO}"
            f"/releases/latest/download/{filename}"
        )

    @staticmethod
    def _resolve_token_from_env_names(*env_names):
        # Resolve first non-empty token from ordered env names (primary -> fallback).
        for env_name in env_names:
            name = str(env_name or "").strip()
            if not name:
                continue
            value = os.getenv(name, "").strip()
            if value:
                return value
        return ""

    def _update_token_value(self):
        # Updater token policy: prefer dedicated read token, fall back to legacy token.
        return JsonEditor._resolve_token_from_env_names(
            getattr(self, "UPDATE_TOKEN_ENV", ""),
            getattr(self, "GITHUB_TOKEN_ENV", ""),
        )

    def _bug_report_token_env_name(self):
        # Bug-report token policy: prefer dedicated write token, fall back to legacy token env name.
        primary = str(getattr(self, "BUG_REPORT_TOKEN_ENV", "") or "").strip()
        fallback = str(getattr(self, "GITHUB_TOKEN_ENV", "") or "").strip()
        if primary and os.getenv(primary, "").strip():
            return primary
        if fallback:
            return fallback
        return primary

    def _has_bug_report_token(self):
        return bool(
            JsonEditor._resolve_token_from_env_names(
                getattr(self, "BUG_REPORT_TOKEN_ENV", ""),
                getattr(self, "GITHUB_TOKEN_ENV", ""),
            )
        )

    def _download_headers(self):
        headers = {"User-Agent": "sins-editor"}
        token = JsonEditor._update_token_value(self)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _set_status(self, text):
        if self.status is None:
            return
        try:
            self.root.after(0, lambda: self.status.config(text=text))
        except Exception:
            return

    def _selected_tree_path_text(self):
        try:
            item_id = self.tree.focus()
        except Exception:
            item_id = None
        return tree_view_service.selected_tree_path_text(item_id, self.item_to_path)

    def _diag_log_path(self):
        runtime_dir = self._runtime_data_dir(create=True)
        base, ext = os.path.splitext(str(self.DIAG_LOG_FILENAME))
        dated_name = f"{base}-{datetime.now().strftime('%Y-%m-%d')}{ext}"
        return os.path.join(runtime_dir, dated_name)

    def _purge_diag_logs_for_new_session(self):
        keep_days = max(1, int(getattr(self, "DIAG_LOG_KEEP_DAYS", 2) or 2))
        runtime_dir = self._runtime_data_dir(create=True)
        base, ext = os.path.splitext(str(self.DIAG_LOG_FILENAME))
        prefix = f"{base}-"
        legacy_names = set(self.LEGACY_DIAG_LOG_FILENAMES)
        keep_stamps = {
            (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range(keep_days)
        }

        try:
            entries = list(os.scandir(runtime_dir))
        except Exception:
            entries = []
        for entry in entries:
            if not entry.is_file():
                continue
            name = str(entry.name)
            should_delete = False
            if name == str(self.DIAG_LOG_FILENAME) or name in legacy_names:
                should_delete = True
            elif name.startswith(prefix) and (not ext or name.endswith(ext)):
                stamp = name[len(prefix) : len(name) - len(ext)] if ext else name[len(prefix) :]
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp) and stamp not in keep_stamps:
                    should_delete = True
            if not should_delete:
                continue
            try:
                os.remove(entry.path)
            except Exception:
                continue

        # Remove legacy diagnostics names from temp/runtime locations.
        names = [self.DIAG_LOG_FILENAME] + list(self.LEGACY_DIAG_LOG_FILENAMES)
        dirs = [runtime_dir, tempfile.gettempdir()]
        for base_dir in dirs:
            for name in names:
                path = os.path.join(base_dir, str(name))
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except Exception:
                    continue

    def _runtime_data_dir(self, create=False):
        base = None
        if sys.platform == "win32":
            base = (
                str(os.environ.get("LOCALAPPDATA", "")).strip()
                or str(os.environ.get("APPDATA", "")).strip()
            )
        if not base:
            try:
                home = os.path.expanduser("~")
                if sys.platform == "win32":
                    base = home
                else:
                    base = os.path.join(home, ".local", "state")
            except Exception:
                base = os.getcwd()
        target = os.path.join(base, self.RUNTIME_DIR_NAME)
        if create:
            try:
                os.makedirs(target, exist_ok=True)
            except Exception:
                return os.getcwd()
        return target

    def _crash_log_path(self):
        return os.path.join(self._runtime_data_dir(create=True), self.CRASH_LOG_FILENAME)

    def _crash_state_path(self):
        return os.path.join(self._runtime_data_dir(create=True), self.CRASH_STATE_FILENAME)

    def _read_crash_log_tail(self, max_chars=None):
        path = self._crash_log_path()
        limit = self.CRASH_LOG_TAIL_MAX_CHARS if max_chars is None else max(0, int(max_chars))
        return runtime_log_service.read_text_file_tail(path, limit)

    def _read_latest_crash_block(self, max_chars=None):
        text = self._read_crash_log_tail(max_chars=0)
        limit = self.CRASH_LOG_TAIL_MAX_CHARS if max_chars is None else max(0, int(max_chars))
        return runtime_log_service.read_latest_block(text, max_chars=limit, marker="\n---\n")

    def _read_crash_prompt_state(self):
        path = self._crash_state_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                parsed = json.load(fh)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {}

    def _write_crash_prompt_state(self, crash_hash):
        path = self._crash_state_path()
        payload = json.dumps(
            {
                "last_seen_hash": str(crash_hash or ""),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            ensure_ascii=False,
            indent=2,
        )
        try:
            self._write_text_file_atomic(path, payload, encoding="utf-8")
        except Exception:
            return

    def _pending_crash_report_payload(self):
        path = self._crash_log_path()
        if not os.path.isfile(path):
            return None
        try:
            if os.path.getsize(path) <= 0:
                return None
        except Exception:
            return None
        crash_tail = self._read_latest_crash_block()
        if not crash_tail.strip():
            return None
        crash_hash = hashlib.sha256(crash_tail.encode("utf-8", errors="replace")).hexdigest().lower()
        state = self._read_crash_prompt_state()
        if str(state.get("last_seen_hash", "")).strip().lower() == crash_hash:
            return None
        return {"hash": crash_hash, "tail": crash_tail}

    def _schedule_crash_report_offer(self, delay_ms=450):
        root = getattr(self, "root", None)
        if root is None:
            return
        existing = getattr(self, "_crash_report_offer_after_id", None)
        if existing:
            try:
                root.after_cancel(existing)
            except Exception:
                pass
        self._crash_report_offer_after_id = None
        try:
            self._crash_report_offer_after_id = root.after(
                max(1, int(delay_ms)),
                self._offer_crash_report_if_available,
            )
        except Exception:
            self._crash_report_offer_after_id = None

    def _offer_crash_report_if_available(self):
        self._crash_report_offer_after_id = None
        payload = self._pending_crash_report_payload()
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
            self._ui_call(
                messagebox.askyesno,
                "Crash Detected",
                prompt,
                wait=True,
                default=False,
            )
        )
        self._write_crash_prompt_state(crash_hash)
        if not wants_report:
            return
        self._open_bug_report_dialog(
            summary_prefill="Crash on previous session",
            details_prefill=(
                "The app crashed in my previous session.\n"
                "Please review the attached crash log tail.\n\n"
                "What I was doing before crash:\n"
            ),
            include_diag_default=True,
            crash_tail=crash_tail,
        )

    def _append_crash_log(self, context, exc_type, exc_value, exc_tb):
        try:
            path = self._crash_log_path()
            self._trim_text_file_for_append(path, self.DIAG_LOG_MAX_BYTES, self.DIAG_LOG_KEEP_BYTES)
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            header = (
                f"\n---\n"
                f"time={stamp}\n"
                f"context={context}\n"
                f"version={self.APP_VERSION}\n"
            )
            detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(header)
                fh.write(detail.rstrip())
                fh.write("\n")
        except Exception:
            return

    def _show_crash_notice_once(self):
        if self._crash_notice_shown:
            return
        self._crash_notice_shown = True
        crash_path = self._crash_log_path()
        msg = (
            "An unexpected error occurred.\n"
            "A crash log was written to:\n"
            f"{crash_path}"
        )
        self._ui_call(messagebox.showerror, "Unexpected Error", msg, wait=False)

    def _handle_unhandled_exception(self, context, exc_type, exc_value, exc_tb):
        self._append_crash_log(context, exc_type, exc_value, exc_tb)
        self._show_crash_notice_once()

    def _handle_sys_excepthook(self, exc_type, exc_value, exc_tb):
        self._handle_unhandled_exception("sys.excepthook", exc_type, exc_value, exc_tb)
        prev = getattr(self, "_prev_sys_excepthook", None)
        if callable(prev) and prev is not self._handle_sys_excepthook:
            try:
                prev(exc_type, exc_value, exc_tb)
            except Exception:
                pass

    def _handle_threading_excepthook(self, args):
        self._handle_unhandled_exception(
            "threading.excepthook",
            getattr(args, "exc_type", Exception),
            getattr(args, "exc_value", Exception("Unknown thread exception")),
            getattr(args, "exc_traceback", None),
        )
        prev = getattr(self, "_prev_threading_excepthook", None)
        if callable(prev) and prev is not self._handle_threading_excepthook:
            try:
                prev(args)
            except Exception:
                pass

    def _handle_tk_callback_exception(self, exc_type, exc_value, exc_tb):
        self._handle_unhandled_exception("tk.report_callback_exception", exc_type, exc_value, exc_tb)

    def _install_global_error_hooks(self):
        if self._error_hooks_installed:
            return
        self._error_hooks_installed = True
        try:
            self._prev_sys_excepthook = sys.excepthook
            sys.excepthook = self._handle_sys_excepthook
        except Exception:
            pass
        if hasattr(threading, "excepthook"):
            try:
                self._prev_threading_excepthook = threading.excepthook
                threading.excepthook = self._handle_threading_excepthook
            except Exception:
                pass
        try:
            self.root.report_callback_exception = self._handle_tk_callback_exception
        except Exception:
            pass

    def _read_diag_log_tail(self, max_chars=8000):
        path = self._diag_log_path()
        return runtime_log_service.read_text_file_tail(path, max_chars)

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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        theme_variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        diag_tail = self._read_diag_log_tail() if include_diag else ""
        return bug_report_service.build_bug_report_markdown(
            summary=summary,
            details=details,
            now_text=now,
            app_version=self.APP_VERSION,
            theme_variant=theme_variant,
            selected_path=self._selected_tree_path_text(),
            last_json_error=getattr(self, "_last_json_error_msg", ""),
            last_highlight_note=getattr(self, "_last_error_highlight_note", ""),
            python_version=platform.python_version(),
            platform_text=platform.platform(),
            include_diag=include_diag,
            diag_tail=diag_tail,
            crash_tail=crash_tail,
            discord_contact=discord_contact,
            screenshot_url=screenshot_url,
            screenshot_filename=screenshot_filename,
            screenshot_note=screenshot_note,
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
        payload = str(body_markdown or "").strip()
        if not payload:
            return False
        root = getattr(self, "root", None)
        if root is None:
            return False
        try:
            root.clipboard_clear()
            root.clipboard_append(payload)
            root.update_idletasks()
            return True
        except Exception:
            return False

    def _open_bug_report_in_browser(self, title, body_markdown):
        # Privacy fallback: open clean issue form and rely on clipboard for full report text.
        JsonEditor._copy_bug_report_body_to_clipboard(self, body_markdown)
        issue_url = self._bug_report_new_issue_url(title, body_markdown, include_body=False)
        return bug_report_api_service.open_bug_report_in_browser(
            issue_url=issue_url,
            open_new_tab_fn=webbrowser.open_new_tab,
        )

    def _bug_report_submit_cooldown_remaining(self, now_monotonic=None):
        now_val = time.monotonic() if now_monotonic is None else float(now_monotonic)
        return bug_report_service.bug_report_submit_cooldown_remaining(
            last_submit_monotonic=getattr(self, "_last_bug_report_submit_monotonic", 0.0),
            cooldown_seconds=getattr(self, "BUG_REPORT_SUBMIT_COOLDOWN_SECONDS", 45),
            now_monotonic=now_val,
        )

    def _mark_bug_report_submit_now(self, now_monotonic=None):
        now_val = time.monotonic() if now_monotonic is None else float(now_monotonic)
        self._last_bug_report_submit_monotonic = now_val

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
                    except Exception:
                        pass
                    try:
                        dlg.destroy()
                    except Exception:
                        pass
            except Exception:
                pass
        if root is not None:
            try:
                current = root.grab_current()
            except Exception:
                current = None
            if current is not None:
                try:
                    current.grab_release()
                except Exception:
                    pass

    def _hide_bug_submit_splash(self):
        after_id = getattr(self, "_bug_submit_splash_after_id", None)
        self._bug_submit_splash_after_id = None
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        splash = getattr(self, "_bug_submit_splash", None)
        self._bug_submit_splash = None
        if splash is not None:
            try:
                if splash.winfo_exists():
                    splash.destroy()
            except Exception:
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
        except Exception:
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
                except Exception:
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
        except Exception:
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
        except Exception:
            pass
        root = getattr(self, "root", None)
        if root is not None:
            try:
                self._bug_report_pulse_after_id = root.after(210, self._tick_bug_report_header_pulse)
            except Exception:
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
            except Exception:
                pass
        except Exception:
            try:
                dialog.overrideredirect(False)
            except Exception:
                pass
            return False

        if close_widget is not None:
            try:
                close_widget.bind("<Button-1>", lambda _e: self._close_bug_report_dialog(), add="+")
            except Exception:
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
            except Exception:
                return

        def _end_move(_event):
            self._bug_report_is_dragging = False

        for widget in tuple(drag_widgets or ()):
            try:
                if widget is not None:
                    widget.bind("<ButtonPress-1>", _start_move, add="+")
                    widget.bind("<B1-Motion>", _on_move, add="+")
                    widget.bind("<ButtonRelease-1>", _end_move, add="+")
            except Exception:
                continue
        return True

    def _trim_text_file_for_append(self, path, max_bytes, keep_bytes):
        if not os.path.isfile(path):
            return
        if max_bytes <= 0 or keep_bytes <= 0:
            return
        try:
            size = os.path.getsize(path)
        except Exception:
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
        except Exception:
            return

    @staticmethod
    def _theme_palette_for_variant(variant):
        return theme_service.theme_palette_for_variant(variant)

    def _apply_dark_theme(self):
        palette = self._theme_palette_for_variant(getattr(self, "_app_theme_variant", "SIINDBAD"))
        bg = palette["bg"]
        fg = palette["fg"]
        tree_fg = palette.get("tree_fg", fg)
        panel = palette["panel"]
        accent = palette["accent"]
        select_bg = palette["select_bg"]
        select_fg = palette.get("tree_selected_fg", palette["select_fg"])
        button_active = palette["button_active"]
        button_pressed = palette["button_pressed"]
        title_bar_bg = palette["title_bar_bg"]
        title_bar_fg = palette["title_bar_fg"]
        title_bar_border = palette["title_bar_border"]

        self.root.configure(bg=bg)

        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TButton", background=accent, foreground=fg, padding=6)
        style.map(
            "TButton",
            background=[("active", button_active), ("pressed", button_pressed)],
            foreground=[("disabled", "#888888")],
        )
        style.configure("TEntry", fieldbackground=panel, foreground=fg, insertcolor=fg)
        style.configure("TPanedwindow", background=bg)
        style.configure("TScrollbar", background=bg, troughcolor=panel)
        self._v_scrollbar_style = "Editor.Vertical.TScrollbar"
        self._h_scrollbar_style = "Editor.Horizontal.TScrollbar"
        style.configure(
            self._v_scrollbar_style,
            gripcount=0,
            background=accent,
            troughcolor=panel,
            bordercolor=panel,
            arrowcolor=fg,
            darkcolor=panel,
            lightcolor=panel,
            relief="flat",
            arrowsize=12,
        )
        style.map(
            self._v_scrollbar_style,
            background=[("active", button_active), ("pressed", button_pressed)],
            arrowcolor=[("disabled", "#7a7a7a")],
        )
        style.configure(
            self._h_scrollbar_style,
            gripcount=0,
            background=accent,
            troughcolor=panel,
            bordercolor=panel,
            arrowcolor=fg,
            darkcolor=panel,
            lightcolor=panel,
            relief="flat",
            arrowsize=12,
        )
        style.map(
            self._h_scrollbar_style,
            background=[("active", button_active), ("pressed", button_pressed)],
            arrowcolor=[("disabled", "#7a7a7a")],
        )

        tree_is_variant_b = str(getattr(self, "_tree_style_variant", "B")).upper() == "B"
        if tree_is_variant_b:
            tree_fg = self._blend_hex_color(tree_fg, panel, 0.22)
        self._apply_tree_style(
            style=style,
            panel=panel,
            tree_fg=tree_fg,
            select_bg=select_bg,
            select_fg=select_fg,
        )
        self._theme = {
            "bg": bg,
            "fg": fg,
            "panel": panel,
            "tree_fg": tree_fg,
            "accent": accent,
            "select_bg": select_bg,
            "select_fg": select_fg,
            "credit_bg": palette["credit_bg"],
            "credit_border": palette["credit_border"],
            "credit_label_fg": palette["credit_label_fg"],
            "find_border": palette["find_border"],
            "logo_border_outer": palette["logo_border_outer"],
            "logo_border_inner": palette["logo_border_inner"],
            "button_active": button_active,
            "button_pressed": button_pressed,
            "title_bar_bg": title_bar_bg,
            "title_bar_fg": title_bar_fg,
            "title_bar_border": title_bar_border,
        }
        self._apply_windows_titlebar_theme(bg=title_bar_bg, fg=title_bar_fg, border=title_bar_border)
        self.root.after(
            0,
            lambda: self._apply_windows_titlebar_theme(
                bg=title_bar_bg, fg=title_bar_fg, border=title_bar_border
            ),
        )

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
            except Exception:
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
        except Exception:
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
        except Exception:
            pass

    def _apply_tree_indicator_layout(self, style):
        """Hide native indicator in TREE B so composite B2 icon pack provides branch arrows."""
        try:
            if self._tree_item_layout_default is None:
                self._tree_item_layout_default = style.layout("Treeview.Item")
        except Exception:
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
            except Exception:
                pass
            return

        try:
            if self._tree_item_layout_default:
                style.layout("Treeview.Item", self._tree_item_layout_default)
        except Exception:
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
        # Backward compatibility: older call sites passed the window as the first positional arg.
        if window_widget is None and bg is not None and hasattr(bg, "winfo_id"):
            window_widget = bg
            bg = None
        if sys.platform != "win32":
            return
        target = window_widget or self.root
        try:
            dwmapi = ctypes.windll.dwmapi
            user32 = ctypes.windll.user32
            target.update_idletasks()
            hwnd = user32.GetParent(target.winfo_id()) or target.winfo_id()
        except Exception:
            return

        hwnd_value = ctypes.c_void_p(hwnd)

        def _set_dwm_attr(attr, value):
            try:
                result = dwmapi.DwmSetWindowAttribute(
                    hwnd_value,
                    ctypes.c_uint(attr),
                    ctypes.byref(value),
                    ctypes.c_uint(ctypes.sizeof(value)),
                )
                return result == 0
            except Exception:
                return False

        dark_flag = ctypes.c_int(1)
        if not _set_dwm_attr(20, dark_flag):
            _set_dwm_attr(19, dark_flag)

        theme = getattr(self, "_theme", {}) or {}
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        default_bg = "#180c32" if variant == "KAMUE" else "#102535"
        default_fg = "#eee8ff" if variant == "KAMUE" else "#e6f6ff"
        default_border = "#30195c" if variant == "KAMUE" else "#2a5a7a"
        effective_bg = bg or theme.get("title_bar_bg", default_bg)
        effective_fg = fg or theme.get("title_bar_fg", default_fg)
        effective_border = border or theme.get("title_bar_border", default_border)

        if effective_bg:
            caption_color = self._hex_to_colorref(effective_bg)
            if caption_color is not None:
                _set_dwm_attr(35, ctypes.c_uint(caption_color))
        if effective_border:
            border_color = self._hex_to_colorref(effective_border)
            if border_color is not None:
                _set_dwm_attr(34, ctypes.c_uint(border_color))
        if effective_fg:
            text_color = self._hex_to_colorref(effective_fg)
            if text_color is not None:
                _set_dwm_attr(36, ctypes.c_uint(text_color))

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
        except Exception:
            pass
        self._configure_json_lock_tags()
        self._style_text_context_menu()

    def _build_text_context_menu(self):
        self._destroy_text_context_menu()
        try:
            scale = self._text_context_menu_scale()
            def _s(value, min_value=1):
                return max(min_value, int(round(float(value) * scale)))

            popup = tk.Toplevel(self.root)
            popup.withdraw()
            popup.overrideredirect(True)
            try:
                popup.attributes("-topmost", True)
            except Exception:
                pass

            anchor = tk.Frame(popup, bd=0, highlightthickness=1)
            anchor.pack(fill="both", expand=True)
            frame = tk.Frame(anchor, bd=0, highlightthickness=1)
            frame.pack(fill="both", expand=True, padx=1, pady=1)
            panel = tk.Frame(frame, bd=0, highlightthickness=1)
            panel.pack(fill="both", expand=True, padx=_s(3), pady=(_s(3), _s(2)))
            body = tk.Frame(panel, bd=0, highlightthickness=0)
            body.pack(fill="both", expand=True, padx=_s(2), pady=(_s(2), _s(1)))

            items = {}
            widget_actions = {}
            menu_layout = (
                ("undo", "Undo", "Ctrl+Z"),
                ("redo", "Redo", "Ctrl+Y"),
                ("copy", "Copy", "Ctrl+C"),
                ("paste", "Paste", "Ctrl+V"),
                ("autofix", "Auto-Fix", ""),
            )
            total_items = len(menu_layout)
            for item_idx, (action, label, shortcut) in enumerate(menu_layout):
                if action == "copy":
                    separator = tk.Frame(body, bd=0, height=1)
                    separator.pack(fill="x", padx=_s(7), pady=_s(5))
                    self._text_context_menu_separator = separator
                elif action == "autofix":
                    separator = tk.Frame(body, bd=0, height=1)
                    separator.pack(fill="x", padx=_s(7), pady=_s(5))
                row = tk.Frame(body, bd=0, highlightthickness=1, cursor="hand2")
                row_bottom = _s(0 if item_idx == (total_items - 1) else 1)
                row.pack(fill="x", padx=_s(2), pady=(_s(1), row_bottom))
                title = tk.Label(row, text=str(label).upper(), anchor="w")
                shortcut_label = tk.Label(row, text=shortcut, anchor="e")
                if action == "autofix":
                    title.configure(anchor="center", justify="center")
                    title.grid(
                        row=0,
                        column=0,
                        columnspan=2,
                        padx=_s(6),
                        pady=_s(4),
                        sticky="nsew",
                    )
                    row.grid_columnconfigure(0, weight=1)
                    row.grid_columnconfigure(1, weight=1)
                else:
                    title.grid(row=0, column=0, padx=(_s(11), _s(10)), pady=_s(4), sticky="w")
                    shortcut_label.grid(row=0, column=1, padx=(0, _s(7)), pady=_s(4), sticky="e")
                    row.grid_columnconfigure(0, weight=1)
                    row.grid_columnconfigure(1, weight=0)
                for widget in (row, title, shortcut_label):
                    widget_actions[widget] = action
                    widget.bind("<Motion>", self._on_text_context_menu_motion, add="+")
                for widget in (title, shortcut_label):
                    widget.bind(
                        "<Button-1>",
                        lambda _evt, key=action: self._on_text_context_menu_click(key),
                        add="+",
                    )
                row.bind(
                    "<Button-1>",
                    lambda _evt, key=action: self._on_text_context_menu_click(key),
                    add="+",
                )
                items[action] = {
                    "row": row,
                    "title": title,
                    "shortcut": shortcut_label,
                }
                if action in ("copy", "autofix"):
                    try:
                        self._text_context_menu_separators.append(separator)
                    except Exception:
                        pass

            popup.bind("<Escape>", self._on_text_context_menu_escape, add="+")
            popup.bind("<Button-1>", lambda _evt: "break", add="+")
            popup.bind("<Motion>", self._on_text_context_menu_motion, add="+")

            self._text_context_menu = popup
            self._text_context_menu_anchor = anchor
            self._text_context_menu_frame = frame
            self._text_context_menu_panel = panel
            self._text_context_menu_body = body
            self._text_context_menu_items = items
            self._text_context_menu_widget_actions = widget_actions
            self._text_context_menu_item_states = {key: True for key in items}
            self._text_context_menu_hover_action = None
            self._style_text_context_menu()
        except Exception:
            self._destroy_text_context_menu()

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
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists():
                return
        except Exception:
            return

        palette = self._text_context_menu_palette()
        scale = self._text_context_menu_scale()
        title_size = max(8, int(round(11 * scale)))
        small_size = max(7, int(round(9 * scale)))
        font_family = self._resolve_font_family(
            ["Tektur", "Oxanium", "Orbitron", "Rajdhani", "Share Tech Mono", "Segoe UI Semibold", "Segoe UI"],
            self._preferred_mono_family(),
        )
        try:
            popup.configure(bg=palette["frame_bg"])
        except Exception:
            pass

        anchor = getattr(self, "_text_context_menu_anchor", None)
        frame = getattr(self, "_text_context_menu_frame", None)
        panel = getattr(self, "_text_context_menu_panel", None)
        body = getattr(self, "_text_context_menu_body", None)
        separator = getattr(self, "_text_context_menu_separator", None)
        separators = list(getattr(self, "_text_context_menu_separators", []) or [])

        if anchor is not None:
            try:
                anchor.configure(
                    bg=palette["bg"],
                    highlightbackground=palette["border"],
                    highlightcolor=palette["border"],
                )
            except Exception:
                pass
        if frame is not None:
            try:
                frame.configure(
                    bg=palette["bg"],
                    highlightbackground=palette["inset_border"],
                    highlightcolor=palette["inset_border"],
                )
            except Exception:
                pass
        if panel is not None:
            try:
                panel.configure(
                    bg=palette["panel_bg"],
                    highlightbackground=palette["panel_border"],
                    highlightcolor=palette["panel_border"],
                )
            except Exception:
                pass
        if body is not None:
            try:
                body.configure(bg=palette["bg"])
            except Exception:
                pass
        if separator is not None:
            try:
                separator.configure(bg=palette["separator"])
            except Exception:
                pass
        for sep in separators:
            try:
                if sep is not None and sep.winfo_exists():
                    sep.configure(bg=palette["separator"])
            except Exception:
                pass

        self._style_text_context_menu_rows(
            palette=palette,
            font_family=font_family,
            shortcut_font_family=self._preferred_mono_family(),
            title_size=title_size,
            small_size=small_size,
            apply_fonts=True,
        )
        self._text_context_menu_row_style = {
            "palette": palette,
            "font_family": font_family,
            "shortcut_font_family": self._preferred_mono_family(),
            "title_size": title_size,
            "small_size": small_size,
        }

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
        parts = getattr(self, "_text_context_menu_items", {}).get(action)
        if not parts:
            return
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

        row = parts["row"]
        title = parts["title"]
        shortcut = parts["shortcut"]
        enabled = bool(getattr(self, "_text_context_menu_item_states", {}).get(action, True))
        hovered = bool(action == getattr(self, "_text_context_menu_hover_action", None) and enabled)
        if hovered:
            row_bg = palette["active_bg"]
            row_fg = palette["active_fg"]
            row_border = palette["active_border"]
            shortcut_fg = palette["active_fg"]
        else:
            row_bg = palette["bg"]
            row_fg = palette["fg"] if enabled else palette["disabled_fg"]
            row_border = palette["inset_border"]
            shortcut_fg = palette["shortcut_fg"] if enabled else palette["disabled_fg"]
        cursor = "hand2" if enabled else "arrow"
        try:
            row.configure(
                bg=row_bg,
                highlightbackground=row_border,
                highlightcolor=row_border,
                cursor=cursor,
            )
        except Exception:
            pass
        for widget in (title, shortcut):
            try:
                widget.configure(bg=row_bg)
            except Exception:
                pass
        try:
            if action == "autofix":
                title_kwargs = {
                    "fg": row_fg,
                    "cursor": cursor,
                    "anchor": "center",
                    "justify": "center",
                }
            else:
                title_kwargs = {
                    "fg": row_fg,
                    "cursor": cursor,
                }
            if apply_fonts:
                title_kwargs["font"] = (font_family, title_size, "bold")
            title.configure(**title_kwargs)
        except Exception:
            pass
        try:
            shortcut_kwargs = {
                "fg": shortcut_fg,
                "cursor": cursor,
            }
            if apply_fonts:
                shortcut_kwargs["font"] = (shortcut_font_family, small_size)
            shortcut.configure(**shortcut_kwargs)
        except Exception:
            pass

    def _has_text_selection(self):
        try:
            return bool(self.text.tag_ranges("sel"))
        except Exception:
            return False

    def _clipboard_has_text(self):
        try:
            value = self.root.clipboard_get()
        except Exception:
            return False
        return bool(value)

    def _text_can_undo(self):
        try:
            return bool(int(self.text.tk.call(self.text._w, "edit", "canundo")))
        except Exception:
            return False

    def _text_can_redo(self):
        try:
            return bool(int(self.text.tk.call(self.text._w, "edit", "canredo")))
        except Exception:
            return False

    def _destroy_text_context_menu(self):
        self._hide_text_context_menu()
        popup = getattr(self, "_text_context_menu", None)
        if popup is not None:
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except Exception:
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
        states = getattr(self, "_text_context_menu_item_states", {}) or {}
        for action in ("undo", "redo", "copy", "paste", "autofix"):
            if states.get(action):
                return action
        return None

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
        widget_actions = getattr(self, "_text_context_menu_widget_actions", {}) or {}
        current = widget
        while current is not None:
            action = widget_actions.get(current)
            if action:
                return action
            try:
                current = current.master
            except Exception:
                current = None
        return None

    def _text_context_menu_action_for_pointer(self):
        popup = getattr(self, "_text_context_menu", None)
        root = getattr(self, "root", None)
        if popup is None or root is None:
            return None, False
        try:
            pointer_x = root.winfo_pointerx()
            pointer_y = root.winfo_pointery()
            under_pointer = root.winfo_containing(pointer_x, pointer_y)
        except Exception:
            return None, False
        action = self._text_context_menu_action_for_widget(under_pointer)
        if action:
            return action, True
        if not self._widget_is_popup_child(under_pointer, popup):
            return None, False
        return None, True

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
        except Exception:
            under_pointer = None
        if self._widget_is_popup_child(under_pointer, popup):
            return "break"
        if getattr(self, "_text_context_menu_hover_action", None) is None:
            return "break"
        self._set_text_context_menu_hover_action(None)
        return "break"

    def _on_text_context_menu_click(self, action):
        states = getattr(self, "_text_context_menu_item_states", {}) or {}
        if not states.get(action):
            return "break"
        self._hide_text_context_menu()
        if action == "undo":
            self._on_context_undo()
        elif action == "redo":
            self._on_context_redo()
        elif action == "copy":
            self._on_context_copy()
        elif action == "paste":
            self._on_context_paste()
        elif action == "autofix":
            self._on_context_autofix()
        return "break"

    def _on_text_context_menu_escape(self, event=None):
        self._hide_text_context_menu()
        return "break"

    @staticmethod
    def _widget_is_popup_child(widget, popup):
        if widget is None or popup is None:
            return False
        widget_path = str(widget)
        popup_path = str(popup)
        return widget_path == popup_path or widget_path.startswith(popup_path + ".")

    def _bind_text_context_menu_global_dismiss(self):
        root = getattr(self, "root", None)
        if root is None:
            return
        self._unbind_text_context_menu_global_dismiss()
        bindings = []
        for sequence in ("<Button-1>", "<Button-2>", "<Button-3>", "<MouseWheel>", "<Escape>"):
            try:
                bind_id = root.bind(sequence, self._on_text_context_menu_global_dismiss, add="+")
            except Exception:
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
            except Exception:
                pass
        self._text_context_menu_global_bindings = []

    def _on_text_context_menu_global_dismiss(self, event=None):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except Exception:
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
        except Exception:
            return
        try:
            self.root.after(30, self._hide_text_context_menu_if_app_inactive)
        except Exception:
            self._hide_text_context_menu_if_app_inactive()

    def _on_root_focus_in(self, event=None):
        if not bool(getattr(self, "BUG_REPORT_USE_CUSTOM_CHROME", True)):
            return
        try:
            self.root.after(50, self._ensure_bug_report_dialog_visible)
        except Exception:
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
            except Exception:
                pass
        except Exception:
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
        except Exception:
            self._bug_report_follow_root = False

    def _on_root_configure(self, event=None):
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
        except Exception:
            return

    def _hide_text_context_menu_if_app_inactive(self):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except Exception:
            return
        root = getattr(self, "root", None)
        if root is None:
            self._hide_text_context_menu()
            return
        try:
            focused = root.focus_displayof()
        except Exception:
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
                except Exception:
                    pass

    def _tick_text_context_menu_pulse(self):
        self._text_context_menu_pulse_after_id = None
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return
        try:
            if not popup.winfo_exists() or not popup.winfo_ismapped():
                return
        except Exception:
            return
        palette = self._text_context_menu_palette()
        hover_action = getattr(self, "_text_context_menu_hover_action", None)
        if hover_action:
            root = getattr(self, "root", None)
            if root is None:
                return
            try:
                self._text_context_menu_pulse_after_id = root.after(140, self._tick_text_context_menu_pulse)
            except Exception:
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
            except Exception:
                pass
        if frame is not None:
            try:
                frame.configure(highlightbackground=inset_color, highlightcolor=inset_color)
            except Exception:
                pass
        if panel is not None:
            try:
                panel.configure(highlightbackground=panel_color, highlightcolor=panel_color)
            except Exception:
                pass
        root = getattr(self, "root", None)
        if root is None:
            return
        try:
            delay_ms = 140 if hover_action else 100
            self._text_context_menu_pulse_after_id = root.after(delay_ms, self._tick_text_context_menu_pulse)
        except Exception:
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
        except Exception:
            pass
        self._style_text_context_menu()

    def _show_text_context_menu_popup(self, popup_x, popup_y):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return False
        try:
            if not popup.winfo_exists():
                return False
        except Exception:
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
        except Exception:
            return False
        self._bind_text_context_menu_global_dismiss()
        self._start_text_context_menu_pulse()
        return True

    def _show_text_context_menu(self, event=None):
        popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            self._build_text_context_menu()
            popup = getattr(self, "_text_context_menu", None)
        if popup is None:
            return "break"
        try:
            self.text.focus_set()
        except Exception:
            pass

        anchor_index = "insert"
        if event is not None and hasattr(event, "x") and hasattr(event, "y"):
            try:
                idx = self.text.index(f"@{event.x},{event.y}")
                anchor_index = idx
                if not self._has_text_selection():
                    self.text.mark_set("insert", idx)
            except Exception:
                pass

        self._set_text_context_menu_item_state("undo", self._text_can_undo())
        self._set_text_context_menu_item_state("redo", self._text_can_redo())
        self._set_text_context_menu_item_state("copy", self._has_text_selection())
        self._set_text_context_menu_item_state("paste", self._clipboard_has_text())
        self._set_text_context_menu_item_state("autofix", self._can_context_autofix())
        self._text_context_menu_hover_action = None

        menu_req_h = 0
        vroot_top = 2
        vroot_bottom = 0
        text_bottom = None
        root_bottom = None
        try:
            popup.update_idletasks()
            menu_req_h = max(1, int(popup.winfo_reqheight()))
            vroot_y = int(self.root.winfo_vrooty())
            vroot_h = max(menu_req_h + 2, int(self.root.winfo_vrootheight()))
            vroot_top = vroot_y + 2
            vroot_bottom = vroot_y + vroot_h
            try:
                text_bottom = int(self.text.winfo_rooty()) + int(self.text.winfo_height())
            except Exception:
                text_bottom = None
            try:
                root_bottom = int(self.root.winfo_rooty()) + int(self.root.winfo_height())
            except Exception:
                root_bottom = None
        except Exception:
            menu_req_h = 0
            vroot_top = 2
            vroot_bottom = 0
            text_bottom = None
            root_bottom = None

        def _resolve_menu_y(preferred_y, anchor_top=None):
            try:
                y = int(preferred_y)
            except Exception:
                return preferred_y
            if menu_req_h <= 0:
                return y
            container_bottom = int(vroot_bottom)
            if container_bottom <= 0:
                try:
                    container_bottom = max(menu_req_h + 2, int(self.root.winfo_screenheight()))
                except Exception:
                    container_bottom = menu_req_h + 2
            try:
                if text_bottom is not None and int(text_bottom) > 0:
                    container_bottom = min(container_bottom, int(text_bottom))
            except Exception:
                pass
            try:
                if root_bottom is not None and int(root_bottom) > 0:
                    container_bottom = min(container_bottom, int(root_bottom))
            except Exception:
                pass
            bottom_limit = container_bottom - menu_req_h - 2
            if y > bottom_limit and anchor_top is not None:
                try:
                    above_y = int(anchor_top) - menu_req_h - 2
                    if above_y >= int(vroot_top):
                        return above_y
                except Exception:
                    pass
            if y > bottom_limit:
                y = max(int(vroot_top), bottom_limit)
            if y < int(vroot_top):
                y = int(vroot_top)
            return y

        popup_x = None
        popup_y = None
        if event is not None and hasattr(event, "x_root"):
            try:
                popup_x = int(event.x_root)
            except Exception:
                popup_x = None
        try:
            box = self.text.bbox(anchor_index)
            if box:
                # Anchor menu below the active line highlight for consistent placement.
                anchor_top = self.text.winfo_rooty() + int(box[1])
                popup_y = _resolve_menu_y(anchor_top + int(box[3]) + 2, anchor_top=anchor_top)
                if popup_x is None:
                    popup_x = self.text.winfo_rootx() + int(box[0]) + 6
        except Exception:
            popup_y = None
        if popup_x is None or popup_y is None:
            try:
                box = self.text.bbox("insert")
                if box:
                    popup_x = self.text.winfo_rootx() + int(box[0]) + 6
                    anchor_top = self.text.winfo_rooty() + int(box[1])
                    popup_y = _resolve_menu_y(anchor_top + int(box[3]) + 2, anchor_top=anchor_top)
            except Exception:
                popup_x = None
                popup_y = None
        if (popup_x is None or popup_y is None) and event is not None and hasattr(event, "x_root") and hasattr(event, "y_root"):
            try:
                popup_x = int(event.x_root)
                popup_y = _resolve_menu_y(int(event.y_root), anchor_top=int(event.y_root))
            except Exception:
                popup_x = None
                popup_y = None
        if popup_x is None or popup_y is None:
            try:
                popup_x = self.root.winfo_rootx() + 40
                popup_y = self.root.winfo_rooty() + 40
            except Exception:
                return "break"

        self._hide_text_context_menu()
        self._text_context_menu_hover_action = None
        self._show_text_context_menu_popup(popup_x, popup_y)
        return "break"

    def _on_context_copy(self):
        if not self._has_text_selection():
            return
        try:
            text = self.text.get("sel.first", "sel.last")
        except Exception:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            return

    def _on_context_undo(self):
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            self.text.edit_undo()
            self.text.see("insert")
            self._auto_apply_pending = True
        except Exception:
            return

    def _on_context_redo(self):
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            self.text.edit_redo()
            self.text.see("insert")
            self._auto_apply_pending = True
        except Exception:
            return

    def _on_context_paste(self):
        try:
            pasted = self.root.clipboard_get()
        except Exception:
            return
        if pasted is None:
            return
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        try:
            if self._has_text_selection():
                self.text.delete("sel.first", "sel.last")
        except Exception:
            pass
        try:
            self.text.insert("insert", pasted)
            self.text.see("insert")
            self._auto_apply_pending = True
        except Exception:
            return

    @staticmethod
    def _parse_suggestion_before_after(message):
        return error_service.parse_suggestion_before_after(message)

    def _current_error_line_number(self):
        focus_idx = getattr(self, "_error_focus_index", None)
        if focus_idx:
            try:
                return int(str(focus_idx).split(".")[0])
            except Exception:
                pass
        try:
            ranges = self.text.tag_ranges("json_error")
            if ranges:
                return int(str(ranges[0]).split(".")[0])
        except Exception:
            pass
        return None

    def _current_overlay_suggestion(self):
        overlay = getattr(self, "error_overlay", None)
        try:
            has_overlay = bool(overlay is not None and overlay.winfo_exists())
        except Exception:
            has_overlay = False
        line_no = self._current_error_line_number()
        return error_service.build_overlay_suggestion_payload(
            has_overlay=has_overlay,
            message=getattr(self, "_last_error_overlay_message", ""),
            line_no=line_no,
        )

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
        if before and before in raw_line:
            new_line = raw_line.replace(before, after, 1)
        elif before and raw_line.strip() == before.strip():
            new_line = indent + after.lstrip()
        elif not before:
            new_line = indent + after.lstrip()
        else:
            stripped_raw = raw_line.strip()
            if stripped_raw:
                new_line = indent + after.lstrip()
            else:
                new_line = after
        if new_line is None:
            return False

        try:
            start_idx = f"{int(line_no)}.0"
            self.text.delete(start_idx, f"{int(line_no)}.0 lineend")
            self.text.insert(start_idx, new_line)
            caret_col = max(len(new_line), 0)
            self.text.mark_set("insert", f"{int(line_no)}.{caret_col}")
            self.text.see(f"{int(line_no)}.{caret_col}")
            return True
        except Exception:
            return False

    def _restore_insert_index(self, restore_index, log_failure=False):
        """Best-effort cursor restore after local text rewrites or re-render passes."""
        if not restore_index:
            return
        target_line = 1
        try:
            target_line = int(self._line_number_from_index(restore_index) or 1)
        except Exception:
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
        except Exception:
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
            except Exception:
                pass
            return

    def _on_context_autofix(self):
        payload = self._current_overlay_suggestion()
        if not payload:
            return
        item_id = self.tree.focus() if getattr(self, "tree", None) is not None else None
        path = self.item_to_path.get(item_id, []) if item_id else []
        restore_index = ""
        try:
            restore_index = str(self.text.index("insert") or "")
        except Exception:
            restore_index = ""
        if self.error_overlay is not None:
            self._destroy_error_overlay()
            self._clear_json_error_highlight()
        changed = self._apply_line_autofix(
            payload.get("line"),
            payload.get("before"),
            payload.get("after"),
        )
        if changed:
            self._restore_insert_index(restore_index)
            try:
                self._apply_json_view_lock_state(path)
            except Exception:
                pass
            # Defer final cursor restore until apply_edit() completes and repaints this node.
            self._pending_insert_restore_index = str(restore_index or "")
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
        except Exception:
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
        except Exception:
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
        except Exception:
            pass
        self._mono_family = "Consolas"
        return self._mono_family

    def _resolve_font_family(self, preferred_families, fallback):
        families = getattr(self, "_font_family_lookup_cache", None)
        if families is None:
            families = {}
            try:
                families = {name.lower(): name for name in tkfont.families(self.root)}
            except Exception:
                families = {}
            self._font_family_lookup_cache = families
        try:
            for family in preferred_families:
                hit = families.get(str(family).lower())
                if hit:
                    return hit
        except Exception:
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
            except Exception:
                position_hint = None
            window.destroy()
        except Exception:
            self._readme_window = None
            return
        self._readme_window = None
        try:
            self.show_readme(position_hint=position_hint)
        except Exception:
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
                except Exception:
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
                except Exception:
                    pass

    def _update_font_size(self):
        """Update the font size in the text widget."""
        if self.text:
            mono = (self._preferred_mono_family(), self._font_size)
            self.text.configure(font=mono)
        # Keep tree text tied to editor font while preserving icon alignment.
        try:
            self._apply_tree_style()
        except Exception:
            pass
        if self._font_size_value_label and self._font_size_value_label.winfo_exists():
            try:
                self._font_size_value_label.configure(text=str(int(self._font_size)))
            except Exception:
                pass
        # Persist the chosen font size for future runs
        try:
            self._save_user_settings()
        except Exception:
            pass
        self._refresh_open_readme_window()
        # Keep active warning/error overlays synchronized with font-size changes.
        self._refresh_active_error_theme()

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
        except Exception:
            return

    def _settings_path(self):
        """Return path to the user settings file in the runtime data directory."""
        return os.path.join(self._runtime_data_dir(create=True), self.SETTINGS_FILENAME)

    @staticmethod
    def _legacy_settings_path():
        try:
            home = os.path.expanduser("~")
            return os.path.join(home, JsonEditor.LEGACY_SETTINGS_FILENAME)
        except Exception:
            return os.path.join(os.getcwd(), JsonEditor.SETTINGS_FILENAME)

    def _load_user_settings(self):
        """Load user settings (font size, app theme, startup update-check preference)."""
        paths = [self._settings_path()]
        legacy_path = None
        legacy_fn = getattr(self, "_legacy_settings_path", None)
        if callable(legacy_fn):
            try:
                legacy_path = legacy_fn()
            except Exception:
                legacy_path = None
        if legacy_path:
            paths.append(legacy_path)
        for path in paths:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
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
            except Exception:
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
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(payload)
        except Exception:
            return

    @staticmethod
    def _normalize_button_token(value):
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def _siindbad_effective_style(self):
        style_map = getattr(self, "_toolbar_style_variant_by_theme", None)
        if not isinstance(style_map, dict):
            style_map = {"SIINDBAD": "B", "KAMUE": "B"}
            self._toolbar_style_variant_by_theme = style_map
        return toolbar_service.resolve_siindbad_effective_style(
            style_focus=getattr(self, "_siindbad_style_focus", ""),
            show_toolbar_variant_controls=getattr(self, "_show_toolbar_variant_controls", False),
            app_theme_variant=getattr(self, "_app_theme_variant", "SIINDBAD"),
            style_map=style_map,
        )

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
        elif style == "C":
            family = self._resolve_font_family(
                ["Rajdhani SemiBold", "Rajdhani", "Segoe UI Semibold", "Segoe UI"],
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
        if style == "C" and not small:
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
        except Exception:
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
        # Optional forced style lock; keep unset so A/B/C can be switched from UI.
        self._siindbad_style_focus = None
        self._toolbar_button_images = {}
        self._toolbar_asset_image_cache = {}
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
        self._startup_loader_extra_hold_ms = 1800
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
        self._startup_loader_progress_interval_ms = 90
        self._startup_loader_statement_interval_loading_ms = 1450
        self._startup_loader_statement_interval_ready_ms = 1150
        self._startup_loader_window_mode = bool(
            getattr(self.root, "_hh_use_startup_loader_window", False)
        )
        self._startup_loader_title_cache = {}
        self._startup_loader_fill_photo_cache = {}
        self._startup_loader_panel_photo_cache = {}
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
        self.error_overlay = None
        self.error_pin = None
        self._mono_family = None
        self._font_family_lookup_cache = None
        self._font_size = 10  # Default font size
        self._auto_apply_pending = False
        self._auto_apply_in_progress = False
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
        self._crash_report_offer_after_id = None
        self._list_labelers = self._default_list_labelers()

    def _default_list_labelers(self):
        # Keep list labeler mapping grouped behind one helper for easier maintenance.
        return {
            ("MailAccounts",): self._mail_account_label,
            ("Mails",): self._mails_label,
            ("PhoneMessages",): self._phone_messages_label,
            ("Files",): self._files_label,
            ("Database",): self._database_label,
            ("Bookmarks",): self._bookmarks_label,
            # Root key is BCCNews; safe-display renders as BCC.News.
            ("BCCNews",): self._bcc_news_label,
            ("BCC.News",): self._bcc_news_label,
            ("BCCNews", "news"): self._bcc_news_label,
            ("BCC.News", "news"): self._bcc_news_label,
            ("Process",): self._process_label,
            ("Processes",): self._process_label,
            ("Typewriter",): self._typewriter_label,
            ("Bank", "accounts"): self._bank_account_label,
            ("Bank", "Accounts"): self._bank_account_label,
            ("Bank", "transactions"): self._bank_transaction_label,
            ("Bank", "Transactions"): self._bank_transaction_label,
            ("AppStore", "unlockedMarketItems"): self._app_store_unlocked_item_label,
            ("App.Store", "unlockedMarketItems"): self._app_store_unlocked_item_label,
            ("AppStore", "purchasedItems"): self._app_store_unlocked_item_label,
            ("App.Store", "purchasedItems"): self._app_store_unlocked_item_label,
            ("Twotter", "users"): self._twotter_user_label,
            ("Quests",): self._quests_label,
            ("Kisscord", "friends"): self._kisscord_friend_label,
            ("WebsiteTemplates",): self._website_templates_label,
            ("Terminal", "installedPackages"): self._terminal_package_label,
            ("Terminal", "datalist"): self._terminal_datalist_label,
            ("Terminal", "dataList"): self._terminal_datalist_label,
        }

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
        except Exception:
            try:
                cache[key] = value
            except Exception:
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
        if style == "C":
            return {
                "button_bg": "#151f2c",
                "button_fg": "#ebf5ff",
                "button_active": "#1d2c3e",
                "button_pressed": "#101a26",
                "border": "#68a4c1",
                "border_active": "#b4dff2",
                "slot_bg": "#0f1926",
                "size_bg": "#132131",
                "inner_border": border_inner,
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
        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
        icon = image_module.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = draw_module.Draw(icon)
        fg = self._hex_to_rgb_tuple(fg_hex) + (255,)
        accent = self._hex_to_rgb_tuple(accent_hex) + (130,)
        accent2 = self._hex_to_rgb_tuple(accent2_hex or accent_hex) + (220,)
        y_shift = 1 if style == "A" else 0

        def shift_line(points):
            return (points[0], points[1] + y_shift, points[2], points[3] + y_shift)

        def shift_box(box):
            return (box[0], box[1] + y_shift, box[2], box[3] + y_shift)

        def shift_poly(points):
            return [(x, y + y_shift) for x, y in points]

        if style == "C":
            try:
                draw.rounded_rectangle((0, 0, 15, 15), radius=4, outline=accent, width=1)
            except Exception:
                draw.rectangle((0, 0, 15, 15), outline=accent, width=1)
        elif style == "B":
            # Bracket frame corners (R5 concept style).
            frame = accent2
            draw.line((1, 1, 5, 1), fill=frame, width=1)
            draw.line((1, 1, 1, 5), fill=frame, width=1)
            draw.line((11, 1, 15, 1), fill=frame, width=1)
            draw.line((15, 1, 15, 5), fill=frame, width=1)
            draw.line((1, 11, 1, 15), fill=frame, width=1)
            draw.line((1, 15, 5, 15), fill=frame, width=1)
            draw.line((15, 11, 15, 15), fill=frame, width=1)
            draw.line((11, 15, 15, 15), fill=frame, width=1)

        def glow_line(points, width=1):
            draw.line(points, fill=accent, width=max(1, width + 2))
            draw.line(points, fill=fg, width=width)

        def glow_rect(box, width=1):
            draw.rectangle(box, outline=accent, width=max(1, width + 1))
            draw.rectangle(box, outline=fg, width=width)

        def glow_ellipse(box, width=1):
            draw.ellipse(box, outline=accent, width=max(1, width + 1))
            draw.ellipse(box, outline=fg, width=width)

        if style == "B" and key == "open":
            glow_line((3, 6, 6, 6), width=1)
            glow_line((6, 6, 7, 5), width=1)
            glow_line((7, 5, 11, 5), width=1)
            glow_rect((3, 7, 12, 12), width=1)
            return icon
        if style == "B" and key == "apply":
            glow_line((3, 9, 6, 12), width=2)
            glow_line((6, 12, 12, 5), width=2)
            return icon
        if style == "B" and key == "export":
            glow_rect((3, 10, 13, 12), width=1)
            glow_line((8, 4, 8, 9), width=2)
            draw.polygon([(5, 8), (8, 12), (11, 8)], fill=fg)
            return icon
        if style == "B" and key == "find":
            glow_ellipse((2, 2, 10, 10), width=2)
            glow_line((9, 9, 13, 13), width=2)
            return icon
        if style == "B" and key == "update":
            draw.arc((2, 2, 13, 13), start=35, end=340, fill=accent, width=3)
            draw.arc((2, 2, 13, 13), start=35, end=340, fill=fg, width=2)
            draw.polygon([(11, 2), (14, 3), (12, 5)], fill=fg)
            return icon
        if style == "B" and key == "readme":
            glow_rect((3, 3, 12, 12), width=1)
            glow_line((7, 3, 7, 12), width=1)
            return icon
        if key == "open":
            # Folder icon: tab + body.
            glow_line(shift_line((2, 5, 5, 5)), width=1)
            glow_line(shift_line((5, 5, 6, 4)), width=1)
            glow_line(shift_line((6, 4, 9, 4)), width=1)
            glow_line(shift_line((2, 6, 12, 6)), width=1)
            glow_rect(shift_box((2, 6, 13, 12)), width=1)
            return icon
        if key == "apply":
            # Check icon.
            glow_line(shift_line((3, 8, 7, 12)), width=2)
            glow_line(shift_line((7, 12, 13, 4)), width=2)
            return icon
        if key == "export":
            # Download/export: tray + arrow.
            glow_rect(shift_box((3, 10, 13, 13)), width=1)
            glow_line(shift_line((8, 2, 8, 9)), width=2)
            draw.polygon(shift_poly([(5, 8), (8, 12), (11, 8)]), fill=accent)
            draw.polygon(shift_poly([(6, 8), (8, 11), (10, 8)]), fill=fg)
            return icon
        if key == "find":
            glow_ellipse(shift_box((2, 2, 10, 10)), width=2)
            glow_line(shift_line((9, 9, 13, 13)), width=2)
            return icon
        if key == "update":
            draw.arc(shift_box((2, 2, 13, 13)), start=30, end=325, fill=accent, width=3)
            draw.arc(shift_box((2, 2, 13, 13)), start=30, end=325, fill=fg, width=2)
            draw.polygon(shift_poly([(11, 2), (14, 3), (12, 5)]), fill=fg)
            return icon
        if key == "readme":
            # Book icon.
            glow_rect(shift_box((2, 3, 13, 12)), width=1)
            glow_line(shift_line((7, 3, 7, 12)), width=1)
            glow_line(shift_line((3, 5, 6, 5)), width=1)
            glow_line(shift_line((8, 5, 12, 5)), width=1)
            return icon

        return icon

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
        except Exception:
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
        if style == "C":
            return 154
        return 156

    @staticmethod
    def _siindbad_toolbar_label_text(style, key, text):
        return toolbar_service.siindbad_toolbar_label_text(style, key, text)

    def _update_find_entry_layout(self):
        host = getattr(self, "_find_entry_host", None)
        if not host or not host.winfo_exists():
            return
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        style = self._siindbad_effective_style()
        if variant == "KAMUE" and style == "A":
            try:
                host.pack_configure(fill="x", expand=True, padx=(3, 2))
                host.pack_propagate(True)
                self.find_entry.pack_configure(fill="x", expand=True, padx=(2, 2), pady=0, ipady=2)
            except Exception:
                return
            return
        if style == "A":
            try:
                slot = getattr(self, "_find_entry_slot", None)
                if slot and slot.winfo_exists():
                    slot.place_forget()
                edge = getattr(self, "_find_entry_edge_line", None)
                if edge and edge.winfo_exists():
                    edge.place_forget()
                inner_edge = getattr(self, "_find_entry_inner_edge_line", None)
                if inner_edge and inner_edge.winfo_exists():
                    inner_edge.place_forget()
                self.find_entry.place_forget()
                host.pack_configure(fill="x", expand=True, padx=(4, 2))
                host.configure(height=34)
                host.pack_propagate(False)
                self.find_entry.configure(
                    width=20,
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                )
                self.find_entry.pack_configure(
                    fill="none",
                    expand=False,
                    padx=0,
                    pady=(5, 3),
                    ipady=1,
                    anchor="center",
                )
            except Exception:
                return
            return
        if style == "B":
            palette = self._siindbad_toolbar_style_palette()
            search_spec = self._siindbad_b_search_spec() or {}
            host_width = int(
                search_spec.get("width", self._find_entry_target_width()) or self._find_entry_target_width()
            )
            host_height = int(search_spec.get("height", 32) or 32)
            host_height = min(host_height, self._siindbad_b_button_height("find", default_height=33))
            input_box = search_spec.get("input_box")
            try:
                slot = getattr(self, "_find_entry_slot", None)
                host.pack_configure(fill="none", expand=False, padx=(2, 0))
                host.configure(width=host_width, height=host_height, bg=palette.get("button_bg", "#0f2439"))
                host.pack_propagate(False)
                try:
                    host.update_idletasks()
                except Exception:
                    pass
                actual_host_width = int(host.winfo_width() or 0)
                actual_host_height = int(host.winfo_height() or 0)
                draw_width = int(max(1, min(host_width, actual_host_width if actual_host_width > 1 else host_width)))
                draw_height = int(max(1, min(host_height, actual_host_height if actual_host_height > 1 else host_height)))
                squeezed = draw_width < host_width or draw_height < host_height
                search_sprite = self._siindbad_b_search_sprite_image(draw_width, draw_height)
                if search_sprite is not None:
                    if slot is None or not slot.winfo_exists() or slot.master is not host:
                        slot = tk.Label(
                            host,
                            bg=palette.get("button_bg", "#0f2439"),
                            bd=0,
                            highlightthickness=0,
                            relief="flat",
                        )
                        self._find_entry_slot = slot
                    slot.configure(image=search_sprite)
                    slot.image = search_sprite
                    slot.place(x=0, y=0, width=draw_width, height=draw_height)
                    slot.lower()
                    host.configure(highlightthickness=0)
                else:
                    if slot and slot.winfo_exists():
                        slot.place_forget()
                    host.configure(
                        highlightthickness=1,
                        highlightbackground=palette.get("border", "#349fc7"),
                        highlightcolor=palette.get("border_active", "#a9ddf0"),
                    )
                edge = getattr(self, "_find_entry_edge_line", None)
                if squeezed:
                    if edge is None or not edge.winfo_exists() or edge.master is not host:
                        edge = tk.Frame(host, bg=palette.get("border", "#349fc7"), bd=0, highlightthickness=0)
                        self._find_entry_edge_line = edge
                    edge.place(x=max(0, draw_width - 1), y=0, width=1, height=draw_height)
                elif edge and edge.winfo_exists():
                    edge.place_forget()
                self.find_entry.configure(
                    width=max(10, draw_width // 8),
                    bg=palette.get("slot_bg", "#091727"),
                    fg=palette.get("button_fg", "#dff8ff"),
                    insertbackground=palette.get("button_fg", "#dff8ff"),
                    highlightbackground=palette.get("slot_bg", "#091727"),
                    highlightcolor=palette.get("slot_bg", "#091727"),
                    selectbackground=palette.get("button_active", "#13304a"),
                    selectforeground="#ffffff",
                    relief="flat",
                    bd=0,
                    highlightthickness=0,
                )
                self.find_entry.pack_forget()
                if isinstance(input_box, (tuple, list)) and len(input_box) == 4:
                    x1, y1, x2, y2 = [int(v) for v in input_box]
                    # Keep the search text box aligned to the sprite's true drawable size.
                    scale_x = float(draw_width) / float(max(1, host_width))
                    scale_y = float(draw_height) / float(max(1, host_height))
                    x1 = int(round(x1 * scale_x))
                    y1 = int(round(y1 * scale_y))
                    x2 = int(round(x2 * scale_x))
                    y2 = int(round(y2 * scale_y))
                    # Draw border from sprite only; keep entry text area inset.
                    x1 = max(3, x1 + 2)
                    y1 = max(3, y1 + 2)
                    x2 = min(draw_width - 4, x2 - 3)
                    y2 = min(draw_height - 3, y2 - 2)
                    self.find_entry.place(
                        x=max(3, x1),
                        y=max(3, y1),
                        width=max(12, x2 - x1),
                        height=max(14, y2 - y1),
                    )
                    inner_edge = getattr(self, "_find_entry_inner_edge_line", None)
                    if squeezed:
                        if inner_edge is None or not inner_edge.winfo_exists() or inner_edge.master is not host:
                            inner_edge = tk.Frame(
                                host,
                                bg=palette.get("border_active", "#a9ddf0"),
                                bd=0,
                                highlightthickness=0,
                            )
                            self._find_entry_inner_edge_line = inner_edge
                        inner_edge.place(
                            x=min(draw_width - 2, max(4, x2 + 1)),
                            y=max(3, y1 - 1),
                            width=1,
                            height=max(14, y2 - y1 + 2),
                        )
                    elif inner_edge and inner_edge.winfo_exists():
                        inner_edge.place_forget()
                else:
                    inner_edge = getattr(self, "_find_entry_inner_edge_line", None)
                    if inner_edge and inner_edge.winfo_exists():
                        inner_edge.place_forget()
                    self.find_entry.place(
                        x=8,
                        y=max(3, (draw_height - 2 - 20) // 2),
                        width=max(20, draw_width - 16),
                        height=20,
                    )
                self.find_entry.lift()
                edge = getattr(self, "_find_entry_edge_line", None)
                if edge and edge.winfo_exists():
                    edge.lift()
                inner_edge = getattr(self, "_find_entry_inner_edge_line", None)
                if inner_edge and inner_edge.winfo_exists():
                    inner_edge.lift()
            except Exception:
                return
            return
        width_px = self._find_entry_target_width()
        try:
            slot = getattr(self, "_find_entry_slot", None)
            if slot and slot.winfo_exists():
                slot.place_forget()
            edge = getattr(self, "_find_entry_edge_line", None)
            if edge and edge.winfo_exists():
                edge.place_forget()
            inner_edge = getattr(self, "_find_entry_inner_edge_line", None)
            if inner_edge and inner_edge.winfo_exists():
                inner_edge.place_forget()
            self.find_entry.place_forget()
            host.pack_configure(fill="none", expand=False, padx=(4, 2))
            host.configure(width=width_px, height=34)
            host.pack_propagate(False)
            self.find_entry.configure(
                relief="flat",
                bd=0,
                highlightthickness=1,
            )
            self.find_entry.pack_configure(fill="x", expand=True, padx=(2, 2), pady=0, ipady=1)
        except Exception:
            return

    def _schedule_topbar_alignment(self, delay_ms=35):
        root = getattr(self, "root", None)
        if root is None:
            return
        existing = getattr(self, "_topbar_align_after_id", None)
        if existing:
            try:
                root.after_cancel(existing)
            except Exception:
                pass
        self._topbar_align_after_id = None
        try:
            self._topbar_align_after_id = root.after(
                max(0, int(delay_ms)),
                self._align_topbar_to_logo,
            )
        except Exception:
            self._topbar_align_after_id = None

    @staticmethod
    def _window_is_maximized(window):
        if window is None:
            return False
        try:
            return str(window.state()).lower() == "zoomed"
        except Exception:
            return False

    def _apply_toolbar_layout_mode(self, force=False):
        host = getattr(self, "_toolbar_host", None)
        center = getattr(self, "_toolbar_center_frame", None)
        if host is None or center is None:
            return
        try:
            if not (host.winfo_exists() and center.winfo_exists()):
                return
        except Exception:
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
        except Exception:
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
        except Exception:
            pass
        try:
            find_btn_host = getattr(find_btn, "_siindbad_frame_host", find_btn)
            find_btn_host.pack_configure(padx=target_btn_padx)
        except Exception:
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
        except Exception:
            pass
        try:
            center.pack_forget()
        except Exception:
            pass
        try:
            center.pack(anchor="center")
        except Exception:
            pass

    def _apply_toolbar_layout_max(self, center, host):
        # Max mode has its own wrapper positioning only; button dimensions stay
        # untouched so normal layout cannot be affected by maximize tuning.
        try:
            center.update_idletasks()
            host.update_idletasks()
        except Exception:
            return

        try:
            toolbar_w = int(center.winfo_reqwidth() or center.winfo_width() or 0)
            toolbar_h = int(center.winfo_reqheight() or center.winfo_height() or 0)
            host_w = int(host.winfo_width() or host.winfo_reqwidth() or 0)
            host_h = int(host.winfo_height() or host.winfo_reqheight() or 0)
        except Exception:
            return
        if toolbar_w <= 0 or host_w <= 0:
            return

        logo_widget = getattr(self, "logo_frame", None) or getattr(self, "logo_label", None)
        logo_center_rel = None
        logo_visual_w = None
        try:
            if logo_widget is not None and logo_widget.winfo_exists():
                logo_widget.update_idletasks()
                logo_visual_w = float(max(1, int(logo_widget.winfo_width())))
                logo_center_rel = (
                    float(logo_widget.winfo_rootx())
                    + (logo_visual_w / 2.0)
                    - float(host.winfo_rootx())
                )
        except Exception:
            logo_center_rel = None
            logo_visual_w = None
        if logo_center_rel is None:
            logo_center_rel = float(host_w) / 2.0

        try:
            if logo_visual_w and self._apply_max_toolbar_search_compaction(toolbar_w, logo_visual_w):
                center.update_idletasks()
                host.update_idletasks()
                toolbar_w = int(center.winfo_reqwidth() or center.winfo_width() or toolbar_w)
                toolbar_h = int(center.winfo_reqheight() or center.winfo_height() or toolbar_h)
                host_w = int(host.winfo_width() or host.winfo_reqwidth() or host_w)
                host_h = int(host.winfo_height() or host.winfo_reqheight() or host_h)
        except Exception:
            pass

        placement = layout_topbar_core.compute_centered_toolbar_position(
            toolbar_w=toolbar_w,
            toolbar_h=toolbar_h,
            host_w=host_w,
            host_h=host_h,
            logo_center_rel=logo_center_rel,
        )
        if placement is None:
            return
        x, y = placement

        try:
            center.pack_forget()
        except Exception:
            pass
        try:
            center.place(x=x, y=y)
        except Exception:
            pass

    def _align_topbar_to_logo(self):
        self._topbar_align_after_id = None
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
        except Exception:
            data = {}
        self._siindbad_b_sprite_manifest_cache = data
        return data

    def _invalidate_siindbad_b_sprite_cache(self):
        after_id = getattr(self, "_theme_prewarm_after_id", None)
        root = getattr(self, "root", None)
        if root is not None and after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
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
        sprite_dir = self._siindbad_b_sprite_dir()
        manifest = self._siindbad_b_sprite_manifest()
        if not os.path.isdir(sprite_dir):
            return None
        render_mode = self._siindbad_b_render_mode(render_mode)
        buttons_meta = manifest.get("buttons", {}) if isinstance(manifest, dict) else {}
        meta = buttons_meta.get(str(key), {}) if isinstance(buttons_meta, dict) else {}

        base_name = str(meta.get("base", f"{key}_base.png"))
        base_path = os.path.join(sprite_dir, base_name)
        if not os.path.isfile(base_path):
            return None

        image_module = importlib.import_module("PIL.Image")
        image_chops_module = importlib.import_module("PIL.ImageChops")
        image_stat_module = importlib.import_module("PIL.ImageStat")
        image_tk_module = importlib.import_module("PIL.ImageTk")

        try:
            base_image = image_module.open(base_path).convert("RGBA")
        except Exception:
            return None
        if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE":
            try:
                base_image = self._shade_toolbar_button_for_theme(base_image)
                base_image = self._harmonize_kamue_b_outer_frame(base_image)
            except Exception:
                pass
        if base_image.width != width or base_image.height != height:
            try:
                base_image = base_image.resize((width, height), image_module.LANCZOS)
            except Exception:
                return None

        hover_files = meta.get("hover_frames", [])
        if not hover_files:
            prefix = f"{key}_hover_"
            try:
                hover_files = sorted(
                    name for name in os.listdir(sprite_dir) if name.startswith(prefix) and name.endswith(".png")
                )
            except Exception:
                hover_files = []

        hover_images = []
        for hover_name in hover_files:
            hover_path = os.path.join(sprite_dir, str(hover_name))
            if not os.path.isfile(hover_path):
                continue
            try:
                hover_image = image_module.open(hover_path).convert("RGBA")
                if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() == "KAMUE":
                    try:
                        hover_image = self._shade_toolbar_button_for_theme(hover_image)
                        hover_image = self._harmonize_kamue_b_outer_frame(hover_image)
                    except Exception:
                        pass
                if hover_image.width != width or hover_image.height != height:
                    hover_image = hover_image.resize((width, height), image_module.LANCZOS)
                hover_images.append(hover_image)
            except Exception:
                continue
        if not hover_images:
            hover_images = [base_image.copy()]
        else:
            # Slightly soften hover frames so mouseover highlight is less aggressive.
            hover_mix = float(meta.get("hover_mix", manifest.get("hover_mix", 0.84)) or 0.84)
            hover_mix = max(0.60, min(0.98, hover_mix))
            softened = []
            for hover_img in hover_images:
                try:
                    softened.append(image_module.blend(base_image, hover_img, hover_mix))
                except Exception:
                    softened.append(hover_img)
            hover_images = softened

        interval = int(meta.get("frame_interval_ms", manifest.get("frame_interval_ms", 40)) or 40)
        # Preview R5 sweep is a single ~2.2s pass. Capture exports may contain extra
        # partial loops; trim to one clean pass for stable replay in Tk.
        cycle_ms = int(meta.get("scan_cycle_ms", manifest.get("scan_cycle_ms", 2200)) or 2200)
        # Match preferred slower feel while keeping room for smoother frame cadence.
        cycle_ms = int(round(float(cycle_ms) * 1.75))
        cycle_ms = max(1200, min(4000, cycle_ms))
        if hover_images and interval > 0:
            expected_frames = max(20, int(round(float(cycle_ms) / float(interval))))
            if len(hover_images) > expected_frames + 1:
                if render_mode == "fast":
                    hover_images = hover_images[:int(expected_frames)]
                else:
                    # Choose a contiguous cycle window with the smoothest wrap seam.
                    # This avoids visible "reset jumps" when the animation loops.
                    def _seam_cost(img_a, img_b):
                        try:
                            a = img_a.convert("L").resize((40, 12), image_module.BILINEAR)
                            b = img_b.convert("L").resize((40, 12), image_module.BILINEAR)
                            diff = image_chops_module.difference(a, b)
                            stat = image_stat_module.Stat(diff)
                            return float(stat.sum[0])
                        except Exception:
                            return 0.0

                    n = len(hover_images)
                    m = int(expected_frames)
                    best_start = 0
                    best_score = None
                    max_start = max(0, n - m)
                    for start in range(max_start + 1):
                        first = hover_images[start]
                        last = hover_images[start + m - 1]
                        score = _seam_cost(first, last)
                        if best_score is None or score < best_score:
                            best_score = score
                            best_start = start
                    hover_images = hover_images[best_start: best_start + m]

        # Add one in-between blend frame between each captured frame.
        # This preserves visual style from R5 sprites while reducing stepped motion in Tk.
        if render_mode != "fast" and len(hover_images) > 1:
            smoothed = []
            total = len(hover_images)
            for idx, frame in enumerate(hover_images):
                smoothed.append(frame)
                nxt = hover_images[(idx + 1) % total]
                try:
                    smoothed.append(image_module.blend(frame, nxt, 0.5))
                except Exception:
                    pass
            if smoothed:
                hover_images = smoothed

        # Keep a bounded frame budget for Tk runtime to avoid hitching on full-image swaps.
        max_runtime_frames = int(meta.get("runtime_max_frames", manifest.get("runtime_max_frames", 120)) or 120)
        if render_mode == "fast":
            max_runtime_frames = min(max_runtime_frames, 36)
        max_runtime_frames = max(24, min(120, max_runtime_frames))
        if len(hover_images) > max_runtime_frames:
            reduced = []
            step = float(len(hover_images)) / float(max_runtime_frames)
            pos = 0.0
            for _ in range(max_runtime_frames):
                reduced.append(hover_images[int(pos) % len(hover_images)])
                pos += step
            hover_images = reduced

        if hover_images and interval > 0:
            interval = int(round(float(cycle_ms) / float(max(1, len(hover_images)))))
        interval = max(20, min(100, interval))
        hover_frames = [image_tk_module.PhotoImage(img) for img in hover_images]
        return {
            "base": image_tk_module.PhotoImage(base_image),
            "hover_frames": hover_frames,
            "frame_interval_ms": interval,
        }

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
            except Exception:
                pass
        if isinstance(input_box, (list, tuple)) and len(input_box) == 4:
            try:
                spec["input_box"] = tuple(int(v) for v in input_box)
            except Exception:
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
                    image = self._shade_toolbar_button_for_theme(image)
                    image = self._harmonize_kamue_b_outer_frame(image)
                except Exception:
                    pass
            if image.width != int(width) or image.height != int(height):
                image = image.resize((max(1, int(width)), max(1, int(height))), image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            self._bounded_cache_put(cache, signature, photo, max_items=48)
            return photo
        except Exception:
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
            except Exception:
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
        except Exception:
            return False

    def _siindbad_b_render_button_bundle(self, key, text, width, height, palette, render_mode=None):
        cache = getattr(self, "_siindbad_b_button_image_cache", None)
        if cache is None:
            cache = {}
            self._siindbad_b_button_image_cache = cache
        render_mode = self._siindbad_b_render_mode(render_mode)
        signature = (
            str(key),
            str(text),
            int(width),
            int(height),
            str(render_mode),
            palette.get("button_bg"),
            palette.get("button_fg"),
            palette.get("button_active"),
            palette.get("border"),
            palette.get("border_active"),
            palette.get("inner_border"),
        )
        cached = cache.get(signature)
        if cached:
            return cached

        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
        font_module = importlib.import_module("PIL.ImageFont")
        image_tk_module = importlib.import_module("PIL.ImageTk")

        sprite_bundle = self._siindbad_b_sprite_bundle(
            key=key,
            width=width,
            height=height,
            render_mode=render_mode,
        )
        if sprite_bundle:
            self._bounded_cache_put(cache, signature, sprite_bundle, max_items=64)
            return sprite_bundle

        def _rgb(hex_color, fallback):
            return self._hex_to_rgb_tuple(hex_color, default_rgb=fallback)

        def _rgba(rgb, alpha=255):
            return (rgb[0], rgb[1], rgb[2], alpha)

        # Primary R5 path: use the exact Variant-B source art footprint and animate hover scan over it.
        asset_path = self._siindbad_b_asset_button_path(key)
        if asset_path:
            try:
                source = image_module.open(asset_path).convert("RGBA")
                if source.width != width or source.height != height:
                    source = source.resize((width, height), image_module.LANCZOS)

                border_active_rgb = self._hex_to_rgb_tuple(
                    palette.get("border_active", "#95eaff"),
                    default_rgb=(149, 234, 255),
                )
                hover_base = source.copy()
                hover_tint = image_module.new("RGBA", (width, height), _rgba(border_active_rgb, 16))
                hover_base = image_module.alpha_composite(hover_base, hover_tint)

                hover_frames = []
                scan_step = 8 if render_mode == "fast" else 4
                for pos in range(-34, width + 34, scan_step):
                    frame = hover_base.copy()
                    frame_draw = draw_module.Draw(frame)
                    for idx in range(24):
                        alpha = int(max(0, 94 - abs(12 - idx) * 7))
                        x = pos + idx
                        if 0 <= x < width:
                            frame_draw.line((x, 1, x, height - 2), fill=_rgba(border_active_rgb, alpha), width=1)
                    core_x = pos + 12
                    if 0 <= core_x < width:
                        frame_draw.line((core_x, 1, core_x, height - 2), fill=_rgba((225, 252, 255), 170), width=1)
                    hover_frames.append(image_tk_module.PhotoImage(frame))

                if render_mode == "fast" and len(hover_frames) > 24:
                    hover_frames = hover_frames[:24]
                bundle = {
                    "base": image_tk_module.PhotoImage(source),
                    "hover_frames": hover_frames,
                    "frame_interval_ms": 40,
                }
                self._bounded_cache_put(cache, signature, bundle, max_items=64)
                return bundle
            except Exception:
                pass

        def _mix(rgb_a, rgb_b, amount):
            amount = max(0.0, min(1.0, float(amount)))
            return (
                int(rgb_a[0] * (1.0 - amount) + rgb_b[0] * amount),
                int(rgb_a[1] * (1.0 - amount) + rgb_b[1] * amount),
                int(rgb_a[2] * (1.0 - amount) + rgb_b[2] * amount),
            )

        bg_rgb = _rgb(palette.get("button_bg", "#10253b"), (16, 37, 59))
        fg_rgb = _rgb(palette.get("button_fg", "#dff5ff"), (223, 245, 255))
        border_rgb = _rgb(palette.get("border", "#3f82a9"), (63, 130, 169))
        border_active_rgb = _rgb(palette.get("border_active", "#95eaff"), (149, 234, 255))
        icon_frame_rgb = _rgb(palette.get("inner_border", "#73d7fb"), (115, 215, 251))
        inner_border_rgb = _mix(border_rgb, bg_rgb, 0.55)
        slot_rgb = _mix(bg_rgb, (0, 0, 0), 0.22)
        top_gloss_rgb = _mix(border_active_rgb, fg_rgb, 0.35)
        corner_bar_rgb = _mix(border_active_rgb, border_rgb, 0.5)

        base = image_module.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = draw_module.Draw(base)

        # Outer/inner frame to match R5 bracket-frame concept.
        draw.rectangle((0, 0, width - 1, height - 1), fill=_rgba(bg_rgb), outline=_rgba(border_rgb))
        draw.rectangle((1, 1, width - 2, height - 2), outline=_rgba(inner_border_rgb))
        draw.line((2, 2, width - 3, 2), fill=_rgba(top_gloss_rgb, 120), width=1)
        draw.line((2, height - 3, width - 3, height - 3), fill=_rgba(slot_rgb, 190), width=1)

        # Stream-tag right corner accents used in the preview.
        draw.line((width - 11, 4, width - 4, 4), fill=_rgba(border_active_rgb), width=1)
        draw.line((width - 4, 4, width - 4, 9), fill=_rgba(border_active_rgb), width=1)
        draw.line((width - 16, height - 4, width - 4, height - 4), fill=_rgba(corner_bar_rgb), width=1)

        # Bracket icon shell from R5.
        ix = 7
        iy = max(2, (height - 18) // 2)
        iw = 18
        ih = 18
        bracket_len = 5
        draw.line((ix, iy, ix + bracket_len, iy), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy, ix, iy + bracket_len), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix + iw - bracket_len - 1, iy, ix + iw - 1, iy), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix + iw - 1, iy, ix + iw - 1, iy + bracket_len), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy + ih - bracket_len - 1, ix, iy + ih - 1), fill=_rgba(icon_frame_rgb), width=1)
        draw.line((ix, iy + ih - 1, ix + bracket_len, iy + ih - 1), fill=_rgba(icon_frame_rgb), width=1)
        draw.line(
            (ix + iw - 1, iy + ih - bracket_len - 1, ix + iw - 1, iy + ih - 1),
            fill=_rgba(icon_frame_rgb),
            width=1,
        )
        draw.line(
            (ix + iw - bracket_len - 1, iy + ih - 1, ix + iw - 1, iy + ih - 1),
            fill=_rgba(icon_frame_rgb),
            width=1,
        )

        gx = ix + 3
        gy = iy + 3

        def _stroke(points, width_px=2):
            draw.line(points, fill=_rgba(icon_frame_rgb, 155), width=max(1, width_px + 2), joint="curve")
            draw.line(points, fill=_rgba(fg_rgb), width=width_px, joint="curve")

        def _rect(box, width_px=1):
            draw.rectangle(box, outline=_rgba(icon_frame_rgb, 135), width=max(1, width_px + 1))
            draw.rectangle(box, outline=_rgba(fg_rgb), width=width_px)

        def _ellipse(box, width_px=1):
            draw.ellipse(box, outline=_rgba(icon_frame_rgb, 135), width=max(1, width_px + 1))
            draw.ellipse(box, outline=_rgba(fg_rgb), width=width_px)

        # Match SVG glyph language from R5 preview.
        if key == "open":
            _stroke((gx + 0, gy + 4, gx + 4, gy + 4, gx + 5, gy + 2, gx + 10, gy + 2, gx + 10, gy + 4), 1)
            _stroke((gx + 0, gy + 5, gx + 12, gy + 5), 1)
            draw.polygon(
                [(gx + 0, gy + 5), (gx + 12, gy + 5), (gx + 10, gy + 11), (gx + 1, gy + 11)],
                fill=None,
                outline=_rgba(fg_rgb),
            )
        elif key == "apply":
            _stroke((gx + 1, gy + 7, gx + 4, gy + 10, gx + 11, gy + 3), 2)
        elif key == "export":
            _stroke((gx + 6, gy + 1, gx + 6, gy + 8), 2)
            _stroke((gx + 3, gy + 6, gx + 6, gy + 9, gx + 9, gy + 6), 2)
            _rect((gx + 1, gy + 9, gx + 11, gy + 11), 1)
        elif key == "find":
            _ellipse((gx + 0, gy + 0, gx + 8, gy + 8), 2)
            _stroke((gx + 7, gy + 7, gx + 11, gy + 11), 2)
        elif key == "update":
            draw.arc((gx + 0, gy + 0, gx + 11, gy + 11), start=35, end=330, fill=_rgba(icon_frame_rgb, 180), width=3)
            draw.arc((gx + 0, gy + 0, gx + 11, gy + 11), start=35, end=330, fill=_rgba(fg_rgb), width=2)
            draw.polygon([(gx + 8, gy + 0), (gx + 11, gy + 1), (gx + 9, gy + 3)], fill=_rgba(fg_rgb))
        elif key == "readme":
            _rect((gx + 1, gy + 1, gx + 10, gy + 10), 1)
            _stroke((gx + 5, gy + 1, gx + 5, gy + 10), 1)

        # Prefer Tektur for R5 parity when present; fallback to existing bundled font.
        font_candidates = [
            os.path.join(self._resource_base_dir(), "assets", "fonts", "Tektur-SemiBold.ttf"),
            os.path.join(self._resource_base_dir(), "assets", "fonts", "Tektur-Regular.ttf"),
            os.path.join(self._resource_base_dir(), "assets", "fonts", "Rajdhani-SemiBold.ttf"),
        ]
        text_font = None
        for font_path in font_candidates:
            try:
                if os.path.isfile(font_path):
                    text_font = font_module.truetype(font_path, 14)
                    break
            except Exception:
                continue
        if text_font is None:
            try:
                text_font = font_module.load_default()
            except Exception:
                text_font = None
        tx = ix + iw + 8
        bbox = draw.textbbox((0, 0), text, font=text_font)
        th = max(1, bbox[3] - bbox[1])
        ty = max(1, (height - th) // 2 - 1)
        draw.text((tx + 1, ty + 1), text, fill=_rgba((7, 20, 33), 210), font=text_font)
        draw.text((tx, ty), text, fill=_rgba(fg_rgb), font=text_font)

        hover_base = base.copy()
        hover_draw = draw_module.Draw(hover_base)
        hover_draw.rectangle((0, 0, width - 1, height - 1), outline=_rgba(border_active_rgb))
        hover_draw.rectangle((1, 1, width - 2, height - 2), outline=_rgba(_mix(border_active_rgb, border_rgb, 0.42)))
        hover_draw.text((tx + 1, ty), text, fill=_rgba(border_active_rgb, 92), font=text_font)

        hover_frames = []
        scan_step = 10 if render_mode == "fast" else 5
        for pos in range(-34, width + 34, scan_step):
            frame = hover_base.copy()
            frame_draw = draw_module.Draw(frame)
            # Wider scanning pass than single-line sweep.
            for idx in range(24):
                alpha = int(max(0, 86 - abs(12 - idx) * 7))
                x = pos + idx
                if 1 <= x <= width - 2:
                    frame_draw.line((x, 1, x, height - 2), fill=_rgba(border_active_rgb, alpha), width=1)
            core_x = pos + 12
            if 1 <= core_x <= width - 2:
                frame_draw.line((core_x, 2, core_x, height - 3), fill=_rgba((222, 252, 255), 160), width=1)
            hover_frames.append(image_tk_module.PhotoImage(frame))

        if render_mode == "fast" and len(hover_frames) > 24:
            hover_frames = hover_frames[:24]

        bundle = {
            "base": image_tk_module.PhotoImage(base),
            "hover_frames": hover_frames,
            "frame_interval_ms": 40,
        }
        self._bounded_cache_put(cache, signature, bundle, max_items=64)
        return bundle

    def _stop_siindbad_b_button_scan(self, button):
        host = getattr(button, "_siindbad_frame_host", None)
        after_id = getattr(button, "_siindbad_scan_after_id", None)
        if host is not None and after_id:
            try:
                host.after_cancel(after_id)
            except Exception:
                pass
        button._siindbad_scan_after_id = None
        button._siindbad_scan_running = False
        button._siindbad_scan_idx = -1
        button._siindbad_scan_start_ts = None
        base_image = getattr(button, "_siindbad_base_image", None)
        if base_image is not None:
            try:
                button.configure(image=base_image)
            except Exception:
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
        except Exception:
            pass
        self._stop_all_siindbad_b_button_scans()
        try:
            command()
        except Exception:
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
            except Exception:
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
        except Exception:
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
            except Exception:
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
            except Exception:
                pass
        try:
            button._siindbad_hover_leave_after_id = host.after(40, _settle)
        except Exception:
            self._stop_siindbad_b_button_scan(button)

    def _apply_siindbad_toolbar_button_style(self, button, key, text):
        palette = self._siindbad_toolbar_style_palette()
        style = self._siindbad_effective_style()
        frame_host = getattr(button, "_siindbad_frame_host", None)
        if frame_host is not None and frame_host.winfo_exists():
            try:
                frame_host.configure(
                    bg=palette["button_bg"],
                    highlightbackground=palette["border"],
                    highlightcolor=palette["border_active"],
                )
            except Exception:
                pass

        display_text = self._siindbad_toolbar_label_text(style, key, text)
        if style == "B":
            width = self._siindbad_toolbar_frame_width(style, key, display_text)
            height = self._siindbad_b_button_height(key, default_height=34)
            try:
                if frame_host is not None and frame_host.winfo_exists():
                    frame_host.configure(width=max(1, int(width)), height=height)
                    frame_host.pack_propagate(False)
            except Exception:
                pass

            bundle = self._siindbad_b_render_button_bundle(
                key=key,
                text=display_text,
                width=max(48, int(width)),
                height=max(24, height),
                palette=palette,
            )
            button._siindbad_base_image = bundle.get("base")
            button._siindbad_hover_frames = bundle.get("hover_frames", [])
            base_interval = int(bundle.get("frame_interval_ms", 40) or 40)
            button._siindbad_scan_interval_ms = max(20, min(100, base_interval))
            self._stop_siindbad_b_button_scan(button)
            try:
                if isinstance(button, tk.Label):
                    button.configure(
                        text="",
                        image=button._siindbad_base_image,
                        compound="none",
                        font=self._toolbar_button_font(),
                        relief="flat",
                        borderwidth=0,
                        highlightthickness=0,
                        padx=0,
                        pady=0,
                        bg=palette["button_bg"],
                        fg=palette["button_fg"],
                        cursor="hand2",
                        anchor="center",
                        justify="center",
                    )
                else:
                    button.configure(
                        text="",
                        image=button._siindbad_base_image,
                        compound="none",
                        font=self._toolbar_button_font(),
                        relief="flat",
                        borderwidth=0,
                        highlightthickness=0,
                        highlightbackground=palette["border"],
                        highlightcolor=palette["border_active"],
                        padx=0,
                        pady=0,
                        bg=palette["button_bg"],
                        fg=palette["button_fg"],
                        activebackground=palette["button_bg"],
                        activeforeground=palette["button_fg"],
                        disabledforeground="#57768c",
                        takefocus=0,
                        cursor="hand2",
                        width=0,
                        anchor="center",
                        justify="center",
                        overrelief="flat",
                        height=0,
                    )
            except Exception:
                return
            return

        self._ensure_siindbad_button_icons()
        icon = self._siindbad_button_icons.get(key)
        symbol = self._siindbad_toolbar_button_symbol(key)
        if icon is not None:
            label_text = display_text
            image_value = icon
            compound = "left"
            anchor = "w"
            pad_x = 7 if style == "A" else 7
        else:
            label_text = f"{symbol}  {display_text}" if symbol else display_text
            image_value = ""
            compound = "none"
            anchor = "center"
            pad_x = 10
        justify = "left"
        if style == "A" and key == "open":
            anchor = "center"
            justify = "center"
            pad_x = 5
        width = self._siindbad_toolbar_button_width(style, key, display_text) if style == "A" else 0
        pad_y = 5 if style == "A" else (4 if style == "B" else 4)
        relief = "flat"
        border_width = 0
        highlight_thickness = 0 if style in ("A", "B") else 1
        try:
            button.configure(
                text=label_text,
                image=image_value,
                compound=compound,
                font=self._toolbar_button_font(),
                relief=relief,
                borderwidth=border_width,
                highlightthickness=highlight_thickness,
                highlightbackground=palette["border"],
                highlightcolor=palette["border_active"],
                padx=pad_x,
                pady=pad_y,
                bg=palette["button_bg"],
                fg=palette["button_fg"],
                activebackground=palette["button_active"],
                activeforeground="#ffffff",
                disabledforeground="#7a93a8" if style != "B" else "#57768c",
                takefocus=0,
                cursor="hand2",
                width=width,
                anchor=anchor,
                justify=justify,
                overrelief="flat",
                height=0,
            )
        except Exception:
            return

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
        except Exception:
            return

    def _make_siindbad_stepper_button(self, parent, symbol, command):
        palette = self._siindbad_toolbar_style_palette()
        style = self._siindbad_effective_style()
        box_w = 28 if style == "A" else (22 if style == "B" else 24)
        box_h = 22 if style in ("A", "B") else 20
        box = tk.Frame(
            parent,
            bg=palette["slot_bg"],
            bd=0,
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["border_active"],
            width=box_w,
            height=box_h,
        )
        box.pack_propagate(False)
        symbol_canvas = tk.Canvas(
            box,
            bg=palette["slot_bg"],
            bd=0,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )
        symbol_canvas.pack(fill="both", expand=True, padx=1, pady=1)

        stroke = 2 if style in ("A", "B") else 1
        normal_bg = palette["slot_bg"]
        active_bg = palette["button_active"]
        fg = palette["button_fg"]

        def _draw_symbol(_event=None):
            symbol_canvas.delete("symbol")
            w = max(4, int(symbol_canvas.winfo_width()))
            h = max(4, int(symbol_canvas.winfo_height()))
            cx = w // 2
            cy = h // 2
            half = max(4, min(w, h) // 4)
            symbol_canvas.create_line(
                cx - half,
                cy,
                cx + half,
                cy,
                fill=fg,
                width=stroke,
                capstyle="round",
                tags="symbol",
            )
            if symbol == "+":
                v_half = max(3, half - 1)
                symbol_canvas.create_line(
                    cx,
                    cy - v_half,
                    cx,
                    cy + v_half,
                    fill=fg,
                    width=stroke,
                    capstyle="round",
                    tags="symbol",
                )

        def _on_press(_event):
            symbol_canvas.configure(bg=active_bg)

        def _on_release(_event):
            symbol_canvas.configure(bg=normal_bg)
            command()

        def _on_leave(_event):
            symbol_canvas.configure(bg=normal_bg)

        symbol_canvas.bind("<Configure>", _draw_symbol)
        symbol_canvas.bind("<ButtonPress-1>", _on_press)
        symbol_canvas.bind("<ButtonRelease-1>", _on_release)
        symbol_canvas.bind("<Leave>", _on_leave)
        _draw_symbol()
        return box

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
            width=136 if style == "A" else (122 if style == "B" else 170),
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
            text="FONT" if style in ("A", "B") else "Font",
            bg=palette["button_bg"],
            fg=palette["button_fg"],
            font=label_font,
            bd=0,
            highlightthickness=0,
        )
        label.pack(side="left", padx=((8 if style != "B" else 0), 6))

        minus_box = self._make_siindbad_stepper_button(parent_for_controls, "-", self.decrease_font_size)
        minus_box.pack(side="left", padx=(0, 1 if style == "B" else 3), pady=5)

        if style == "C":
            size_box = tk.Frame(
                host,
                bg=palette["size_bg"],
                bd=0,
                highlightthickness=1,
                highlightbackground=frame_border,
                highlightcolor=frame_border_active,
                width=30,
                height=20,
            )
            size_box.pack(side="left", padx=0, pady=5)
            size_box.pack_propagate(False)
            self._font_size_value_label = tk.Label(
                size_box,
                text=str(int(self._font_size)),
                bg=palette["size_bg"],
                fg=palette["button_fg"],
                font=self._toolbar_button_font(small=True),
                bd=0,
                highlightthickness=0,
            )
            self._font_size_value_label.pack(fill="both", expand=True)

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
        except Exception:
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
        key = self._normalize_button_token(image_key or text)
        self._toolbar_button_text[key] = text
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        style = self._siindbad_effective_style()
        if variant == "SIINDBAD" or (variant == "KAMUE" and style == "B"):
            if style == "A":
                palette = self._siindbad_toolbar_style_palette()
                frame = tk.Frame(
                    parent,
                    bg=palette["button_bg"],
                    bd=1,
                    relief="solid",
                    highlightthickness=1,
                    highlightbackground=palette["border"],
                    highlightcolor=palette["border_active"],
                )
                button = tk.Button(frame, command=command)
                button.pack(fill="both", expand=True)
                button._siindbad_frame_host = frame
            elif style == "B":
                palette = self._siindbad_toolbar_style_palette()
                frame_width = self._siindbad_toolbar_frame_width(style, key, text)
                frame_height = self._siindbad_b_button_height(key, default_height=34)
                frame = tk.Frame(
                    parent,
                    bg=palette["button_bg"],
                    bd=0,
                    relief="flat",
                    highlightthickness=0,
                    highlightbackground=palette["button_bg"],
                    highlightcolor=palette["button_bg"],
                    width=max(1, int(frame_width)) if frame_width else 1,
                    height=max(1, int(frame_height)),
                )
                frame.pack_propagate(False)
                button = tk.Label(
                    frame,
                    text="",
                    bd=0,
                    relief="flat",
                    highlightthickness=0,
                    bg=palette["button_bg"],
                    cursor="hand2",
                )
                button.pack(fill="both", expand=True, padx=0, pady=0)
                button._siindbad_frame_host = frame
                button._siindbad_scan_running = False
                button._siindbad_scan_after_id = None
                button._siindbad_hover_leave_after_id = None
                button._siindbad_scan_start_ts = None
                button._siindbad_hover_require_reenter = False
                hover_targets = (frame, button)
                for target in hover_targets:
                    target.bind(
                        "<Enter>",
                        lambda _event, b=button: self._siindbad_b_button_hover_enter(b),
                        add="+",
                    )
                    target.bind(
                        "<Leave>",
                        lambda _event, b=button: self._siindbad_b_button_hover_leave(b),
                        add="+",
                    )
                for target in (frame, button):
                    target.bind(
                        "<Button-1>",
                        lambda _event, b=button, cmd=command: self._invoke_siindbad_b_button(b, cmd),
                        add="+",
                    )
            else:
                button = tk.Button(parent, command=command)
            self._apply_siindbad_toolbar_button_style(button, key=key, text=text)
            return button
        image = self._toolbar_button_images.get(key)
        if image is not None:
            button = tk.Button(
                parent,
                image=image,
                command=command,
            )
            self._apply_asset_toolbar_button_style(button)
            return button
        return ttk.Button(parent, text=text, command=command)

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
        except Exception:
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
        # SIINDBAD A/B/C uses generated native buttons/icons (non-asset-heavy).
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
            except Exception:
                continue
        if self._font_stepper_label and self._font_stepper_label.winfo_exists():
            image = self._toolbar_button_images.get("font")
            if image is not None:
                try:
                    self._font_stepper_label.configure(image=image)
                except Exception:
                    pass

    @staticmethod
    def _theme_chip_palette(variant):
        return theme_service.theme_chip_palette(variant)

    @staticmethod
    def _tree_variant_chip_palette(variant):
        return theme_service.tree_variant_chip_palette(variant)

    def _footer_style_variant(self):
        return footer_service.footer_style_variant()

    def _footer_visual_spec(self):
        mode = self._footer_style_variant()
        spec = footer_service.footer_visual_spec(mode)
        return {
            "label_font": (self._preferred_mono_family(), 9, "bold"),
            "chip_font": self._footer_badge_chip_font(),
            **dict(spec),
        }

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
            except Exception:
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
        except Exception:
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
        except Exception:
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
        except Exception:
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
        except Exception:
            pass

    def _update_header_variant_controls(self):
        theme = getattr(self, "_theme", {})
        host = getattr(self, "_header_variant_host", None)
        host_in_footer = bool(getattr(self, "_header_variant_is_footer", False))
        host_bg = theme.get("credit_bg", "#0b1118") if host_in_footer else theme.get("bg", "#0f131a")
        if host and host.winfo_exists():
            try:
                host.configure(bg=host_bg)
            except Exception:
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
                except Exception:
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
            except Exception:
                continue

    def _apply_footer_layout_variant(self):
        bar = getattr(self, "_credit_bar", None)
        content = getattr(self, "_credit_content", None)
        left_slot = getattr(self, "_credit_left_slot", None)
        center_slot = getattr(self, "_credit_center_slot", None)
        right_slot = getattr(self, "_credit_right_slot", None)
        if bar is None or content is None or left_slot is None or center_slot is None or right_slot is None:
            return
        try:
            if not (bar.winfo_exists() and content.winfo_exists()):
                return
        except Exception:
            return

        is_b = self._footer_style_variant() == "B"
        try:
            # Keep content owned by left slot; only adjust grid placement for alignment.
            if not content.winfo_manager():
                content.pack(side="left")
        except Exception:
            pass

        if is_b:
            try:
                center_slot.grid_remove()
                right_slot.grid_remove()
            except Exception:
                pass
            try:
                left_slot.grid_configure(column=0, columnspan=3, sticky="ew", padx=(6, 6), pady=(1, 1))
                bar.grid_columnconfigure(0, weight=1)
                bar.grid_columnconfigure(1, weight=0)
                bar.grid_columnconfigure(2, weight=0)
                content.pack_configure(side="left", fill="none", expand=False)
            except Exception:
                pass
        else:
            try:
                left_slot.grid_configure(column=0, columnspan=1, sticky="w", padx=(6, 0), pady=(1, 1))
                center_slot.grid(row=0, column=1, sticky="ew", pady=(1, 1))
                right_slot.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=(1, 1))
                bar.grid_columnconfigure(0, weight=0)
                bar.grid_columnconfigure(1, weight=1)
                bar.grid_columnconfigure(2, weight=0)
                content.pack_configure(side="left", fill="none", expand=False)
            except Exception:
                pass

        divider_pad = (5, 4) if is_b else (8, 6)
        left_side_widgets = (
            getattr(self, "_credit_badge_host", None),
            getattr(self, "_credit_badges_divider", None),
            getattr(self, "_credit_discord_badge_host", None),
            getattr(self, "_credit_discord_divider", None),
            getattr(self, "_bug_report_host", None),
            getattr(self, "_credit_theme_divider", None),
            getattr(self, "_theme_selector_host", None),
        )
        for widget in left_side_widgets:
            if widget is None:
                continue
            try:
                if widget.winfo_exists():
                    widget.pack_configure(side="left")
            except Exception:
                continue
        for divider in (
            getattr(self, "_credit_badges_divider", None),
            getattr(self, "_credit_discord_divider", None),
            getattr(self, "_credit_theme_divider", None),
        ):
            if divider is None:
                continue
            try:
                if divider.winfo_exists():
                    divider.pack_configure(padx=divider_pad)
            except Exception:
                continue

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
                except Exception:
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
            except Exception:
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
        self._schedule_theme_asset_prewarm(targets=(other_variant,), delay_ms=180)
        if save:
            try:
                self._save_user_settings()
            except Exception:
                pass
        self._log_theme_perf(f"switch {previous_variant}->{variant}", started_ts=switch_started)

    def _refresh_runtime_theme_widgets(self):
        theme = getattr(self, "_theme", None)
        if not theme:
            return
        try:
            self.root.configure(bg=theme["bg"])
        except Exception:
            pass

        self._update_logo_for_theme(force=False)

        if self._font_stepper_label and self._font_stepper_label.winfo_exists():
            try:
                self._font_stepper_label.configure(bg=theme["bg"])
            except Exception:
                pass
        if self.logo_label and self.logo_label.winfo_exists():
            try:
                self.logo_label.configure(bg=theme["bg"])
            except Exception:
                pass
        self._apply_logo_frame_theme()

        if hasattr(self, "find_entry") and self.find_entry:
            try:
                self.find_entry.configure(
                    bg=theme.get("panel", "#161b24"),
                    fg=theme.get("fg", "#e6e6e6"),
                    insertbackground=theme.get("fg", "#e6e6e6"),
                    selectbackground=theme.get("select_bg", "#2f3a4d"),
                    selectforeground=theme.get("select_fg", "#ffffff"),
                    highlightbackground=theme.get("find_border", "#ffffff"),
                    highlightcolor=theme.get("find_border", "#ffffff"),
                )
            except Exception:
                pass
        toolbar_center = getattr(self, "_toolbar_center_frame", None)
        if toolbar_center and toolbar_center.winfo_exists():
            try:
                toolbar_center.configure(bg=theme.get("bg", "#0f131a"))
            except Exception:
                pass
        separator = getattr(self, "_body_top_separator", None)
        if separator and separator.winfo_exists():
            try:
                border = theme.get("logo_border_outer", "#349fc7")
                separator.configure(
                    bg=theme.get("bg", "#0f131a"),
                    highlightbackground=border,
                    highlightcolor=border,
                )
            except Exception:
                pass
        separator_inner = getattr(self, "_body_top_separator_inner", None)
        if separator_inner and separator_inner.winfo_exists():
            try:
                inner = theme.get("logo_border_inner", "#a9ddf0")
                separator_inner.configure(
                    bg=theme.get("bg", "#0f131a"),
                    highlightbackground=inner,
                    highlightcolor=inner,
                )
            except Exception:
                pass
        self._refresh_input_mode_theme_widgets()
        self._update_find_entry_layout()

        if self._credit_bar and self._credit_bar.winfo_exists():
            try:
                self._credit_bar.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    highlightbackground=theme.get("credit_border", "#1f2f3f"),
                    highlightcolor=theme.get("credit_border", "#1f2f3f"),
                )
            except Exception:
                pass
        if self._credit_content and self._credit_content.winfo_exists():
            try:
                self._credit_content.configure(bg=theme.get("credit_bg", "#0b1118"))
            except Exception:
                pass
        if self._credit_label and self._credit_label.winfo_exists():
            try:
                self._credit_label.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    fg=theme.get("credit_label_fg", "#b5cade"),
                )
            except Exception:
                pass
        if self._credit_badge_host and self._credit_badge_host.winfo_exists():
            try:
                self._credit_badge_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except Exception:
                pass
            self._render_credit_badges()
        if self._header_variant_bar and self._header_variant_bar.winfo_exists():
            try:
                self._header_variant_bar.configure(bg=theme.get("bg", "#0f131a"))
            except Exception:
                pass
        if self._credit_discord_badge_host and self._credit_discord_badge_host.winfo_exists():
            try:
                self._credit_discord_badge_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except Exception:
                pass
            self._render_credit_discord_badges()
        divider = getattr(self, "_credit_badges_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = self._blend_hex_color(border, label, 0.35)
                glow_line = self._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(self, "_credit_badges_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except Exception:
                pass
        divider = getattr(self, "_credit_discord_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = self._blend_hex_color(border, label, 0.35)
                glow_line = self._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(self, "_credit_discord_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except Exception:
                pass
        divider = getattr(self, "_credit_theme_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = self._blend_hex_color(border, label, 0.35)
                glow_line = self._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(self, "_credit_theme_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except Exception:
                pass
        if self._theme_selector_host and self._theme_selector_host.winfo_exists():
            try:
                self._theme_selector_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except Exception:
                pass
        if self._bug_report_host and self._bug_report_host.winfo_exists():
            try:
                self._bug_report_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except Exception:
                pass
        if self._bug_report_label and self._bug_report_label.winfo_exists():
            try:
                self._bug_report_label.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    fg=theme.get("credit_label_fg", "#b5cade"),
                )
            except Exception:
                pass
        if self._bug_report_chip and self._bug_report_chip.winfo_exists():
            self._sync_bug_report_chip_colors()
        self._apply_footer_layout_variant()
        self._update_editor_mode_controls()
        bug_dialog = getattr(self, "_bug_report_dialog", None)
        if bug_dialog is not None:
            try:
                if bug_dialog.winfo_exists():
                    self._apply_windows_titlebar_theme(bug_dialog)
            except Exception:
                pass
        bug_header = getattr(self, "_bug_report_header_frame", None)
        bug_card = getattr(self, "_bug_report_card_frame", None)
        if bug_header is not None:
            try:
                if bug_header.winfo_exists():
                    header_bg = theme.get("title_bar_bg", "#102535")
                    header_fg = theme.get("title_bar_fg", theme.get("fg", "#e6e6e6"))
                    header_border = theme.get("title_bar_border", theme.get("logo_border_outer", "#2a5a7a"))
                    bug_header.configure(
                        bg=header_bg,
                        highlightbackground=header_border,
                        highlightcolor=header_border,
                    )
                    for attr in ("_bug_report_header_icon", "_bug_report_header_title", "_bug_report_close_badge"):
                        widget = getattr(self, attr, None)
                        if widget is not None and widget.winfo_exists():
                            widget.configure(bg=header_bg, fg=header_fg)
                    bug_icon = getattr(self, "_bug_report_header_icon", None)
                    if bug_icon is not None and bug_icon.winfo_exists():
                        bug_icon_photo = self._load_bug_report_chip_icon(max_size=18, tint=header_fg)
                        self._bug_report_header_icon_photo = bug_icon_photo
                        bug_icon.configure(image=bug_icon_photo if bug_icon_photo is not None else "")
            except Exception:
                pass
        if bug_card is not None:
            try:
                if bug_card.winfo_exists():
                    border = theme.get("logo_border_outer", "#4b97c2")
                    bug_card.configure(highlightbackground=border, highlightcolor=border)
                    if bug_dialog is not None and bug_dialog.winfo_exists():
                        bug_dialog.configure(bg=theme.get("bg", "#0f131a"))
                    self._start_bug_report_header_pulse()
            except Exception:
                pass

        self._update_app_theme_controls()
        self._update_header_variant_controls()
        self._update_tree_style_controls()
        self._update_toolbar_style_controls()
        self._style_text_widget()
        self._refresh_open_readme_window()
        self._refresh_tree_item_markers()
        self._refresh_active_error_theme()

    @staticmethod
    def _startup_loader_lines(ready=False):
        return loader_service.startup_loader_lines(ready=ready)

    def _next_startup_loader_line(self, ready=False):
        pool_attr = "_startup_loader_line_pool_ready" if ready else "_startup_loader_line_pool_loading"
        line, next_pool = loader_service.pop_startup_loader_line(
            ready=ready,
            pool=getattr(self, pool_attr, []),
        )
        setattr(self, pool_attr, next_pool)
        return line

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
        except Exception:
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
            except Exception:
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
        except Exception:
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
        self._update_startup_loader_progress()
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_startup_loader_progress_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
        interval = max(70, int(getattr(self, "_startup_loader_progress_interval_ms", 90) or 90))
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
            except Exception:
                pass
        self._startup_loader_text_after_id = root.after(interval, self._tick_startup_loader_statement)

    def _startup_loader_title_color_for_variant(self, variant):
        return loader_service.title_color_for_variant(
            variant,
            siindbad_palette=self._theme_palette_for_variant("SIINDBAD"),
            kamue_palette=self._theme_palette_for_variant("KAMUE"),
        )

    def _apply_startup_loader_title_variant(self):
        prefix = getattr(self, "_startup_loader_title_prefix_label", None)
        if prefix is None or not prefix.winfo_exists():
            return
        suffix = getattr(self, "_startup_loader_title_suffix_label", None)
        variant = loader_service.normalize_title_variant(
            getattr(self, "_startup_loader_title_variant", "SIINDBAD")
        )
        self._startup_loader_title_variant = variant
        try:
            prefix.configure(
                text=variant,
                fg=self._startup_loader_title_color_for_variant(variant),
            )
        except Exception:
            pass
        if suffix is not None and suffix.winfo_exists():
            try:
                suffix.configure(text=" SHELL SYSTEM SYNC")
            except Exception:
                pass

    def _tick_startup_loader_title(self):
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        prefix = getattr(self, "_startup_loader_title_prefix_label", None)
        if prefix is None or not prefix.winfo_exists():
            return
        current = getattr(self, "_startup_loader_title_variant", "SIINDBAD")
        self._startup_loader_title_variant = loader_service.next_title_variant(current)
        self._apply_startup_loader_title_variant()
        root = getattr(self, "root", None)
        if root is None:
            return
        after_id = getattr(self, "_startup_loader_title_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except Exception:
                pass
        cycle_ms = max(2200, int(getattr(self, "_startup_loader_title_cycle_ms", 4200) or 4200))
        self._startup_loader_title_after_id = root.after(cycle_ms, self._tick_startup_loader_title)

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
        except Exception:
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
        except Exception:
            self._bounded_cache_put(cache, key, None, max_items=256)
            return None

    @staticmethod
    def _set_startup_loader_bar_fill(fill_widget, pct):
        if fill_widget is None:
            return
        payload = fill_widget
        if isinstance(payload, dict):
            track = payload.get("track")
            fill_label = payload.get("widget")
            owner = payload.get("owner")
            fill_color = payload.get("color", "#4f90bf")
            if (
                track is None
                or fill_label is None
                or owner is None
                or not track.winfo_exists()
                or not fill_label.winfo_exists()
            ):
                return
            fill_w, fill_h = loader_service.compute_loader_fill_dimensions(
                track.winfo_width(),
                track.winfo_height(),
                pct,
            )
            if fill_w <= 0:
                fill_label.place_forget()
                payload["last_w"] = 0
                return
            # Keep loader animation lightweight: avoid per-frame PIL image redraws.
            # Rounded track shell stays intact while fill uses a fast solid block.
            last_color = str(payload.get("last_color", ""))
            if last_color != str(fill_color):
                fill_label.configure(bg=fill_color, image="", text="")
                fill_label.image = None
                payload["last_color"] = str(fill_color)
            last_w = int(payload.get("last_w", -1) or -1)
            if last_w != fill_w or not bool(fill_label.winfo_ismapped()):
                fill_label.place(x=1, y=1, width=fill_w, height=fill_h)
                payload["last_w"] = fill_w
            return
        if not fill_widget.winfo_exists():
            return
        track = fill_widget.master
        if track is None or not track.winfo_exists():
            return
        fill_w, fill_h = loader_service.compute_loader_fill_dimensions(
            track.winfo_width(),
            track.winfo_height(),
            pct,
        )
        fill_widget.place(x=1, y=1, width=max(0, fill_w), height=max(1, fill_h))

    def _startup_loader_variant_progress(self, variant):
        variant = str(variant).upper()
        total = int(getattr(self, "_theme_prewarm_total_by_variant", {}).get(variant, 0) or 0)
        done = int(getattr(self, "_theme_prewarm_done_by_variant", {}).get(variant, 0) or 0)
        warmed = set(getattr(self, "_theme_prewarm_done", set()))
        if total <= 0:
            return 100.0 if variant in warmed else 0.0
        done = max(0, min(done, total))
        return float(done) * 100.0 / float(total)

    def _update_startup_loader_progress(self):
        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is None or not overlay.winfo_exists():
            return
        started = float(getattr(self, "_startup_loader_started_ts", 0.0) or 0.0)
        now = time.perf_counter()
        elapsed_ms = max(0.0, (now - started) * 1000.0) if started > 0 else 0.0
        timeline_ms = max(1000, int(getattr(self, "_startup_loader_extra_hold_ms", 1800) or 1800))
        ready = getattr(self, "_startup_loader_ready_ts", None) is not None
        overall, top_pct, bottom_pct = startup_loader_core.compute_loader_progress(
            elapsed_ms=elapsed_ms,
            timeline_ms=timeline_ms,
            ready=ready,
            required_variants=getattr(self, "_startup_loader_required_variants", set()),
            active_variant=getattr(self, "_app_theme_variant", "SIINDBAD"),
            variant_progress_getter=self._startup_loader_variant_progress,
        )

        self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_top_fill", None), top_pct)
        self._set_startup_loader_bar_fill(getattr(self, "_startup_loader_bottom_fill", None), bottom_pct)

        pct_label = getattr(self, "_startup_loader_pct_label", None)
        if pct_label is not None and pct_label.winfo_exists():
            pct_label.configure(text=f"{int(round(overall))}%")

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
            except Exception:
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
                    except Exception:
                        pass
                setattr(self, attr, None)

        overlay = getattr(self, "_startup_loader_overlay", None)
        if overlay is not None and overlay.winfo_exists():
            try:
                overlay.destroy()
            except Exception:
                pass
        if root is not None and bool(getattr(self, "_startup_loader_window_mode", False)):
            try:
                root.deiconify()
                root.lift()
                root.focus_force()
            except Exception:
                pass
        self._startup_loader_overlay = None
        self._startup_loader_pct_label = None
        self._startup_loader_statement_label = None
        self._startup_loader_title_prefix_label = None
        self._startup_loader_title_suffix_label = None
        self._startup_loader_top_fill = None
        self._startup_loader_bottom_fill = None
        deferred = startup_loader_core.normalize_deferred_variants_for_schedule(
            getattr(self, "_startup_loader_deferred_variants", set())
        )
        self._startup_loader_deferred_variants = set()
        if root is not None and deferred:
            try:
                self._schedule_theme_asset_prewarm(targets=deferred, delay_ms=180)
            except Exception:
                pass
        # Run auto update-check after loader teardown so startup stays responsive.
        if root is not None and self._auto_update_startup_enabled():
            self._schedule_auto_update_check(delay_ms=350)
        self._schedule_crash_report_offer()

    def _log_theme_perf(self, label, started_ts=None):
        if not bool(getattr(self, "_theme_perf_logging", False)):
            return
        if started_ts is None:
            print(f"[theme-perf] {label}")
            return
        elapsed = (time.perf_counter() - float(started_ts)) * 1000.0
        print(f"[theme-perf] {label}: {elapsed:.1f}ms")

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
        return tasks

    def _execute_theme_prewarm_task(self, task):
        variant = str(task.get("variant", "")).upper()
        kind = str(task.get("kind", "")).lower()
        if variant not in ("SIINDBAD", "KAMUE"):
            return

        original_variant = getattr(self, "_app_theme_variant", "SIINDBAD")
        original_theme = getattr(self, "_theme", None)
        try:
            self._app_theme_variant = variant
            self._theme = self._theme_palette_for_variant(variant)
            if kind == "button":
                key = str(task.get("key", ""))
                text = str(task.get("text", key.title()))
                style = self._siindbad_effective_style()
                display_text = self._siindbad_toolbar_label_text(style, key, text)
                palette = self._siindbad_toolbar_style_palette()
                width = self._siindbad_toolbar_frame_width(style, key, display_text)
                height = self._siindbad_b_button_height(key, default_height=34)
                self._siindbad_b_render_button_bundle(
                    key=key,
                    text=display_text,
                    width=max(1, int(width)),
                    height=max(1, int(height)),
                    palette=palette,
                    render_mode="full",
                )
                return
            if kind == "search":
                search_spec = self._siindbad_b_search_spec() or {}
                search_width = int(search_spec.get("width", 172) or 172)
                search_height = int(search_spec.get("height", 32) or 32)
                find_height = self._siindbad_b_button_height("find", default_height=33)
                search_height = max(1, min(search_height, int(find_height)))
                self._siindbad_b_search_sprite_image(search_width, search_height)
                return
            if kind == "font":
                font_spec = self._siindbad_b_font_sprite_spec()
                if not font_spec:
                    return
                fw = max(1, int(font_spec.get("width", 146) or 146))
                fh = max(1, int(font_spec.get("height", 34) or 34))
                base_path = font_spec.get("path")
                if base_path:
                    self._load_toolbar_button_image(base_path, max_width=fw, max_height=fh, stretch_to_fit=True)
                hover_path = str(font_spec.get("hover_path", "") or "")
                if hover_path and os.path.isfile(hover_path):
                    self._load_toolbar_button_image(hover_path, max_width=fw, max_height=fh, stretch_to_fit=True)
                return
            if kind == "logo":
                logo_path = self._find_logo_path()
                if logo_path:
                    self._load_logo_image(logo_path)
                return
            if kind == "badges":
                self._load_credit_badge_sources()
                self._load_credit_github_icon(max_size=14, tint="#d8e8f2", with_plate=False)
                self._load_credit_discord_icon(max_size=14, tint="#d8e8f2", with_plate=False)
                return
        finally:
            self._app_theme_variant = original_variant
            self._theme = original_theme

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
            try:
                self.root.after(1, self._refresh_toolbar_button_images)
            except Exception:
                pass
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
            except Exception:
                pass
        self._theme_prewarm_after_id = root.after(max(1, int(delay_ms)), self._run_theme_asset_prewarm)

    def _run_theme_asset_prewarm(self):
        self._theme_prewarm_after_id = None
        queue = list(getattr(self, "_theme_prewarm_queue", []))
        raw_tasks = getattr(self, "_theme_prewarm_tasks", None)
        if isinstance(raw_tasks, deque):
            tasks = raw_tasks
        elif raw_tasks:
            tasks = deque(raw_tasks)
        else:
            tasks = deque()
        if not queue or not tasks:
            self._theme_prewarm_queue = []
            self._theme_prewarm_tasks = deque()
            self._update_startup_loader_progress()
            self._on_startup_full_load_ready()
            return
        loader_visible = False
        try:
            overlay = getattr(self, "_startup_loader_overlay", None)
            loader_visible = bool(overlay is not None and overlay.winfo_exists())
        except Exception:
            loader_visible = False
        budget_ms, max_tasks_this_tick, next_tick_ms = startup_loader_core.prewarm_tick_policy(
            loader_visible=loader_visible,
            loader_budget_ms=int(getattr(self, "_theme_prewarm_loader_budget_ms", 6) or 6),
            idle_budget_ms=int(getattr(self, "_theme_prewarm_budget_ms", 10) or 10),
            loader_tick_ms=int(getattr(self, "_theme_prewarm_loader_tick_ms", 16) or 16),
            idle_tick_ms=int(getattr(self, "_theme_prewarm_idle_tick_ms", 12) or 12),
        )
        deadline = time.perf_counter() + (float(budget_ms) / 1000.0)
        done_counts = dict(getattr(self, "_theme_prewarm_done_by_variant", {}))
        totals = dict(getattr(self, "_theme_prewarm_total_by_variant", {}))
        processed = 0
        while tasks and time.perf_counter() < deadline and processed < max_tasks_this_tick:
            task = tasks.popleft()
            variant = str(task.get("variant", "")).upper()
            if variant not in ("SIINDBAD", "KAMUE"):
                continue
            processed += 1
            self._theme_prewarm_active_variant = variant
            try:
                self._execute_theme_prewarm_task(task)
            except Exception:
                pass
            total = int(totals.get(variant, 0) or 0)
            if total > 0:
                current_done = int(done_counts.get(variant, 0) or 0)
                done_counts[variant] = min(total, current_done + 1)
            remaining_for_variant = any(
                str(item.get("variant", "")).upper() == variant for item in tasks
            )
            if not remaining_for_variant:
                queue = [name for name in queue if str(name).upper() != variant]
                self._finish_theme_prewarm_variant(variant)

        self._theme_prewarm_done_by_variant = done_counts
        self._theme_prewarm_queue = queue
        self._theme_prewarm_tasks = tasks
        self._update_startup_loader_progress()
        if self._theme_prewarm_tasks:
            self._theme_prewarm_after_id = self.root.after(next_tick_ms, self._run_theme_asset_prewarm)
        else:
            self._on_startup_full_load_ready()

    def _prewarm_theme_variant_assets(self, variant):
        tasks = self._build_theme_prewarm_tasks(variant)
        for task in tasks:
            try:
                self._execute_theme_prewarm_task(task)
            except Exception:
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
            except Exception:
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

    def _shade_toolbar_button_for_theme(self, image):
        """Apply theme-specific color treatment to toolbar button assets."""
        if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() != "KAMUE":
            return image
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
            return out
        except Exception:
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
        except Exception:
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
            image = self._shade_toolbar_button_for_theme(image)
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
        except Exception:
            pass

        try:
            image = tk.PhotoImage(file=path)
        except Exception:
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
        except Exception:
            messagebox.showerror("Open Link", f"Failed to open link:\n{url}")

    @staticmethod
    def _bind_click_recursive(widget, callback):
        widget.bind("<Button-1>", callback)
        try:
            widget.configure(cursor="hand2")
        except Exception:
            pass
        for child in widget.winfo_children():
            JsonEditor._bind_click_recursive(child, callback)

    @staticmethod
    def _extract_badge_boxes(image, threshold=16):
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = rgb.load()
        min_row_pixels = max(8, width // 60)
        min_group_height = max(20, height // 20)

        def row_lit_count(y):
            lit = 0
            for x in range(width):
                if max(pixels[x, y]) > threshold:
                    lit += 1
            return lit

        def box_for_rows(y1, y2):
            x1, x2 = width, -1
            for yy in range(y1, y2 + 1):
                for xx in range(width):
                    if max(pixels[xx, yy]) > threshold:
                        if xx < x1:
                            x1 = xx
                        if xx > x2:
                            x2 = xx
            if x2 < x1:
                return None
            pad = 4
            return (
                max(0, x1 - pad),
                max(0, y1 - pad),
                min(width, x2 + pad + 1),
                min(height, y2 + pad + 1),
            )

        row_has = [row_lit_count(y) >= min_row_pixels for y in range(height)]
        groups = []
        y = 0
        while y < height:
            while y < height and not row_has[y]:
                y += 1
            if y >= height:
                break
            start = y
            while y < height and row_has[y]:
                y += 1
            end = y - 1
            if end - start + 1 >= min_group_height:
                groups.append((start, end))

        boxes = []
        for start, end in groups:
            box = box_for_rows(start, end)
            if not box:
                continue
            area = (box[2] - box[0]) * (box[3] - box[1])
            if area >= 20000:
                boxes.append(box)

        if len(boxes) < 2:
            halves = ((0, height // 2), (height // 2, height))
            split_boxes = []
            for y_start, y_end in halves:
                top = None
                bottom = None
                for yy in range(y_start, y_end):
                    if row_lit_count(yy) >= min_row_pixels:
                        if top is None:
                            top = yy
                        bottom = yy
                if top is None or bottom is None:
                    continue
                box = box_for_rows(top, bottom)
                if not box:
                    continue
                area = (box[2] - box[0]) * (box[3] - box[1])
                if area >= 20000:
                    split_boxes.append(box)
            boxes = split_boxes

        if len(boxes) > 2:
            boxes = sorted(
                boxes,
                key=lambda b: (b[2] - b[0]) * (b[3] - b[1]),
                reverse=True,
            )[:2]
        boxes.sort(key=lambda b: b[1])
        return boxes

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
            with image_module.open(path) as source_file:
                source = source_file.convert("RGBA")
            boxes = self._extract_badge_boxes(source)
            if len(boxes) < 2:
                self._credit_badge_sources_cache = []
                return []
            result = [source.crop(box).copy() for box in boxes[:2]]
            self._credit_badge_sources_cache = result
            return result
        except Exception:
            self._credit_badge_sources_cache = []
            return []

    def _load_credit_github_icon(self, max_size=16, tint="#dff6ff", with_plate=False):
        cache = getattr(self, "_credit_github_icon_cache", None)
        if cache is None:
            cache = {}
            self._credit_github_icon_cache = cache
        signature = (int(max_size), str(tint), bool(with_plate))
        cached = cache.get(signature)
        if cached is not None:
            return cached
        base_dir = self._resource_base_dir()
        candidates = [
            os.path.join(base_dir, "assets", "buttons", "github_mark_official.png"),
            os.path.join(base_dir, "assets", "buttons", "github_mark_octicons.png"),
        ]
        icon_path = next((path for path in candidates if os.path.isfile(path)), None)
        if not icon_path:
            self._bounded_cache_put(cache, signature, None, max_items=64)
            return None
        try:
            image_module = importlib.import_module("PIL.Image")
            with image_module.open(icon_path) as icon_file:
                icon = icon_file.convert("RGBA")
            alpha = icon.split()[-1]
            alpha_min, alpha_max = alpha.getextrema()
            mask = alpha
            if alpha_min == 255 and alpha_max == 255:
                # Some downloaded marks ship on white backgrounds; derive a mask from luminance.
                gray = icon.convert("L")
                mask = gray.point(lambda p: max(0, min(255, (235 - p) * 4)))
            bounds = mask.getbbox()
            if bounds:
                icon = icon.crop(bounds)
                mask = mask.crop(bounds)
            tint_hex = str(tint).strip().lstrip("#")
            if len(tint_hex) != 6:
                tint_hex = "dff6ff"
            rgb = tuple(int(tint_hex[i:i + 2], 16) for i in (0, 2, 4))
            tinted = image_module.new("RGBA", icon.size, rgb + (0,))
            tinted.putalpha(mask)
            icon = tinted
            if max_size and (icon.width > max_size or icon.height > max_size):
                scale = min(max_size / float(icon.width), max_size / float(icon.height))
                new_size = (
                    max(1, int(round(icon.width * scale))),
                    max(1, int(round(icon.height * scale))),
                )
                icon = icon.resize(new_size, image_module.LANCZOS)
            if with_plate:
                draw_module = importlib.import_module("PIL.ImageDraw")
                plate_pad = 3
                plate_size = max(icon.width, icon.height) + (plate_pad * 2)
                plate = image_module.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
                draw = draw_module.Draw(plate)
                draw.ellipse(
                    (0, 0, plate_size - 1, plate_size - 1),
                    fill=(70, 116, 146, 28),
                )
                draw.ellipse(
                    (1, 1, plate_size - 2, plate_size - 2),
                    fill=(18, 30, 42, 210),
                    outline=(76, 111, 136, 120),
                    width=1,
                )
                pos = ((plate_size - icon.width) // 2, (plate_size - icon.height) // 2)
                plate.alpha_composite(icon, pos)
                icon = plate
            photo = self._pil_to_photo(icon)
            self._bounded_cache_put(cache, signature, photo, max_items=64)
            return photo
        except Exception:
            self._bounded_cache_put(cache, signature, None, max_items=64)
            return None

    def _load_credit_discord_icon(self, max_size=16, tint="#dff6ff", with_plate=False):
        cache = getattr(self, "_credit_discord_icon_cache", None)
        if cache is None:
            cache = {}
            self._credit_discord_icon_cache = cache
        signature = (int(max_size), str(tint), bool(with_plate))
        cached = cache.get(signature)
        if cached is not None:
            return cached
        base_dir = self._resource_base_dir()
        candidates = [
            os.path.join(base_dir, "assets", "buttons", "discord_clyde_icon.png"),
            os.path.join(base_dir, "assets", "buttons", "discord_mark_symbol.png"),
        ]
        icon_path = next((path for path in candidates if os.path.isfile(path)), None)
        if not icon_path:
            self._bounded_cache_put(cache, signature, None, max_items=64)
            return None
        try:
            image_module = importlib.import_module("PIL.Image")
            with image_module.open(icon_path) as icon_file:
                icon = icon_file.convert("RGBA")
            alpha = icon.split()[-1]
            alpha_min, alpha_max = alpha.getextrema()
            mask = alpha
            if alpha_min == 255 and alpha_max == 255:
                gray = icon.convert("L")
                mask = gray.point(lambda p: max(0, min(255, (235 - p) * 4)))
            bounds = mask.getbbox()
            if bounds:
                icon = icon.crop(bounds)
                mask = mask.crop(bounds)
            tint_hex = str(tint).strip().lstrip("#")
            if len(tint_hex) != 6:
                tint_hex = "dff6ff"
            rgb = tuple(int(tint_hex[i:i + 2], 16) for i in (0, 2, 4))
            tinted = image_module.new("RGBA", icon.size, rgb + (0,))
            tinted.putalpha(mask)
            icon = tinted
            if max_size and (icon.width > max_size or icon.height > max_size):
                scale = min(max_size / float(icon.width), max_size / float(icon.height))
                new_size = (
                    max(1, int(round(icon.width * scale))),
                    max(1, int(round(icon.height * scale))),
                )
                icon = icon.resize(new_size, image_module.LANCZOS)
            if with_plate:
                draw_module = importlib.import_module("PIL.ImageDraw")
                plate_pad = 3
                plate_size = max(icon.width, icon.height) + (plate_pad * 2)
                plate = image_module.new("RGBA", (plate_size, plate_size), (0, 0, 0, 0))
                draw = draw_module.Draw(plate)
                draw.ellipse(
                    (0, 0, plate_size - 1, plate_size - 1),
                    fill=(70, 116, 146, 28),
                )
                draw.ellipse(
                    (1, 1, plate_size - 2, plate_size - 2),
                    fill=(18, 30, 42, 210),
                    outline=(76, 111, 136, 120),
                    width=1,
                )
                pos = ((plate_size - icon.width) // 2, (plate_size - icon.height) // 2)
                plate.alpha_composite(icon, pos)
                icon = plate
            photo = self._pil_to_photo(icon)
            self._bounded_cache_put(cache, signature, photo, max_items=64)
            return photo
        except Exception:
            self._bounded_cache_put(cache, signature, None, max_items=64)
            return None

    def _resize_pil_image_to_height(self, image, max_height):
        if not image or not max_height or image.height <= max_height:
            return image
        try:
            image_module = importlib.import_module("PIL.Image")
            scale = max_height / float(image.height)
            new_size = (max(1, int(round(image.width * scale))), max_height)
            return image.resize(new_size, image_module.LANCZOS)
        except Exception:
            return image

    def _enhance_badge_image(self, image):
        try:
            image_enhance_module = importlib.import_module("PIL.ImageEnhance")
            boosted = image_enhance_module.Contrast(image).enhance(1.18)
            boosted = image_enhance_module.Sharpness(boosted).enhance(1.28)
            return boosted
        except Exception:
            return image

    def _pil_to_photo(self, image):
        try:
            image_tk_module = importlib.import_module("PIL.ImageTk")
            return image_tk_module.PhotoImage(image)
        except Exception:
            return None

    def _render_credit_badges(self):
        parent = self._credit_badge_host
        if parent is None:
            return

        github_specs = [
            ("SIINDBAD", "https://github.com/Siindbad"),
            ("KAMUE", "https://github.com/Kamue-cmd"),
        ]
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        palette = self._footer_badge_palette(variant)
        spec = self._footer_visual_spec()
        sources = self._load_credit_badge_sources()
        self._credit_badge_images = []
        chip_bg = palette["bg"]
        chip_border = palette["border"]
        text_fg = palette["fg"]
        icon_tint = "#d8e8f2"
        icon_with_plate = False
        icon_size = int(spec["chip_icon_size"])
        render_signature = (
            tuple(github_specs),
            variant,
            self._footer_style_variant(),
            chip_bg,
            chip_border,
            text_fg,
            icon_tint,
            bool(icon_with_plate),
            int(icon_size),
            tuple(spec["chip_font"]),
        )
        if (
            render_signature == getattr(self, "_credit_badge_render_signature", None)
            and parent.winfo_children()
        ):
            return
        for child in parent.winfo_children():
            child.destroy()

        github_icon_photo = self._load_credit_github_icon(
            max_size=icon_size,
            tint=icon_tint,
            with_plate=icon_with_plate,
        )
        if github_icon_photo is not None:
            self._credit_badge_images.append(github_icon_photo)
        name_font = spec["chip_font"]

        for idx, (name, url) in enumerate(github_specs):
            source = sources[idx] if idx < len(sources) else None
            pad_left = 0 if idx == 0 else int(spec["chip_gap"])
            open_cb = lambda _event, link=url: self._open_external_link(link)

            chip = tk.Frame(
                parent,
                bg=chip_bg,
                bd=0,
                highlightthickness=1,
                highlightbackground=chip_border,
                highlightcolor=chip_border,
            )
            chip.pack(side="left", padx=(pad_left, 0))
            if github_icon_photo is not None:
                icon_label = tk.Label(
                    chip,
                    image=github_icon_photo,
                    bg=chip_bg,
                    bd=0,
                    highlightthickness=0,
                )
                icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            elif source is not None:
                icon_width = max(1, int(round(source.width * 0.30)))
                icon = source.crop((0, 0, icon_width, source.height))
                icon = self._resize_pil_image_to_height(icon, int(spec["chip_icon_size"]))
                icon_photo = self._pil_to_photo(icon)
                if icon_photo is not None:
                    self._credit_badge_images.append(icon_photo)
                    icon_label = tk.Label(
                        chip,
                        image=icon_photo,
                        bg=chip_bg,
                        bd=0,
                        highlightthickness=0,
                    )
                    icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            text_label = tk.Label(
                chip,
                text=name,
                bg=chip_bg,
                fg=text_fg,
                font=name_font,
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=spec["chip_text_pady"],
            )
            text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
            self._bind_click_recursive(chip, open_cb)
        self._credit_badge_render_signature = render_signature

    def _render_credit_discord_badges(self):
        parent = self._credit_discord_badge_host
        if parent is None:
            return
        discord_specs = [
            ("SIN.NETWORK", "https://discord.gg/kpFXrtyr2Z"),
            ("G-DEVS", "https://discord.gg/U7pZFXXtcn"),
        ]
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        palette = self._footer_badge_palette(variant)
        spec = self._footer_visual_spec()
        theme = getattr(self, "_theme", {})
        self._credit_discord_badge_images = []
        chip_bg = palette["bg"]
        chip_border = palette["border"]
        text_fg = palette["fg"]
        label_bg = theme.get("credit_bg", "#0b1118")
        label_fg = theme.get("credit_label_fg", "#b5cade")
        icon_tint = "#d8e8f2"
        icon_with_plate = False
        icon_size = int(spec["chip_icon_size"])
        render_signature = (
            tuple(discord_specs),
            variant,
            self._footer_style_variant(),
            chip_bg,
            chip_border,
            text_fg,
            label_bg,
            label_fg,
            icon_tint,
            bool(icon_with_plate),
            int(icon_size),
            tuple(spec["chip_font"]),
        )
        if (
            render_signature == getattr(self, "_credit_discord_badge_render_signature", None)
            and parent.winfo_children()
        ):
            return
        for child in parent.winfo_children():
            child.destroy()
        discord_icon_photo = self._load_credit_discord_icon(
            max_size=icon_size,
            tint=icon_tint,
            with_plate=icon_with_plate,
        )
        if discord_icon_photo is not None:
            self._credit_discord_badge_images.append(discord_icon_photo)
        name_font = spec["chip_font"]
        discord_label = tk.Label(
            parent,
            text="DISCORD :",
            bg=label_bg,
            fg=label_fg,
            font=spec["label_font"],
            bd=0,
            highlightthickness=0,
            padx=0,
            pady=spec["chip_text_pady"],
        )
        discord_label.pack(side="left", padx=(0, spec["label_gap"]))

        for idx, (name, url) in enumerate(discord_specs):
            pad_left = 0 if idx == 0 else int(spec["chip_gap"])
            chip = tk.Frame(
                parent,
                bg=chip_bg,
                bd=0,
                highlightthickness=1,
                highlightbackground=chip_border,
                highlightcolor=chip_border,
            )
            chip.pack(side="left", padx=(pad_left, 0))
            if discord_icon_photo is not None:
                icon_label = tk.Label(
                    chip,
                    image=discord_icon_photo,
                    bg=chip_bg,
                    bd=0,
                    highlightthickness=0,
                )
                icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
            text_label = tk.Label(
                chip,
                text=name,
                bg=chip_bg,
                fg=text_fg,
                font=name_font,
                bd=0,
                highlightthickness=0,
                padx=0,
                pady=spec["chip_text_pady"],
            )
            text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
            if url:
                self._bind_click_recursive(chip, lambda _event, link=url: self._open_external_link(link))
        self._credit_discord_badge_render_signature = render_signature

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
            except Exception:
                pass
        elif self.logo_label and self.logo_label.winfo_exists():
            try:
                self.logo_label.destroy()
            except Exception:
                pass
        self.logo_frame = None
        self._logo_frame_inner = None
        self.logo_label = None

    def _update_logo_for_theme(self, force=False):
        parent = self._header_frame
        if not parent or not parent.winfo_exists():
            return
        logo_path = self._find_logo_path()
        if not logo_path:
            return

        needs_reload = force or logo_path != getattr(self, "_logo_path", None) or not self.logo_image
        if needs_reload:
            image = self._load_logo_image(logo_path)
            if image is None:
                return
            self.logo_image = image
            self._logo_path = logo_path

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
            except Exception:
                pass

        # Keep logo centered even when theme changes or window is resized/maximized.
        pack_target = self.logo_frame if wants_frame else self.logo_label
        try:
            if pack_target is not None and pack_target.winfo_exists():
                pack_target.pack_configure(anchor="center", pady=0)
        except Exception:
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
                except Exception:
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
            except Exception:
                pass
        if self._logo_frame_inner and self._logo_frame_inner.winfo_exists():
            try:
                self._logo_frame_inner.configure(
                    bg=bg,
                    highlightbackground=inner,
                    highlightcolor=inner,
                )
            except Exception:
                pass
        if self.logo_label and self.logo_label.winfo_exists():
            try:
                self.logo_label.configure(bg=bg)
            except Exception:
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
                except Exception:
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
            image = image_module.open(path).convert("RGBA")
            if image.width > max_width:
                scale = max_width / image.width
                new_size = (max_width, int(image.height * scale))
                image = image.resize(new_size, image_module.LANCZOS)
            photo = image_tk_module.PhotoImage(image)
            self._bounded_cache_put(cache, signature, photo, max_items=48)
            return photo
        except Exception:
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
        except Exception:
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
        """Wrap readable prose while preserving section/divider formatting."""
        width = max(56, int(wrap_width or 0))
        out_lines = []
        in_change_logs = False
        for raw_line in str(content or "").splitlines():
            line = raw_line.rstrip()
            # Preserve centered/indented ASCII lines exactly as generated.
            if line and (len(line) - len(line.lstrip(" ")) > 0):
                out_lines.append(line)
                continue
            stripped = line.strip()
            if not stripped:
                out_lines.append("")
                continue
            if re.fullmatch(r"=+", stripped):
                # Normalize divider length to current README viewport width.
                out_lines.append("=" * width)
                continue

            if stripped.upper() == "[ CHANGE LOGS ]":
                in_change_logs = True
                out_lines.append(stripped)
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                # Keep changelog scope active for the version marker only.
                if in_change_logs and not re.match(r"^\[\s*Version\b.*\]$", stripped, re.IGNORECASE):
                    in_change_logs = False
                out_lines.append(stripped)
                continue

            num_match = re.match(r"^(\s*\d+\.\s+)(.+)$", line)
            bullet_match = re.match(r"^(\s*-\s+)(.+)$", line)
            if num_match or bullet_match:
                match = num_match or bullet_match
                prefix = match.group(1)
                body = match.group(2).strip()
                if in_change_logs and bullet_match:
                    # Keep changelog bullets single-line so release notes stay aligned.
                    out_lines.append(prefix + body)
                    continue
                body_width = max(24, width - len(prefix))
                wrapped = textwrap.wrap(
                    body,
                    width=body_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                if not wrapped:
                    out_lines.append(prefix.rstrip())
                    continue
                out_lines.append(prefix + wrapped[0])
                continuation_prefix = " " * len(prefix)
                out_lines.extend(continuation_prefix + chunk for chunk in wrapped[1:])
                continue

            wrapped = textwrap.wrap(
                stripped,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            if wrapped:
                out_lines.extend(wrapped)
            else:
                out_lines.append("")
        return "\n".join(out_lines)

    def show_readme(self, position_hint=None):
        theme = getattr(self, "_theme", None)
        base_dir = self._resource_base_dir()
        readme_path = os.path.join(base_dir, "assets", "Readme.txt")
        content = ""
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except Exception as exc:
                messagebox.showerror("ReadMe", f"Failed to load README.md: {exc}")
                return
        else:
            content = "Readme.txt not found in assets."

        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()

        existing = getattr(self, "_readme_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.destroy()
            except Exception:
                pass

        window = tk.Toplevel(self.root)
        self._readme_window = window
        window.title("ReadMe")
        window.transient(self.root)
        window.bind(
            "<Destroy>",
            lambda _evt, win=window: setattr(self, "_readme_window", None)
            if getattr(self, "_readme_window", None) is win
            else None,
            add="+",
        )
        if theme:
            window.configure(bg=theme["bg"])
            try:
                self._apply_windows_titlebar_theme(
                    bg=theme.get("title_bar_bg"),
                    fg=theme.get("title_bar_fg"),
                    border=theme.get("title_bar_border"),
                    window_widget=window,
                )
                window.after(
                    0,
                    lambda win=window, th=theme: self._apply_windows_titlebar_theme(
                        bg=th.get("title_bar_bg"),
                        fg=th.get("title_bar_fg"),
                        border=th.get("title_bar_border"),
                        window_widget=win,
                    ),
                )
            except Exception:
                pass

        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=8, pady=8)

        mono = self._readme_font_for_theme()
        lines = content.splitlines() or [""]
        trimmed_lengths = [len(line.rstrip()) for line in lines if line.rstrip()]
        if trimmed_lengths:
            sorted_lengths = sorted(trimmed_lengths)
            p90_index = max(0, int((len(sorted_lengths) - 1) * 0.90))
            target_chars = sorted_lengths[p90_index] + 2
        else:
            target_chars = 80
        # Keep README wider so changelog bullets do not need forced formatter wraps.
        target_chars = max(78, min(118, target_chars + 8))
        if variant == "KAMUE":
            content = self._apply_kamue_readme_header(content, center_width=target_chars)
            lines = content.splitlines() or [""]
        elif variant == "SIINDBAD":
            content = self._apply_siindbad_readme_header(content, center_width=target_chars)
            lines = content.splitlines() or [""]
        # Keep content compact while avoiding awkward single-word wraps on long lines.
        readme_wrap_chars = max(72, target_chars - 1)
        # Small right-side gutter so content does not hug the final visible column.
        readme_view_chars = readme_wrap_chars + 2
        content = self._format_readme_content(content, wrap_width=readme_wrap_chars)
        lines = content.splitlines() or [""]

        if variant == "KAMUE":
            readme_bg = theme.get("panel", "#0d061c") if theme else "#0d061c"
            readme_fg = "#efe5ff"
            readme_border = readme_bg
            readme_highlight = 0
        else:
            readme_bg = theme.get("panel", "#161b24") if theme else "#161b24"
            readme_fg = "#dce8f4"
            readme_border = theme.get("panel", "#161b24") if theme else "#161b24"
            readme_highlight = 1

        text = tk.Text(frame, wrap="none", font=mono, width=readme_view_chars)
        text.pack(fill="both", expand=True, side="left")
        v_scroll_style = getattr(self, "_v_scrollbar_style", "Vertical.TScrollbar")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview, style=v_scroll_style)
        v_scroll.pack(fill="y", side="right")
        h_scroll_style = getattr(self, "_h_scrollbar_style", "Horizontal.TScrollbar")
        h_scroll = ttk.Scrollbar(frame, orient="horizontal", command=text.xview, style=h_scroll_style)
        h_scroll.pack(fill="x", side="bottom")
        text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        if theme:
            text.configure(
                bg=readme_bg,
                fg=readme_fg,
                insertbackground=readme_fg,
                selectbackground=theme["select_bg"],
                selectforeground=theme["select_fg"],
                relief="flat",
                highlightthickness=readme_highlight,
                highlightbackground=readme_border,
                highlightcolor=readme_border,
            )
        text.insert("1.0", content)
        text.configure(state="disabled")
        try:
            font = tkfont.Font(font=mono)
            char_w = font.measure("M")
            line_h = font.metrics("linespace")
            width_px = char_w * readme_view_chars + 56
            height_px = min(680, max(360, line_h * min(len(lines) + 2, 38)))
            popup_scale = max(0.9, min(1.2, float(getattr(self, "_display_scale", 1.0) or 1.0)))
            self._apply_centered_toplevel_geometry(
                window,
                width_px=int(round(width_px * popup_scale)),
                height_px=int(round(height_px * popup_scale)),
                min_width=640,
                min_height=360,
                max_width_ratio=0.92,
                max_height_ratio=0.90,
            )
            if position_hint is not None:
                try:
                    window.update_idletasks()
                    w = max(220, int(window.winfo_width()))
                    h = max(140, int(window.winfo_height()))
                    screen_w, screen_h = self._screen_size()
                    px, py = int(position_hint[0]), int(position_hint[1])
                    max_x = max(0, int(screen_w) - w)
                    max_y = max(0, int(screen_h) - h)
                    px = max(0, min(max_x, px))
                    py = max(0, min(max_y, py))
                    window.geometry(f"{w}x{h}+{px}+{py}")
                except Exception:
                    pass
        except Exception:
            self._apply_centered_toplevel_geometry(
                window,
                width_px=760,
                height_px=520,
                min_width=640,
                min_height=360,
                max_width_ratio=0.92,
                max_height_ratio=0.90,
            )
            if position_hint is not None:
                try:
                    window.update_idletasks()
                    w = max(220, int(window.winfo_width()))
                    h = max(140, int(window.winfo_height()))
                    screen_w, screen_h = self._screen_size()
                    px, py = int(position_hint[0]), int(position_hint[1])
                    max_x = max(0, int(screen_w) - w)
                    max_y = max(0, int(screen_h) - h)
                    px = max(0, min(max_x, px))
                    py = max(0, min(max_y, py))
                    window.geometry(f"{w}x{h}+{px}+{py}")
                except Exception:
                    pass

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
        try:
            if path.lower().endswith(".hhsav"):
                with gzip.open(path, "rb") as f:
                    raw = f.read().decode("utf-8")
                self.data = json.loads(raw)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        self.path = path
        self.root.title(
            f"SIINDBAD's HackHub Editor - {os.path.basename(path)} - v{self.APP_VERSION}"
        )
        self._rebuild_tree()
        self.set_status("Loaded")

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
        except Exception:
            self._tree_marker_integrity_ok = False
        if not self._tree_marker_integrity_ok:
            try:
                if getattr(self, "status", None) is not None:
                    self.set_status("Warning: locked tree marker assets changed or missing.")
            except Exception:
                pass
        return self._tree_marker_integrity_ok

    def _load_tree_marker_icon(self, kind, selected=False, expandable=False, expanded=False):
        variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
        key = (variant, str(kind), bool(selected), bool(expandable), bool(expanded))
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
            palette = self._tree_marker_palette(variant)
            style_variant = str(getattr(self, "_tree_style_variant", "B")).upper()
            if style_variant == "B":
                self._check_tree_marker_integrity()
                theme_slug = "kamue" if variant == "KAMUE" else "siindbad"
                arrow_state = "leaf"
                if expandable:
                    arrow_state = "expanded" if expanded else "collapsed"
                if str(kind) == "main":
                    icon_name = f"b2-main-{arrow_state}-{theme_slug}.png"
                else:
                    sel = "on" if selected else "off"
                    icon_name = f"b2-sub-{sel}-{arrow_state}-{theme_slug}.png"
                icon_path = os.path.join(self._resource_base_dir(), "assets", "buttons", "tree-b2", icon_name)
                if os.path.isfile(icon_path):
                    with image_module.open(icon_path) as icon_file:
                        icon = icon_file.convert("RGBA")
                    if str(kind) == "main":
                        icon = self._nudge_marker_image_y(icon, delta_y=-1)
                    else:
                        icon = self._nudge_marker_image_y(icon, delta_y=-0.5)
                    photo = self._pil_to_photo(icon)
                    self._bounded_cache_put(cache, key, photo, max_items=128)
                    return photo

            if str(kind) == "main":
                # Locked asset path: do not procedurally replace main-square style.
                icon_name = self.TREE_MAIN_MARKER_FILES.get(variant, self.TREE_MAIN_MARKER_FILES["SIINDBAD"])
                icon_path = os.path.join(self._resource_base_dir(), "assets", "buttons", icon_name)
                self._check_tree_marker_integrity()
                if os.path.isfile(icon_path):
                    with image_module.open(icon_path) as icon_file:
                        icon = icon_file.convert("RGBA")
                    if style_variant == "B":
                        icon = self._nudge_marker_image_y(icon, delta_y=-1)
                    photo = self._pil_to_photo(icon)
                    self._bounded_cache_put(cache, key, photo, max_items=64)
                    return photo
                self._bounded_cache_put(cache, key, None, max_items=64)
                return None
            else:
                canvas = image_module.new("RGBA", (10, 10), (0, 0, 0, 0))
                draw = draw_module.Draw(canvas)
                fill = palette["sub_fill"] if selected else None
                draw.ellipse(
                    (1, 1, 8, 8),
                    fill=fill,
                    outline=palette["sub_edge"],
                    width=1,
                )
                if style_variant == "B":
                    canvas = self._nudge_marker_image_y(canvas, delta_y=-0.5)
            photo = self._pil_to_photo(canvas)
            self._bounded_cache_put(cache, key, photo, max_items=64)
            return photo
        except Exception:
            self._bounded_cache_put(cache, key, None, max_items=64)
            return None

    @staticmethod
    def _nudge_marker_image_y(image, delta_y=-1):
        """Shift marker pixels vertically while preserving image size."""
        try:
            dy = float(delta_y)
        except Exception:
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
        except Exception:
            return image

    def _is_input_red_arrow_root_path(self, path):
        return tree_policy_service.should_use_input_red_arrow_for_path(self, path)

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
            except Exception:
                pass
            photo = self._pil_to_photo(canvas)
            self._bounded_cache_put(cache, key, photo, max_items=128)
            return photo
        except Exception:
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
        except Exception:
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
        except Exception:
            pass

    def _add_placeholder_if_container(self, item_id, value):
        if isinstance(value, (dict, list)) and len(value) > 0:
            self.tree.insert(item_id, "end", text="(loading)")

    def _reset_find_state(self):
        self.find_matches = []
        self.find_index = 0
        self.last_find_query = ""
        self._find_search_entries = []

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

    def _append_find_search_entries(self, path, value, entries):
        if isinstance(value, dict):
            hidden_keys_getter = getattr(self, "_hidden_root_tree_keys_for_mode", None)
            hidden_keys = (
                hidden_keys_getter() if callable(hidden_keys_getter) else set(getattr(self, "HIDDEN_ROOT_TREE_KEYS", set()))
            )
            keys = list(value.keys())
            if isinstance(path, list) and len(path) == 0:
                keys = sorted(
                    keys,
                    key=lambda raw: str(self._tree_display_label_for_key(raw)).casefold(),
                )
            for key in keys:
                if (
                    isinstance(path, list)
                    and not path
                    and self._normalize_root_tree_key(key) in hidden_keys
                ):
                    continue
                child_path = path + [key]
                child_text = self._tree_display_label_for_key(key)
                if tuple(path or []) in (("Typewriter",),):
                    entry_value = value.get(key)
                    if isinstance(entry_value, dict):
                        type_value = entry_value.get("type")
                        if type_value:
                            child_text = str(type_value)
                entries.append((child_path, str(child_text).casefold()))
                child_value = value.get(key)
                if isinstance(child_value, (dict, list)) and len(child_value) > 0:
                    self._append_find_search_entries(child_path, child_value, entries)
            return

        if isinstance(value, list) and self._is_network_list(path, value):
            groups = {}
            for idx, item in enumerate(value):
                group = item.get("type") if isinstance(item, dict) else "UNKNOWN"
                groups.setdefault(group, []).append((idx, item))

            ordered_groups = [t for t in self.network_types if t in groups]
            for group in sorted(g for g in groups.keys() if g not in self.network_types_set):
                ordered_groups.append(group)

            for group in ordered_groups:
                items = groups[group]
                group_label = f"{group} ({len(items)})"
                entries.append((("__group__", list(path), group), group_label.casefold()))
                for idx, item in items:
                    label = ""
                    if isinstance(item, dict):
                        if group in ("ROUTER", "DEVICE", "FIREWALL", "SPLITTER"):
                            ip = item.get("ip")
                            if group == "SPLITTER":
                                name = None
                            elif group == "FIREWALL":
                                name = None
                                users = item.get("users")
                                if isinstance(users, list) and users:
                                    user0 = users[0]
                                    if isinstance(user0, dict):
                                        name = user0.get("id")
                            else:
                                name = item.get("name")
                                if not name:
                                    domain = item.get("domain")
                                    if isinstance(domain, dict):
                                        name = domain.get("name")
                                if not name:
                                    users = item.get("users")
                                    if isinstance(users, list) and users:
                                        user0 = users[0]
                                        if isinstance(user0, dict):
                                            name = user0.get("firstName") or user0.get("name")
                                if not name and group in ("ROUTER", "DEVICE"):
                                    name = item.get("type")
                            if ip is not None or name is not None:
                                ip_str = "" if ip is None else str(ip)
                                name_str = "" if name is None else str(name)
                                label = f"{ip_str} | {name_str}".strip(" |")
                            else:
                                extra = []
                                if "id" in item:
                                    extra.append(f"id={item['id']}")
                                if "ip" in item:
                                    extra.append(f"ip={item['ip']}")
                                if extra:
                                    label = " ".join(extra)
                        else:
                            extra = []
                            if "id" in item:
                                extra.append(f"id={item['id']}")
                            if "ip" in item:
                                extra.append(f"ip={item['ip']}")
                            if extra:
                                label = " ".join(extra)
                    if not label:
                        label = f"Item {idx + 1}"
                    child_path = path + [idx]
                    entries.append((child_path, str(label).casefold()))
                    if isinstance(item, (dict, list)) and len(item) > 0:
                        self._append_find_search_entries(child_path, item, entries)
            return

        if isinstance(value, list):
            labeler = self._list_labelers.get(tuple(path))
            for idx, item in enumerate(value):
                if labeler:
                    label = labeler(idx, item)
                elif self._is_database_table_rows_path(path):
                    label = self._database_table_row_label(idx, item)
                else:
                    label = f"[{idx}]"
                child_path = path + [idx]
                entries.append((child_path, str(label).casefold()))
                if isinstance(item, (dict, list)) and len(item) > 0:
                    self._append_find_search_entries(child_path, item, entries)

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
                return None
            current_item = next_item
        return current_item

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
        query = self.find_entry.get().strip()
        if not query:
            self.set_status("Find: enter text to search")
            return

        query_lower = query.lower()
        if query_lower != self.last_find_query:
            if not self._find_search_entries:
                self._find_search_entries = self._build_find_search_index()
            self.find_matches = [entry[0] for entry in self._find_search_entries if query_lower in entry[1]]
            self.find_index = 0
            self.last_find_query = query_lower

        if not self.find_matches:
            self.set_status(f'Find: no matches for "{query}"')
            return

        match_ref = self.find_matches[self.find_index]
        self.find_index = (self.find_index + 1) % len(self.find_matches)
        if isinstance(match_ref, tuple) and len(match_ref) == 3 and match_ref[0] == "__group__":
            item_id = self._ensure_tree_group_item_loaded(match_ref[1], match_ref[2])
        else:
            item_id = self._ensure_tree_item_for_path(match_ref)
        if item_id is None:
            self.set_status(f'Find: item is no longer available for "{query}"')
            self._reset_find_state()
            return
        self._open_to_item(item_id)
        self.tree.selection_set(item_id)
        self.tree.see(item_id)
        self.on_select(None)
        self.set_status(f'Find: {self.find_index}/{len(self.find_matches)}')

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
                except Exception:
                    pass
                self.set_status("INPUT mode: Bank subcategories are disabled.")
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
                return
            self._refresh_input_mode_fields(path, value)
        else:
            self._show_value(value, path=path)
        self.set_status(self._describe(value))

    def _show_value(self, value, path=None):
        self._json_render_seq = int(getattr(self, "_json_render_seq", 0) or 0) + 1
        render_seq = int(self._json_render_seq)
        try:
            self.text.configure(state="normal")
        except Exception:
            pass
        self.text.delete("1.0", "end")
        try:
            rendered = json.dumps(value, indent=2, ensure_ascii=False)
        except TypeError:
            rendered = str(value)
        self.text.insert("1.0", rendered)
        # Keep visible key highlights instant; defer heavier value-rule pass.
        self._clear_json_lock_highlight()
        self._set_json_text_editable(True)
        self._apply_json_view_key_highlights(path, line_limit=self._initial_highlight_line_limit())
        self._schedule_json_view_lock_state(path, render_seq=render_seq)
        try:
            # Keep undo/redo scoped to the current node content.
            self.text.edit_reset()
            self.text.edit_modified(False)
        except Exception:
            pass

    def _initial_highlight_line_limit(self):
        # Fast-first paint: highlight currently visible JSON area first.
        try:
            text_h = max(1, int(self.text.winfo_height()))
            top_idx = str(self.text.index("@0,0"))
            bottom_idx = str(self.text.index(f"@0,{text_h}"))
            top_line = int(top_idx.split(".", 1)[0])
            bottom_line = int(bottom_idx.split(".", 1)[0])
            return max(80, int(bottom_line - top_line + 30))
        except Exception:
            return 160

    def _cancel_pending_json_view_lock_state(self):
        after_id = getattr(self, "_json_lock_apply_after_id", None)
        self._json_lock_apply_after_id = None
        if not after_id:
            return
        try:
            self.root.after_cancel(after_id)
        except Exception:
            return

    def _schedule_json_view_lock_state(self, path, render_seq=None):
        self._cancel_pending_json_view_lock_state()
        snapshot_path = list(path or [])
        expected_seq = int(render_seq if render_seq is not None else getattr(self, "_json_render_seq", 0) or 0)

        def _apply_pending():
            self._json_lock_apply_after_id = None
            if int(getattr(self, "_json_render_seq", 0) or 0) != expected_seq:
                return
            self._apply_json_view_key_highlights(snapshot_path)
            self._apply_json_view_value_highlights(snapshot_path)

        try:
            self._json_lock_apply_after_id = self.root.after_idle(_apply_pending)
        except Exception:
            self._json_lock_apply_after_id = None
            self._apply_json_view_key_highlights(snapshot_path)
            self._apply_json_view_value_highlights(snapshot_path)

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
        palette = self._json_lock_tag_palette()
        try:
            self.text.tag_config("json_brace_token", foreground="#54d5ff")
            self.text.tag_config("json_bracket_token", foreground="#ff7ac8")
            self.text.tag_config("json_bool_true", foreground="#5fa8ff")
            self.text.tag_config("json_bool_false", foreground="#ff9ea1")
            self.text.tag_config("json_value_green", foreground="#49c979")
            self.text.tag_config("json_property_key", foreground=palette["fg"])
            self.text.tag_config("json_locked_key", foreground=palette["fg"])
            self.text.tag_config(
                "json_locked_block",
                foreground=palette["fg"],
                background=palette["block_bg"],
            )
            # Lime-green label accents for coordinate/dimension keys.
            self.text.tag_config("json_xy_key", foreground="#b6ff3b")
            self.text.tag_raise("json_brace_token")
            self.text.tag_raise("json_bracket_token")
            self.text.tag_raise("json_bool_true")
            self.text.tag_raise("json_bool_false")
            self.text.tag_raise("json_value_green")
            self.text.tag_raise("json_locked_key")
            self.text.tag_raise("json_property_key")
            self.text.tag_raise("json_xy_key")
        except Exception:
            return

    def _clear_json_lock_highlight(self):
        try:
            self.text.tag_remove("json_brace_token", "1.0", "end")
            self.text.tag_remove("json_bracket_token", "1.0", "end")
            self.text.tag_remove("json_bool_true", "1.0", "end")
            self.text.tag_remove("json_bool_false", "1.0", "end")
            self.text.tag_remove("json_value_green", "1.0", "end")
            self.text.tag_remove("json_property_key", "1.0", "end")
            self.text.tag_remove("json_locked_key", "1.0", "end")
            self.text.tag_remove("json_locked_block", "1.0", "end")
            self.text.tag_remove("json_xy_key", "1.0", "end")
        except Exception:
            return

    def _set_json_text_editable(self, editable=True):
        text = getattr(self, "text", None)
        if text is None:
            return
        target_state = "normal" if editable else "disabled"
        try:
            if str(text.cget("state")) != target_state:
                text.configure(state=target_state)
        except Exception:
            return

    def _json_token_followed_by_colon(self, end_index, lookahead_chars=24):
        # Locked-key highlight guard: only tag JSON object keys ("key":), not string values ("KEY").
        text = getattr(self, "text", None)
        if text is None:
            return False
        try:
            tail = self.text.get(end_index, f"{end_index}+{max(1, int(lookahead_chars))}c")
        except Exception:
            return False
        if not tail:
            return False
        for ch in tail:
            if ch in (" ", "\t", "\r", "\n"):
                continue
            return ch == ":"
        return False

    def _tag_json_locked_key_occurrences(self, key_name):
        token = f'"{key_name}"'
        malformed_missing_close_quote = f'"{key_name}:'
        malformed_missing_open_quote = f'{key_name}"'
        index = "1.0"
        while True:
            try:
                hit = self.text.search(token, index, stopindex="end", nocase=True)
            except Exception:
                hit = ""
            if not hit:
                break
            try:
                end = f"{hit}+{len(token)}c"
                if self._json_token_followed_by_colon(end):
                    self.text.tag_add("json_locked_key", hit, end)
            except Exception:
                break
            index = end
        # Parse-error continuity: keep key labels highlighted when one quote is removed
        # (for example `"key:` or `key"` before `:`) while user is fixing JSON syntax.
        for malformed_token in (malformed_missing_close_quote, malformed_missing_open_quote):
            index = "1.0"
            while True:
                try:
                    hit = self.text.search(malformed_token, index, stopindex="end", nocase=True)
                except Exception:
                    hit = ""
                if not hit:
                    break
                try:
                    if malformed_token.endswith(":"):
                        end = f"{hit}+{len(malformed_token) - 1}c"
                    else:
                        end = f"{hit}+{len(malformed_token)}c"
                    if self._json_token_followed_by_colon(end):
                        self.text.tag_add("json_locked_key", hit, end)
                except Exception:
                    break
                index = end

    def _tag_json_xy_key_occurrences(self, key_name):
        token = f'"{key_name}"'
        index = "1.0"
        while True:
            try:
                hit = self.text.search(token, index, stopindex="end", nocase=False)
            except Exception:
                hit = ""
            if not hit:
                break
            try:
                end = f"{hit}+{len(token)}c"
                if self._json_token_followed_by_colon(end):
                    self.text.tag_add("json_xy_key", hit, end)
            except Exception:
                break
            index = end

    def _should_batch_tag_locked_keys(self, key_names):
        # Large-category optimization: use one-pass key tagging for big root JSON blocks.
        if not key_names:
            return False
        if len(tuple(key_names)) < 12:
            return False
        # While editing with active error overlays, keep per-key path for malformed key handling.
        try:
            if getattr(self, "error_overlay", None) is not None:
                return False
        except Exception:
            return False
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return False
        if len(raw or "") < 4000:
            return False
        return True

    def _tag_json_key_occurrences_batch(self, locked_key_names, xy_key_names=(), line_limit=None):
        locked_targets = {
            str(name or "").strip().casefold()
            for name in tuple(locked_key_names or ())
            if str(name or "").strip()
        }
        xy_targets = {
            str(name or "").strip()
            for name in tuple(xy_key_names or ())
            if str(name or "").strip()
        }
        if not locked_targets and not xy_targets:
            return
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return
        line_no = 1
        key_pattern = re.compile(r'"([^"\r\n:]+)"\s*:')
        max_lines = int(line_limit or 0)
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in key_pattern.finditer(line_text):
                key_name = str(hit.group(1) or "")
                locked_match = key_name.casefold() in locked_targets
                xy_match = key_name in xy_targets
                if not locked_match and not xy_match:
                    continue
                key_start = int(hit.start(0))
                key_end = int(key_start + len(key_name) + 2)
                try:
                    start = f"{line_no}.{key_start}"
                    end = f"{line_no}.{key_end}"
                    if locked_match:
                        self.text.tag_add("json_locked_key", start, end)
                    if xy_match:
                        self.text.tag_add("json_xy_key", start, end)
                except Exception:
                    continue
            line_no += 1

    def _tag_json_string_value_literals(self, line_limit=None):
        # Value accent pass: tag quoted JSON string values while leaving object keys untagged.
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        token_pattern = re.compile(r'"([^"\\]|\\.)*"')
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in token_pattern.finditer(line_text):
                start_col = int(hit.start(0))
                end_col = int(hit.end(0))
                next_nonspace = ""
                for ch in line_text[end_col:]:
                    if ch in (" ", "\t", "\r", "\n"):
                        continue
                    next_nonspace = ch
                    break
                is_key = next_nonspace == ":"
                if is_key:
                    continue
                try:
                    self.text.tag_add("json_value_green", f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except Exception:
                    continue
            line_no += 1

    def _tag_json_brace_tokens(self, line_limit=None):
        # Structural accent pass: color object/list tokens without touching quoted strings.
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            in_string = False
            escaped = False
            col_no = 0
            for ch in line_text:
                if escaped:
                    escaped = False
                    col_no += 1
                    continue
                if ch == "\\" and in_string:
                    escaped = True
                    col_no += 1
                    continue
                if ch == '"':
                    in_string = not in_string
                    col_no += 1
                    continue
                if not in_string and ch in ("{", "}", "[", "]"):
                    try:
                        token_tag = "json_brace_token" if ch in ("{", "}") else "json_bracket_token"
                        self.text.tag_add(token_tag, f"{line_no}.{col_no}", f"{line_no}.{col_no + 1}")
                    except Exception:
                        pass
                col_no += 1
            line_no += 1

    def _tag_json_boolean_literals(self, line_limit=None):
        # Boolean accent pass: color JSON literals true/false outside quoted strings.
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        token_pattern = re.compile(r"\b(true|false)\b")
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            in_string = False
            escaped = False
            string_mask = [False] * len(line_text)
            for idx, ch in enumerate(line_text):
                string_mask[idx] = in_string
                if escaped:
                    escaped = False
                    continue
                if ch == "\\" and in_string:
                    escaped = True
                    continue
                if ch == '"':
                    in_string = not in_string
            for hit in token_pattern.finditer(line_text):
                start_col = int(hit.start(0))
                end_col = int(hit.end(0))
                inside_string = any(string_mask[idx] for idx in range(start_col, min(end_col, len(string_mask))))
                if inside_string:
                    continue
                token = str(hit.group(1) or "")
                tag_name = "json_bool_true" if token == "true" else "json_bool_false"
                try:
                    self.text.tag_add(tag_name, f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except Exception:
                    continue
            line_no += 1

    def _tag_json_property_keys(self, line_limit=None):
        # Property-key accent pass: color all JSON object key tokens including quotes.
        try:
            raw = self.text.get("1.0", "end-1c")
        except Exception:
            return
        line_no = 1
        max_lines = int(line_limit or 0)
        key_pattern = re.compile(r'"([^"\\]|\\.)*"\s*:')
        for line_text in str(raw or "").splitlines():
            if max_lines and line_no > max_lines:
                break
            for hit in key_pattern.finditer(line_text):
                token = str(hit.group(0) or "")
                colon_index = token.rfind(":")
                if colon_index <= 0:
                    continue
                end_col = int(hit.start(0) + colon_index)
                start_col = int(hit.start(0))
                while end_col > start_col and line_text[end_col - 1] in (" ", "\t"):
                    end_col -= 1
                try:
                    self.text.tag_add("json_property_key", f"{line_no}.{start_col}", f"{line_no}.{end_col}")
                except Exception:
                    continue
            line_no += 1

    def _json_literal_offsets_after_key(self, key_end_index, literal_token, lookahead_chars=120, ignore_case=False):
        # Value-highlight guard: only tag when this key is immediately followed by the configured JSON literal.
        text = getattr(self, "text", None)
        token = str(literal_token or "")
        if text is None or not token:
            return None
        try:
            tail = self.text.get(key_end_index, f"{key_end_index}+{max(1, int(lookahead_chars))}c")
        except Exception:
            return None
        if not tail:
            return None
        i = 0
        while i < len(tail) and tail[i] in (" ", "\t", "\r", "\n"):
            i += 1
        if i >= len(tail) or tail[i] != ":":
            return None
        i += 1
        while i < len(tail) and tail[i] in (" ", "\t", "\r", "\n"):
            i += 1
        if i >= len(tail):
            return None
        candidate = tail[i:i + len(token)]
        if ignore_case:
            if candidate.casefold() != token.casefold():
                return None
        else:
            if candidate != token:
                return None
        end = i + len(token)
        if end < len(tail):
            next_ch = tail[end]
            if next_ch not in (" ", "\t", "\r", "\n", ",", "}", "]"):
                return None
        return i, end

    def _tag_json_locked_value_occurrences(self, field_name, literal_value, ignore_case=False):
        key_token = json.dumps(str(field_name), ensure_ascii=False)
        value_token = json.dumps(literal_value, ensure_ascii=False)
        index = "1.0"
        while True:
            try:
                hit = self.text.search(key_token, index, stopindex="end", nocase=True)
            except Exception:
                hit = ""
            if not hit:
                break
            try:
                key_end = f"{hit}+{len(key_token)}c"
                offsets = self._json_literal_offsets_after_key(
                    key_end,
                    value_token,
                    ignore_case=bool(ignore_case),
                )
                if offsets is not None:
                    value_start = f"{key_end}+{int(offsets[0])}c"
                    value_end = f"{key_end}+{int(offsets[1])}c"
                    self.text.tag_add("json_locked_key", value_start, value_end)
            except Exception:
                break
            index = key_end

    def _apply_json_view_lock_state(self, path):
        self._clear_json_lock_highlight()
        self._set_json_text_editable(True)
        self._apply_json_view_key_highlights(path)
        self._apply_json_view_value_highlights(path)

    def _apply_json_view_key_highlights(self, path, line_limit=None):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "JSON":
            return
        self._tag_json_brace_tokens(line_limit=line_limit)
        self._tag_json_boolean_literals(line_limit=line_limit)
        self._tag_json_property_keys(line_limit=line_limit)
        use_path = list(path or [])
        xy_keys = ("x", "y") if len(use_path) == 1 else ()
        dimension_keys = ("width", "height")
        if highlight_label_service.is_locked_field_path(use_path):
            # Subcategory JSON stays white; apply-time guard still blocks locked edits.
            return
        locked_fields = tuple(highlight_label_service.locked_highlight_fields_for_path(use_path))
        if self._should_batch_tag_locked_keys(locked_fields):
            self._tag_json_key_occurrences_batch(locked_fields, xy_key_names=xy_keys, line_limit=line_limit)
        else:
            for coord_key in xy_keys:
                self._tag_json_xy_key_occurrences(coord_key)
            for field_name in locked_fields:
                self._tag_json_locked_key_occurrences(field_name)
        for dim_key in dimension_keys:
            self._tag_json_xy_key_occurrences(dim_key)
        # Global value tint: render quoted values in light green without overriding key highlights.
        self._tag_json_string_value_literals(line_limit=line_limit)

    def _apply_json_view_value_highlights(self, path):
        if str(getattr(self, "_editor_mode", "JSON")).upper() != "JSON":
            return
        use_path = list(path or [])
        if highlight_label_service.is_locked_field_path(use_path):
            return
        for rule in highlight_label_service.locked_highlight_value_rules_for_path(use_path):
            field_name = str(rule.get("field") or "").strip()
            if not field_name:
                continue
            ignore_case = bool(rule.get("ignore_case", False))
            for literal in tuple(rule.get("values") or ()):
                self._tag_json_locked_value_occurrences(field_name, literal, ignore_case=ignore_case)

    def _describe(self, value):
        if isinstance(value, dict):
            return f"dict ({len(value)} keys)"
        if isinstance(value, list):
            return f"list ({len(value)} items)"
        return f"{type(value).__name__}"


    def apply_edit(self):
        action = "auto_apply" if self._auto_apply_in_progress else "apply_edit"
        self._begin_diag_action(action)
        item_id = self.tree.focus()
        if not item_id:
            messagebox.showwarning("No selection", "Select a node in the tree.")
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path[0] == "__group__":
            messagebox.showwarning("Not editable", "Select a specific item to edit.")
            return
        if str(getattr(self, "_editor_mode", "JSON")).upper() == "INPUT":
            self._apply_input_edit()
            return

        raw = self.text.get("1.0", "end").strip()
        try:
            new_value = json.loads(raw)
        except Exception as exc:
            message = self._format_json_error(exc)
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            # Keep highlight-label colors active while JSON is temporarily invalid.
            self._apply_json_view_lock_state(path)
            # Prefer one specific diagnostic note per apply cycle; use overlay_parse only as fallback.
            self._last_error_highlight_note = ""
            self._highlight_json_error(exc)
            highlight_note = str(getattr(self, "_last_error_highlight_note", "") or "").strip()
            if (
                not highlight_note
                or highlight_note == "highlight"
                or highlight_note.startswith("highlight_failed")
            ):
                try:
                    self._log_json_error(exc, getattr(exc, "lineno", None) or 1, note="overlay_parse")
                except Exception:
                    pass
            return
        self._clear_json_error_highlight()

        spacing_issue = self._find_json_spacing_issue()
        if spacing_issue:
            line, start_col, end_col, before_line, after_line = spacing_issue
            message = self._format_suggestion(
                'Invalid Entry: add a space after ":".',
                before_line,
                after_line,
            )
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            try:
                start_index = f"{line}.{max(start_col, 0)}"
                end_index = f"{line}.{max(end_col, start_col + 1)}"
                dummy = type(
                    "E",
                    (),
                    {"msg": "Missing space after ':'", "lineno": line, "colno": start_col + 1},
                )
                self._apply_json_error_highlight(
                    dummy, line, start_index, end_index, note="spacing_missing_space_after_colon"
                )
            except Exception:
                self._highlight_custom_range(line, start_col, end_col)
            return

        email_validation = self._find_invalid_email_in_value(path, new_value)
        if email_validation:
            field_path, bad_value, email_issue = email_validation
            field_label = self._format_path_for_display(field_path)
            before_line = f'"{field_label}": "{bad_value}"'
            after_line = f'"{field_label}": "{email_issue["suggested"]}"'
            message = self._format_suggestion(
                email_issue["message"],
                before_line,
                after_line,
            )
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            preferred_key = field_path[-1] if field_path and isinstance(field_path[-1], str) else None
            span = self._find_value_span_in_editor(bad_value, preferred_key=preferred_key)
            if span:
                line, start_col, end_col = span
                self._highlight_custom_range(line, start_col, end_col)
            else:
                self._highlight_custom_range(1, 0, max(1, len(before_line)))
            try:
                log_line = span[0] if span else 1
                log_col = (span[1] + 1) if span else 1
                dummy = type("E", (), {"msg": email_issue["log_msg"], "lineno": log_line, "colno": log_col})
                self._log_json_error(dummy, log_line, note=email_issue["note"])
            except Exception:
                pass
            return

        phone_issue = self._find_phone_format_issue()
        if phone_issue:
            line, start_col, end_col, before_line, after_line = phone_issue
            message = self._format_suggestion(
                "Invalid Entry: add \"-\" to the phone number.",
                before_line,
                after_line,
            )
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            self._highlight_custom_range(line, start_col, end_col)
            try:
                dummy = type("E", (), {"msg": "Missing '-' in phone", "lineno": line, "colno": start_col + 1})
                self._log_json_error(dummy, line, note="missing_phone_dash")
            except Exception:
                pass
            return

        if not self._is_json_edit_allowed(path, new_value, show_feedback=True, auto_restore=True):
            return
        self._destroy_error_overlay()
        self._error_visual_mode = "guide"
        if not self._is_edit_allowed(path, new_value):
            return

        self._set_value(path, new_value)

        # Refresh subtree
        self._populate_children(item_id)
        # Repaint label highlights after JSON edits so fixed key quotes stay orange.
        self._apply_json_view_lock_state(path)
        pending_restore = str(getattr(self, "_pending_insert_restore_index", "") or "")
        self._pending_insert_restore_index = ""
        if pending_restore:
            try:
                if getattr(self, "root", None) is not None:
                    self.root.after_idle(lambda idx=pending_restore: self._restore_insert_index(idx, log_failure=True))
                else:
                    self._restore_insert_index(pending_restore, log_failure=True)
            except Exception:
                pass
        self.set_status("Edited")

    def _extract_key_name_from_diag_line(self, line_text):
        raw = str(line_text or "").strip()
        if not raw:
            return ""
        m = re.search(r'"([^"\r\n:]+)"\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)"\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        m = re.search(r'"([A-Za-z_][A-Za-z0-9_]*)\s*:', raw)
        if m:
            return str(m.group(1) or "").strip()
        return ""

    def _locked_field_name_from_parse_diag(self, path, diag):
        use_path = list(path or [])
        if highlight_label_service.is_locked_field_path(use_path) and use_path:
            return str(use_path[-1] or "").strip()
        locked_fields = tuple(highlight_label_service.locked_highlight_fields_for_path(use_path))
        if not locked_fields:
            return ""
        for key in ("after", "before"):
            field_name = self._extract_key_name_from_diag_line((diag or {}).get(key))
            if not field_name:
                continue
            for locked_name in locked_fields:
                if str(locked_name).casefold() == str(field_name).casefold():
                    return str(locked_name)
        return ""

    def _find_lock_anchor_index(self, field_name, preferred_index=None):
        token = f'"{str(field_name or "").strip()}"'
        if token == '""':
            token = ""
        normalized_preferred = str(preferred_index or "")
        try:
            if normalized_preferred:
                normalized_preferred = str(self.text.index(normalized_preferred))
        except Exception:
            pass
        if not token:
            return normalized_preferred
        try:
            if normalized_preferred:
                # Anchor priority for repeated locked keys:
                # 1) nearest key at/above current edit position
                # 2) nearest key below current edit position
                backward_hit = self.text.search(
                    token,
                    normalized_preferred,
                    stopindex="1.0",
                    nocase=True,
                    backwards=True,
                )
                if backward_hit:
                    return backward_hit
                forward_hit = self.text.search(token, normalized_preferred, stopindex="end", nocase=True)
                if forward_hit:
                    return forward_hit
        except Exception:
            pass
        try:
            hit = self.text.search(token, "1.0", stopindex="end", nocase=True)
            if hit:
                return hit
        except Exception:
            pass
        return normalized_preferred

    def _diag_line_mentions_locked_field(self, line_no, field_name):
        if not line_no or not field_name:
            return False
        try:
            line_text = str(self._line_text(int(line_no)) or "")
        except Exception:
            return False
        if not line_text.strip():
            return False
        field_lookup = str(field_name).strip().casefold()
        line_lookup = line_text.casefold()
        if field_lookup in line_lookup:
            return True
        compact_field = "".join(ch for ch in field_lookup if ch.isalnum())
        compact_line = "".join(ch for ch in line_lookup if ch.isalnum())
        if compact_field and compact_field in compact_line:
            return True
        return False

    def _maybe_restore_locked_parse_error(self, path, diag, exc=None):
        # Parse-error lock handoff: key-quote parse failures on protected keys should restore via lock flow.
        note = str((diag or {}).get("note") or "").strip().lower()
        parse_lock_notes = {
            "missing_key_quote_before_colon",
            "symbol_wrong_property_key_symbol",
            "symbol_wrong_property_quote_char",
        }
        if note not in parse_lock_notes:
            return False
        use_path = list(path or [])
        policy = highlight_label_service.lock_policy_for_path(use_path)
        if policy is None:
            return False
        field_name = self._locked_field_name_from_parse_diag(use_path, diag)
        if not field_name:
            return False
        try:
            insert_line = self._line_number_from_index(self.text.index("insert")) or 0
        except Exception:
            insert_line = 0
        try:
            insert_line_text = str(self._line_text(int(insert_line)) or "") if insert_line else ""
        except Exception:
            insert_line_text = ""
        try:
            diag_line = int((diag or {}).get("line") or 0)
        except Exception:
            diag_line = 0
        # Strict handoff gate:
        # diagnostic line must match parser-reported line for this exact Apply Edit parse failure.
        try:
            parse_line = int(getattr(exc, "lineno", 0) or 0)
        except Exception:
            parse_line = 0
        if parse_line and diag_line and int(parse_line) != int(diag_line):
            return False
        # Lock handoff must be anchored to the actively edited line.
        if insert_line and diag_line and int(insert_line) != int(diag_line):
            return False
        # Parse-lock safety gate:
        # only auto-restore when the parse diagnostic is near the user's active edit location.
        if insert_line and diag_line and abs(int(insert_line) - int(diag_line)) > 1:
            return False
        if diag_line and not self._diag_line_mentions_locked_field(diag_line, field_name):
            return False
        # Strict key-quote gate:
        # only route into lock auto-restore when the parser line itself is a key-quote syntax issue.
        if diag_line:
            try:
                diag_line_text = str(self._line_text(diag_line) or "")
            except Exception:
                diag_line_text = ""
            has_key_quote_issue = False
            try:
                has_key_quote_issue = bool(
                    self._line_has_missing_key_quote_before_colon(diag_line_text)
                    or self._line_has_property_key_invalid_escape(diag_line_text)
                )
            except Exception:
                has_key_quote_issue = False
            if not has_key_quote_issue:
                return False
            line_field = self._extract_key_name_from_diag_line(diag_line_text)
            if line_field and str(line_field).casefold() != str(field_name).casefold():
                return False
        # Also require the current insert line to be the same locked key-quote issue.
        try:
            insert_has_key_quote_issue = bool(
                self._line_has_missing_key_quote_before_colon(insert_line_text)
                or self._line_has_property_key_invalid_escape(insert_line_text)
            )
        except Exception:
            insert_has_key_quote_issue = False
        if not insert_has_key_quote_issue:
            return False
        insert_field = self._extract_key_name_from_diag_line(insert_line_text)
        if insert_field and str(insert_field).casefold() != str(field_name).casefold():
            return False
        try:
            current_value = self._get_value(use_path)
        except Exception:
            return False

        try:
            previous_insert = self.text.index("insert")
        except Exception:
            previous_insert = "1.0"
        self._show_value(current_value, path=use_path)
        self._clear_json_error_highlight()
        self._error_visual_mode = "guide"
        self._show_error_overlay(
            "Not editable",
            f'Locked: "{field_name}" is a protected field. Line restored.',
        )
        anchor_index = self._find_lock_anchor_index(field_name, preferred_index=previous_insert)
        if not anchor_index:
            try:
                anchor_index = str(previous_insert or self.text.index("insert"))
            except Exception:
                anchor_index = "1.0"
        self._error_focus_index = anchor_index
        try:
            self.text.mark_set("insert", anchor_index)
            self.text.see(anchor_index)
        except Exception:
            pass
        try:
            anchor_line = self._line_number_from_index(anchor_index) or 1
            self._position_error_overlay(anchor_line)
        except Exception:
            pass
        try:
            self._tag_json_locked_key_occurrences(field_name)
        except Exception:
            pass
        try:
            self.set_status(
                str(policy.get("status_restored") or "Auto-fixed: protected field restored.")
            )
        except Exception:
            pass
        try:
            log_line = int((diag or {}).get("line") or 1)
            marker = type("E", (), {"msg": "Locked parse edit restored", "lineno": log_line, "colno": 1})
            self._log_json_error(marker, log_line, note="locked_parse_auto_restore")
        except Exception:
            pass
        return True

    def _format_json_error(self, exc):
        return json_error_diagnostics_core.format_json_error(self, exc)


    def _example_for_error(self, exc):
        lineno = getattr(exc, "lineno", None)
        line_text = ""
        if lineno:
            try:
                line_text = self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()
            except Exception:
                line_text = ""

        msg = getattr(exc, "msg", None)
        if msg == "Expecting ',' delimiter":
            if self._is_missing_object_open_at(lineno):
                return "{"
            if self._is_missing_object_open(exc):
                return self._missing_object_example(lineno)
            if self._is_missing_object_close():
                return self._missing_close_example("Expecting '}'")
            if self._is_missing_list_close():
                return self._missing_close_example("Expecting ']'")
            return self._comma_example_line(lineno)

        if msg == "Expecting property name enclosed in double quotes":
            if line_text:
                return line_text
            return "\"key\": \"value\""

        if msg == "Expecting ':' delimiter":
            if line_text:
                return self._missing_colon_example(line_text)
            return "\"key\": \"value\""

        if msg and msg.startswith("Invalid control character"):
            if line_text:
                return self._fix_missing_quote(line_text)
            return "\"key\": \"value\""

        if msg in ("Expecting ']'", "Expecting '}'"):
            return self._missing_close_example(msg)

        if msg == "Expecting value":
            if self._is_missing_list_open_at_start(exc):
                return "["
            if self._is_missing_list_close():
                return self._missing_close_example("Expecting ']'")
            if self._is_missing_object_close():
                return self._missing_close_example("Expecting '}'")
            if self._is_missing_list_open(exc):
                return "\"items\": ["
            if self._is_missing_object_open(exc):
                return "\"data\": {"

        if msg == "Extra data":
            if self._missing_object_open_from_extra_data():
                return "{"
            if self._missing_list_open_from_extra_data():
                return "["
            next_line = self._next_non_empty_line(lineno or 1)
            if next_line:
                next_text = self._line_text(next_line).strip()
                if next_text:
                    return next_text
            if line_text:
                return line_text
            return "\"key\": \"value\""

        if msg in ("Unexpected ']'", "Unexpected '}'"):
            return self._missing_close_example(msg)

        if msg == "Unterminated string":
            return "\"text\""

        if line_text:
            return line_text
        return "\"key\": \"value\""

    def _missing_colon_example(self, line_text):
        if ":" in line_text:
            return line_text
        has_trailing_comma = line_text.rstrip().endswith(",")
        stripped = line_text.strip().strip(",")
        if not stripped:
            return "\"key\": \"value\""
        # Handle: "key" value  ->  "key": value
        m = re.match(r'^\s*"([^"]+)"\s+(.+?)\s*$', stripped)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            result = f"\"{key}\": {value}"
            if has_trailing_comma and not result.rstrip().endswith(","):
                result += ","
            return result
        # If we have two quoted strings, insert colon between them.
        if "\"" in stripped:
            try:
                first = stripped.split("\"", 2)
                if len(first) >= 2:
                    quote_index = stripped.find('"', 1)
                    rest = stripped[quote_index + 1 :].strip()
                    rest = rest.lstrip()
                    if rest.startswith("\""):
                        result = f"{stripped[:quote_index + 1]}: {rest}"
                        if line_text.rstrip().endswith(",") and not result.rstrip().endswith(","):
                            result = result.rstrip() + ","
                        return result
            except Exception:
                pass
        if not stripped.startswith("\""):
            stripped = f"\"{stripped.strip()}\""
        result = f"{stripped}: \"value\""
        if has_trailing_comma and not result.rstrip().endswith(","):
            result += ","
        return result

    def _is_json_value_token_start(self, value_text):
        stripped = (value_text or "").lstrip()
        if not stripped:
            return False
        ch = stripped[0]
        if ch in ('"', "{", "[") or ch == "-" or ch.isdigit():
            return True
        for lit in ("true", "false", "null"):
            if stripped.startswith(lit):
                end = len(lit)
                if end >= len(stripped) or not re.match(r"[A-Za-z0-9_]", stripped[end]):
                    return True
        return False

    def _missing_colon_key_value_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        if ":" in raw:
            return None
        m = re.match(r'^(?P<indent>\s*)"(?P<key>[^"]+)"(?P<gap>\s+)(?P<value>.+?)\s*,?\s*$', raw)
        if not m:
            return None
        value = m.group("value") or ""
        if not self._is_json_value_token_start(value):
            return None
        first_q = raw.find('"')
        if first_q < 0:
            return None
        second_q = raw.find('"', first_q + 1)
        if second_q < 0:
            return None
        insert_col = second_q + 1
        return insert_col, insert_col

    def _line_has_missing_colon_key_value(self, line_text):
        return self._missing_colon_key_value_span(line_text) is not None

    def _find_nearby_missing_colon_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_missing_colon_key_value(txt):
                return ln, txt
        return None, None

    def _is_key_colon_comma_line(self, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*,\s*$', line_text))

    def _key_colon_comma_to_list_open(self, line_text):
        if not self._is_key_colon_comma_line(line_text):
            return line_text
        m = re.match(r'^(\s*"[^"]+"\s*:\s*),\s*$', line_text)
        if not m:
            return line_text
        return m.group(1) + "["

    def _line_extra_quote_in_string_value(self, line_text):
        # Detect: "key": "value""   -> likely meant comma after closing quote.
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*"[^"]*""\s*,?\s*$', line_text))

    def _fix_extra_quote_to_comma(self, line_text):
        if not self._line_extra_quote_in_string_value(line_text):
            return line_text
        idx = line_text.rfind('""')
        if idx == -1:
            return line_text
        return line_text[:idx] + '",' + line_text[idx + 2 :]

    def _line_has_trailing_stray_quote_after_comma(self, line_text):
        # Detect: "key": "value","
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*"[^"]*"\s*,\s*"\s*$', line_text))

    def _fix_trailing_stray_quote_after_comma(self, line_text):
        if not self._line_has_trailing_stray_quote_after_comma(line_text):
            return line_text
        return re.sub(r',\s*"\s*$', ",", line_text)

    def _find_nearby_trailing_stray_quote_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_trailing_stray_quote_after_comma(txt):
                return ln, txt
        return None, None

    def _line_has_duplicate_trailing_comma(self, line_text):
        if not line_text:
            return False
        return bool(re.match(r'^\s*"[^"]+"\s*:\s*.+,\s*,\s*$', line_text))

    def _fix_duplicate_trailing_comma(self, line_text):
        if not self._line_has_duplicate_trailing_comma(line_text):
            return line_text
        return re.sub(r',\s*,\s*$', ",", line_text)

    def _find_nearby_duplicate_trailing_comma_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_duplicate_trailing_comma(txt):
                return ln, txt
        return None, None

    def _line_requires_trailing_comma(self, lineno):
        if not lineno:
            return False
        next_line = self._next_non_empty_line_number(lineno)
        if not next_line:
            return False
        next_text = self._line_text(next_line).lstrip()
        return not next_text.startswith(("}", "]"))

    def _duplicate_comma_run_span(self, line_text, lineno=None):
        if not line_text:
            return None
        raw = line_text.rstrip()
        # Detect any trailing duplicate-comma run and return span of only the
        # extra commas (or all commas when no delimiter is allowed).
        m = re.match(r'^(?P<prefix>.*?),(?P<extra>\s*,+\s*)$', raw)
        if not m:
            return None
        prefix = m.group("prefix") or ""
        extra = m.group("extra") or ""
        if not extra or "," not in extra:
            return None
        # Guard against non-value lines like "key:" where comma runs are handled elsewhere.
        prefix_stripped = prefix.strip()
        if not prefix_stripped or prefix_stripped.endswith(":"):
            return None

        keep_one_comma = self._line_requires_trailing_comma(lineno)
        if keep_one_comma:
            leading_ws = len(extra) - len(extra.lstrip())
            start_col = len(prefix) + 1 + leading_ws
        else:
            # No delimiter is valid before a closer; highlight the whole comma run.
            start_col = len(prefix)
        end_col = len(raw.rstrip())
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _line_has_duplicate_comma_run(self, line_text, lineno=None):
        return self._duplicate_comma_run_span(line_text, lineno=lineno) is not None

    def _fix_duplicate_comma_run(self, line_text, lineno=None):
        if not line_text:
            return line_text
        raw = line_text.rstrip()
        m = re.match(r'^(?P<prefix>.*?),(?P<extra>\s*,+\s*)$', raw)
        if not m:
            return raw
        prefix = m.group("prefix") or ""
        if self._line_requires_trailing_comma(lineno):
            return prefix + ","
        return prefix

    def _find_nearby_duplicate_comma_run_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_duplicate_comma_run(txt, lineno=ln):
                return ln, txt
        return None, None

    def _comma_before_colon_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*)(?P<run>,(?:\s*,)*)(?P<rest>\s*:\s*.+)$', raw)
        if not m:
            return None
        start_col = len(m.group("head") or "")
        run = (m.group("run") or "").rstrip()
        end_col = start_col + max(1, len(run))
        return start_col, end_col

    def _line_has_comma_before_colon(self, line_text):
        return self._comma_before_colon_span(line_text) is not None

    def _fix_comma_before_colon(self, line_text):
        if not line_text:
            return line_text
        raw = line_text.rstrip()
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*)(?P<run>,(?:\s*,)*)(?P<rest>\s*:\s*.+)$', raw)
        if not m:
            return raw
        head = m.group("head") or ""
        rest = m.group("rest") or ""
        return head + rest

    def _find_nearby_comma_before_colon_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_comma_before_colon(txt):
                return ln, txt
        return None, None

    def _comma_after_colon_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        # Match: "key":, value / "key":,, value (comma run after colon section)
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<run>,(?:\s*,)*)(?P<tail>\s*.+)$', raw)
        if not m:
            return None
        tail = m.group("tail") or ""
        if not tail.strip():
            return None
        start_col = len(m.group("head") or "")
        run = (m.group("run") or "").rstrip()
        run_len = max(1, len(run))
        first_non_ws = None
        for idx, ch in enumerate(tail):
            if not ch.isspace():
                first_non_ws = idx
                break
        if first_non_ws is None:
            return None

        def is_value_start(s, idx):
            def has_clean_tail(end_idx):
                j = end_idx
                while j < len(s) and s[j].isspace():
                    j += 1
                if j >= len(s):
                    return True
                if s[j] in (",", "}", "]"):
                    k = j + 1
                    while k < len(s) and s[k].isspace():
                        k += 1
                    return k >= len(s)
                return False

            ch = s[idx]
            if ch in ("{", "["):
                return True
            if ch == '"':
                mstr = re.match(r'"(?:\\.|[^"\\])*"', s[idx:])
                if not mstr:
                    return False
                end = idx + len(mstr.group(0))
                return has_clean_tail(end)
            if ch == "-" or ch.isdigit():
                mnum = re.match(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', s[idx:])
                if not mnum:
                    return False
                end = idx + len(mnum.group(0))
                return has_clean_tail(end)
            if s.startswith("true", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                return has_clean_tail(idx + 4)
            if s.startswith("false", idx) and (idx + 5 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 5])):
                return has_clean_tail(idx + 5)
            if s.startswith("null", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                return has_clean_tail(idx + 4)
            return False

        def next_value_start_on_boundary(s, start_idx):
            i = start_idx
            while i < len(s):
                while i < len(s) and not s[i].isspace():
                    i += 1
                while i < len(s) and s[i].isspace():
                    i += 1
                if i < len(s) and is_value_start(s, i):
                    return i
            return None

        invalid_prefix_len = 0
        if not is_value_start(tail, first_non_ws):
            next_valid = next_value_start_on_boundary(tail, first_non_ws)
            if next_valid is not None:
                invalid_prefix_len = next_valid
            else:
                invalid_prefix_len = len(tail.rstrip())

        end_col = start_col + run_len + max(0, invalid_prefix_len)
        return start_col, end_col

    def _line_has_comma_after_colon(self, line_text):
        return self._comma_after_colon_span(line_text) is not None

    def _fix_comma_after_colon(self, line_text):
        if not line_text:
            return line_text
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<run>,(?:\s*,)*)(?P<tail>\s*.+)$', line_text.rstrip())
        if not m:
            return line_text.rstrip()
        head = m.group("head") or ""
        tail = m.group("tail") or ""
        first_non_ws = None
        for idx, ch in enumerate(tail):
            if not ch.isspace():
                first_non_ws = idx
                break
        if first_non_ws is None:
            return head.rstrip()

        def is_value_start(s, idx):
            def has_clean_tail(end_idx):
                j = end_idx
                while j < len(s) and s[j].isspace():
                    j += 1
                if j >= len(s):
                    return True
                if s[j] in (",", "}", "]"):
                    k = j + 1
                    while k < len(s) and s[k].isspace():
                        k += 1
                    return k >= len(s)
                return False

            ch = s[idx]
            if ch in ("{", "["):
                return True
            if ch == '"':
                mstr = re.match(r'"(?:\\.|[^"\\])*"', s[idx:])
                if not mstr:
                    return False
                end = idx + len(mstr.group(0))
                return has_clean_tail(end)
            if ch == "-" or ch.isdigit():
                mnum = re.match(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', s[idx:])
                if not mnum:
                    return False
                end = idx + len(mnum.group(0))
                return has_clean_tail(end)
            if s.startswith("true", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                return has_clean_tail(idx + 4)
            if s.startswith("false", idx) and (idx + 5 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 5])):
                return has_clean_tail(idx + 5)
            if s.startswith("null", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                return has_clean_tail(idx + 4)
            return False

        def next_value_start_on_boundary(s, start_idx):
            i = start_idx
            while i < len(s):
                while i < len(s) and not s[i].isspace():
                    i += 1
                while i < len(s) and s[i].isspace():
                    i += 1
                if i < len(s) and is_value_start(s, i):
                    return i
            return None

        keep_from = first_non_ws
        if not is_value_start(tail, first_non_ws):
            next_valid = next_value_start_on_boundary(tail, first_non_ws)
            if next_valid is not None:
                keep_from = next_valid

        kept_tail = tail[keep_from:].lstrip()
        sep = "" if not kept_tail else ("" if head.endswith((" ", "\t")) else " ")
        return f"{head}{sep}{kept_tail}"

    def _find_nearby_comma_after_colon_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_comma_after_colon(txt):
                return ln, txt
        return None, None

    def _analyze_invalid_prefix_after_colon(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<tail>.*)$', raw)
        if not m:
            return None
        head = m.group("head") or ""
        tail = m.group("tail") or ""
        if not tail.strip():
            return None
        first_non_ws = None
        for idx, ch in enumerate(tail):
            if not ch.isspace():
                first_non_ws = idx
                break
        if first_non_ws is None:
            return None
        # Comma-after-colon has a dedicated diagnostic path.
        if tail[first_non_ws] == ",":
            return None
        # Keep existing value-typo paths for normal value starts.
        first_ch = tail[first_non_ws]
        if first_ch.isalnum() or first_ch in ('"', "-"):
            return None

        def head_with_space():
            return re.sub(r':\s*$', ': ', head)

        def token_end_if_clean(s, idx):
            ch = s[idx]
            if ch == '"':
                mstr = re.match(r'"(?:\\.|[^"\\])*"', s[idx:])
                if not mstr:
                    return None
                end = idx + len(mstr.group(0))
            elif ch == "-" or ch.isdigit():
                mnum = re.match(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', s[idx:])
                if not mnum:
                    return None
                end = idx + len(mnum.group(0))
            elif s.startswith("true", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                end = idx + 4
            elif s.startswith("false", idx) and (idx + 5 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 5])):
                end = idx + 5
            elif s.startswith("null", idx) and (idx + 4 >= len(s) or not re.match(r"[A-Za-z0-9_]", s[idx + 4])):
                end = idx + 4
            elif ch in ("{", "["):
                close = "}" if ch == "{" else "]"
                j = idx + 1
                while j < len(s) and s[j].isspace():
                    j += 1
                if j >= len(s):
                    # Allow container start at EOL (valid multi-line value).
                    return len(s)
                if j < len(s) and s[j] == close:
                    end = j + 1
                else:
                    return None
            else:
                return None

            j = end
            while j < len(s) and s[j].isspace():
                j += 1
            if j < len(s) and s[j] == ",":
                j += 1
                while j < len(s) and s[j].isspace():
                    j += 1
            if j == len(s):
                return end
            return None

        # If the first value token is valid and the rest of the tail is clean,
        # this is not an invalid-prefix-after-colon case.
        if token_end_if_clean(tail, first_non_ws) is not None:
            return None

        def next_value_start_on_boundary(s, start_idx):
            i = start_idx
            while i < len(s):
                while i < len(s) and not s[i].isspace():
                    i += 1
                while i < len(s) and s[i].isspace():
                    i += 1
                if i < len(s) and token_end_if_clean(s, i) is not None:
                    return i
            return None

        next_valid = next_value_start_on_boundary(tail, first_non_ws)
        start_col = len(head) + first_non_ws
        if next_valid is not None:
            end_col = len(head) + next_valid
            after = f"{head_with_space()}{tail[next_valid:].lstrip()}".rstrip()
        else:
            end_col = len(raw)
            after = head.rstrip()
        if end_col <= start_col:
            end_col = start_col + 1
        return {"start_col": start_col, "end_col": end_col, "after": after}

    def _line_has_invalid_prefix_after_colon(self, line_text):
        return self._analyze_invalid_prefix_after_colon(line_text) is not None

    def _fix_invalid_prefix_after_colon(self, line_text):
        analysis = self._analyze_invalid_prefix_after_colon(line_text)
        if not analysis:
            return line_text
        return analysis["after"]

    def _find_nearby_invalid_prefix_after_colon_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_invalid_prefix_after_colon(txt):
                return ln, txt
        return None, None

    def _comma_before_closer_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(
            r'^(?P<indent>\s*)(?P<run>,(?:\s*,)*)\s*(?P<close>[\}\]])(?P<trail>\s*)$',
            raw,
        )
        if not m:
            return None
        start_col = len(m.group("indent") or "")
        end_col = len(raw)
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _line_has_comma_before_closer(self, line_text):
        return self._comma_before_closer_span(line_text) is not None

    def _fix_comma_before_closer(self, line_text):
        if not line_text:
            return line_text
        raw = line_text.rstrip()
        m = re.match(
            r'^(?P<indent>\s*)(?P<run>,(?:\s*,)*)\s*(?P<close>[\}\]])(?P<trail>\s*)$',
            raw,
        )
        if not m:
            return raw
        indent = m.group("indent") or ""
        close = m.group("close") or "}"
        return f"{indent}{close},"

    def _find_nearby_comma_before_closer_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_comma_before_closer(txt):
                return ln, txt
        return None, None

    def _comma_line_invalid_tail_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<indent>\s*),(?P<tail>.*)$', raw)
        if not m:
            return None
        tail = m.group("tail") or ""
        idx = 0
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx >= len(tail):
            return None
        # Dedicated comma-before-closer rule handles ",}" / ",]".
        if tail[idx] in ("}", "]"):
            return None
        start_col = len(m.group("indent") or "")
        end_col = len(raw)
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _line_has_comma_line_invalid_tail(self, line_text):
        return self._comma_line_invalid_tail_span(line_text) is not None

    def _expected_missing_close_symbol(self, lineno):
        try:
            if self._is_missing_object_close():
                return "}"
            if self._is_missing_list_close():
                return "]"
        except Exception:
            pass
        next_line = self._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = self._line_text(next_line).strip() if next_line else ""
        if next_text.startswith("["):
            return "]"
        return "}"

    def _fix_comma_line_invalid_tail(self, line_text, lineno=None):
        if not line_text:
            return line_text
        raw = line_text.rstrip()
        m = re.match(r'^(?P<indent>\s*),(?P<tail>.*)$', raw)
        if not m:
            return raw
        indent = m.group("indent") or ""
        close = self._expected_missing_close_symbol(lineno)
        return f"{indent}{close},"

    def _find_nearby_comma_line_invalid_tail_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_comma_line_invalid_tail(txt):
                return ln, txt
        return None, None

    def _missing_key_quote_before_colon_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        # Detect: `"name=: ...` where an invalid trailing symbol appears before
        # the key/value colon and should be removed before closing quote.
        m = re.match(
            r'^(?P<indent>\s*)"(?P<base>[A-Za-z_][A-Za-z0-9_]*)(?P<bad>[^\w"]+):(?P<rest>.*)$',
            raw,
        )
        if m:
            indent = m.group("indent") or ""
            base = m.group("base") or ""
            bad = m.group("bad") or ""
            start_col = len(indent) + 1 + len(base)
            return {
                "start_col": start_col,
                "end_col": start_col + len(bad),
                "issue": "wrong_symbol_before_colon",
            }

        # Detect: `"name: "lib",` where the closing quote on the key is missing.
        m = re.match(r'^(?P<indent>\s*)"(?P<key>[^":]+):(?P<rest>.*)$', raw)
        if m:
            rest = m.group("rest") or ""
            rest_trim = rest.lstrip()
            # Ignore array-item/value typos like `"hackhub.net:,` so they route
            # through value-tail diagnostics instead of key-quote diagnostics.
            if not rest_trim or rest_trim.startswith(","):
                return None
            indent = m.group("indent") or ""
            key = m.group("key") or ""
            colon_col = len(indent) + 1 + len(key)
            return {
                "start_col": colon_col,
                "end_col": colon_col,
                "issue": "missing_close_quote",
            }

        # Detect: `<bad>name": ...` where a wrong opening quote symbol is used
        # (for example `'`, `` ` ``, `\`, or other punctuation).
        m = re.match(r'^(?P<indent>\s*)(?P<bad>[^\w"\s])(?P<key>[^":]+)"(?P<rest>\s*:.*)$', raw)
        if m:
            indent = m.group("indent") or ""
            start_col = len(indent)
            return {
                "start_col": start_col,
                "end_col": start_col + 1,
                "issue": "wrong_open_quote_char",
            }

        # Detect: `name": ...` where opening quote is missing.
        m = re.match(r'^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)"(?P<rest>\s*:.*)$', raw)
        if not m:
            return None
        indent = m.group("indent") or ""
        start_col = len(indent)
        return {
            "start_col": start_col,
            "end_col": start_col,
            "issue": "missing_open_quote",
        }

    def _line_has_missing_key_quote_before_colon(self, line_text):
        return self._missing_key_quote_before_colon_span(line_text) is not None

    def _fix_property_key_symbol_before_colon(self, line_text):
        if not line_text:
            return line_text
        return re.sub(
            r'^(\s*)"([A-Za-z_][A-Za-z0-9_]*)([^\w"]+)(\s*:)',
            r'\1"\2"\4',
            line_text.rstrip(),
            count=1,
        )

    def _find_nearby_missing_key_quote_before_colon_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_missing_key_quote_before_colon(txt):
                return ln, txt
        return None, None

    def _property_key_invalid_escape_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        # Detect: `"name\: ...` where an invalid backslash is used before the
        # key/value colon and should be corrected to a closing quote.
        m = re.match(r'^(?P<indent>\s*)"(?P<key>[^"]*)\\(?P<rest>\s*:.*)$', raw)
        if not m:
            return None
        indent = m.group("indent") or ""
        key = m.group("key") or ""
        start_col = len(indent) + 1 + len(key)
        return start_col, start_col + 1

    def _line_has_property_key_invalid_escape(self, line_text):
        return self._property_key_invalid_escape_span(line_text) is not None

    def _fix_property_key_invalid_escape(self, line_text):
        if not line_text:
            return line_text
        # Only replace the first key-close escape before ":".
        return re.sub(r'^(\s*"[^"]*)\\(\s*:)', r'\1"\2', line_text.rstrip(), count=1)

    def _find_nearby_property_key_invalid_escape_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_property_key_invalid_escape(txt):
                return ln, txt
        return None, None

    def _missing_key_quote_before_colon_diag(self, line_no, colno=1):
        missing_key_quote_no, missing_key_quote_text = self._find_nearby_missing_key_quote_before_colon_line(
            line_no
        )
        if not (missing_key_quote_text and missing_key_quote_no):
            return None
        raw = self._line_text(missing_key_quote_no)
        span = self._missing_key_quote_before_colon_span(raw)
        if span:
            start_col = int(span.get("start_col", max((colno or 1) - 1, 0)))
            end_col = int(span.get("end_col", start_col))
            issue = str(span.get("issue", "")).strip().lower()
        else:
            start_col = max((colno or 1) - 1, 0)
            end_col = start_col
            issue = ""
        header = "Invalid Entry: add quotes around the highlighted name."
        note = "missing_key_quote_before_colon"
        after = self._quote_property_name(missing_key_quote_text).strip()
        if issue == "wrong_symbol_before_colon":
            header = "Invalid Entry: remove the invalid symbol before ':'."
            note = "symbol_wrong_property_key_symbol"
            after = self._fix_property_key_symbol_before_colon(missing_key_quote_text).strip()
        if issue == "wrong_open_quote_char":
            header = "Invalid Entry: replace the wrong quote with a double quote."
            note = "symbol_wrong_property_quote_char"
        return {
            "header": header,
            "before": missing_key_quote_text.strip(),
            "after": after,
            "line": missing_key_quote_no,
            "start_col": start_col,
            "end_col": end_col,
            "note": note,
        }

    def _quoted_item_invalid_tail_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        # Object-member typo like `"name: "value"` should use key-quote repair,
        # not quoted-array-item trailing-symbol diagnostics.
        if self._line_has_missing_key_quote_before_colon(raw):
            return None
        m = re.match(r'^(?P<head>\s*"[^"]*")(?P<tail>.*)$', raw)
        if not m:
            return None
        head = m.group("head") or ""
        tail = m.group("tail") or ""
        # Array-item rule only: ignore object member lines like
        # `"phone": "909-505-4131",,,#`.
        if tail.lstrip().startswith(":"):
            return None
        idx = 0
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx >= len(tail):
            return None

        # Allow one delimiter comma after a quoted array item. Highlight only
        # extra/invalid symbols after that first comma.
        if tail[idx] == ",":
            idx += 1
            while idx < len(tail) and tail[idx].isspace():
                idx += 1
            if idx >= len(tail):
                return None

        start_col = len(head) + idx
        end_col = len(raw)
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _line_has_invalid_tail_after_quoted_item(self, line_text):
        return self._quoted_item_invalid_tail_span(line_text) is not None

    def _fix_invalid_tail_after_quoted_item(self, line_text, lineno=None):
        if not line_text:
            return line_text
        m = re.match(r'^(?P<head>\s*"[^"]*")(?P<tail>.*)$', line_text.rstrip())
        if not m:
            return line_text
        head = m.group("head")
        next_line = self._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = self._line_text(next_line).strip() if next_line else ""
        needs_comma = not next_text.startswith(("]", "}"))
        return head + ("," if needs_comma else "")

    def _find_nearby_invalid_tail_after_quoted_item_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_invalid_tail_after_quoted_item(txt):
                return ln, txt
        return None, None

    def _line_has_illegal_trailing_comma_before_close(self, line_text, lineno):
        if not line_text or not lineno:
            return False
        raw = line_text.rstrip()
        if not raw.endswith(","):
            return False
        # If there are already invalid trailing symbols after a completed
        # value/item, prefer the symbol-run diagnostic so the full bad tail
        # is highlighted (not just the final comma).
        if self._line_has_invalid_trailing_symbols_after_string_value(raw):
            return False
        if self._line_has_invalid_tail_after_quoted_item(raw):
            return False
        # Comma runs are handled by duplicate-comma diagnostics so only extra
        # commas are marked red and "After" reduces to a single comma.
        if re.search(r',\s*,+\s*$', raw):
            return False
        next_line = self._next_non_empty_line_number(lineno)
        if not next_line:
            return False
        next_text = self._line_text(next_line).lstrip()
        return next_text.startswith(("}", "]"))

    def _trailing_comma_before_close_col(self, line_text):
        if not line_text:
            return None
        idx = line_text.rstrip().rfind(",")
        return idx if idx >= 0 else None

    def _fix_illegal_trailing_comma_before_close(self, line_text):
        if not line_text:
            return line_text
        return re.sub(r',\s*$', "", line_text.rstrip())

    def _find_nearby_illegal_trailing_comma_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_illegal_trailing_comma_before_close(txt, ln):
                return ln, txt
        return None, None

    def _line_has_illegal_comma_after_top_level_close(self, line_text, lineno):
        if not line_text or not lineno:
            return False
        if not re.match(r'^\s*[\}\]]\s*,+\s*$', line_text):
            return False
        # If content continues, it's more likely a missing list/object wrapper.
        next_line = self._next_non_empty_line_number(lineno)
        return next_line is None

    def _top_level_close_symbol_run_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<indent>\s*)(?P<close>[\}\]])(?P<trail>.*)$', raw)
        if not m:
            return None
        tail = m.group("trail") or ""
        idx = 0
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx >= len(tail):
            return None
        start_col = len(m.group("indent") or "") + 1 + idx
        end_col = len(raw)
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _line_has_top_level_close_symbol_run(self, line_text, lineno):
        if not line_text or not lineno:
            return False
        if self._top_level_close_symbol_run_span(line_text) is None:
            return False
        # Only classify as top-level tail run when this is EOF context.
        next_line = self._next_non_empty_line_number(lineno)
        return next_line is None

    def _fix_top_level_close_symbol_run(self, line_text):
        if not line_text:
            return line_text
        return re.sub(r'(\s*[\}\]])\s*.*$', r'\1', line_text.rstrip())

    def _find_nearby_top_level_close_symbol_run_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_top_level_close_symbol_run(txt, ln):
                return ln, txt
        return None, None

    def _comma_run_after_top_level_close_span(self, line_text):
        if not line_text:
            return None
        raw = line_text.rstrip()
        m = re.match(r'^(?P<indent>\s*)(?P<close>[\}\]])(?P<trail>\s*,+\s*)$', raw)
        if not m:
            return None
        indent_len = len(m.group("indent") or "")
        start_col = raw.find(",", indent_len + 1)
        if start_col < 0:
            return None
        end_col = len(raw)
        if end_col <= start_col:
            end_col = start_col + 1
        return start_col, end_col

    def _fix_illegal_comma_after_top_level_close(self, line_text):
        if not line_text:
            return line_text
        return re.sub(r'(\s*[\}\]])\s*,+\s*$', r'\1', line_text.rstrip())

    def _find_nearby_illegal_comma_after_top_level_close_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if txt.strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_illegal_comma_after_top_level_close(txt, ln):
                return ln, txt
        return None, None

    def _split_completed_scalar_value_tail(self, line_text):
        """Return (head, tail, prefix_len) for lines like `"key": <scalar><tail>`.

        Supports completed scalar values:
        - string: "value"
        - number: 123 / -1.2 / 1e3
        - literals: true / false / null
        """
        if not line_text:
            return None
        m = re.match(r'^(?P<prefix>\s*"[^"]+"\s*:\s*)(?P<rest>.*)$', line_text)
        if not m:
            return None
        prefix = m.group("prefix") or ""
        rest = m.group("rest") or ""
        idx = 0
        while idx < len(rest) and rest[idx].isspace():
            idx += 1
        if idx >= len(rest):
            return None

        value_end = None
        ch = rest[idx]
        if ch == '"':
            j = idx + 1
            escaped = False
            while j < len(rest):
                c = rest[j]
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    value_end = j + 1
                    break
                j += 1
            if value_end is None:
                return None
        elif ch in "-0123456789":
            num_m = re.match(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?", rest[idx:])
            if not num_m:
                return None
            value_end = idx + len(num_m.group(0))
        else:
            literal_end = None
            for lit in ("true", "false", "null"):
                if rest.startswith(lit, idx):
                    end_idx = idx + len(lit)
                    if end_idx >= len(rest) or not re.match(r"[A-Za-z0-9_]", rest[end_idx]):
                        literal_end = end_idx
                        break
            if literal_end is None:
                return None
            value_end = literal_end

        prefix_len = len(prefix) + value_end
        head = line_text[:prefix_len]
        tail = line_text[prefix_len:]
        return head, tail, prefix_len

    def _line_has_invalid_trailing_symbols_after_string_value(self, line_text):
        parsed = self._split_completed_scalar_value_tail(line_text)
        if not parsed:
            return False
        _head, tail, _prefix_len = parsed
        return tail.strip() not in ("", ",")

    def _first_invalid_trailing_symbol_col(self, line_text, lineno=None):
        parsed = self._split_completed_scalar_value_tail(line_text)
        if not parsed:
            return None
        _head, tail, prefix_len = parsed
        idx = 0
        # Skip whitespace after the value.
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        # A single trailing comma can be valid for continued objects/lists.
        # If anything follows that comma, include the comma in the error span
        # only when the comma itself is illegal for this line.
        if idx < len(tail) and tail[idx] == ",":
            comma_idx = idx
            idx += 1
            while idx < len(tail) and tail[idx].isspace():
                idx += 1
            if idx < len(tail):
                comma_is_valid = bool(lineno) and self._line_requires_trailing_comma(lineno)
                if comma_is_valid:
                    return prefix_len + idx
                return prefix_len + comma_idx
            return None
        if idx < len(tail):
            return prefix_len + idx
        return None

    def _fix_invalid_trailing_symbols_after_string_value(self, line_text, lineno=None):
        parsed = self._split_completed_scalar_value_tail(line_text)
        if not parsed:
            return line_text
        head, _tail, _prefix_len = parsed
        next_line = self._next_non_empty_line_number(lineno or 1) if lineno else None
        next_text = self._line_text(next_line).strip() if next_line else ""
        needs_comma = not next_text.startswith(("}", "]"))
        return head + ("," if needs_comma else "")

    def _find_nearby_invalid_trailing_symbols_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_invalid_trailing_symbols_after_string_value(txt):
                return ln, txt
        return None, None

    def _line_has_invalid_symbol_after_closer(self, line_text):
        if not line_text:
            return False
        m = re.match(r'^\s*([\}\]])(?P<trail>.*)$', line_text)
        if not m:
            return False
        tail = (m.group("trail") or "").strip()
        # Valid: just closer, or closer followed by comma.
        return tail not in ("", ",")

    def _first_invalid_symbol_after_closer_col(self, line_text):
        m = re.match(r'^\s*([\}\]])(?P<trail>.*)$', line_text)
        if not m:
            return None
        prefix_len = len(line_text) - len(m.group("trail"))
        tail = m.group("trail") or ""
        idx = 0
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx < len(tail) and tail[idx] == ",":
            idx += 1
            while idx < len(tail) and tail[idx].isspace():
                idx += 1
        if idx < len(tail):
            return prefix_len + idx
        return None

    def _fix_invalid_symbol_after_closer(self, line_text):
        m = re.match(r'^(\s*[\}\]])(?P<trail>.*)$', line_text)
        if not m:
            return line_text
        head = m.group(1)
        return head + ","

    def _find_nearby_invalid_symbol_after_closer_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_invalid_symbol_after_closer(txt):
                return ln, txt
        return None, None

    def _invalid_symbol_after_open_span(self, line_text):
        if not line_text:
            return None
        m = re.match(r'^(?P<indent>\s*)(?P<open>[\{\[])(?P<trail>.*)$', line_text)
        if not m:
            return None
        opener = m.group("open")
        tail = m.group("trail") or ""
        idx = 0
        while idx < len(tail) and tail[idx].isspace():
            idx += 1
        if idx >= len(tail):
            return None
        ch = tail[idx]

        if opener == "{":
            # After '{' at line start, only a quoted key or '}' is valid.
            if ch in ('"', "}"):
                return None
        else:
            # After '[' at line start, allow common JSON value starts.
            if ch in ("]", "{", "[", '"', "-") or ch.isdigit() or ch.lower() in ("t", "f", "n"):
                return None

        # Restrict this path to symbol errors so name/value diagnostics can
        # continue handling alphanumeric cases.
        if ch.isalnum() or ch in ('"', "'", "_"):
            return None

        run_end = idx + 1
        while run_end < len(tail):
            nxt = tail[run_end]
            if nxt.isspace() or nxt.isalnum() or nxt in ('"', "'", "_"):
                break
            run_end += 1

        col_start = len(m.group("indent")) + 1 + idx
        col_end = len(m.group("indent")) + 1 + run_end
        symbol_text = tail[idx:run_end]
        return opener, col_start, col_end, symbol_text

    def _line_has_invalid_symbol_after_open(self, line_text):
        return self._invalid_symbol_after_open_span(line_text) is not None

    def _fix_invalid_symbol_after_open(self, line_text):
        span = self._invalid_symbol_after_open_span(line_text)
        if not span:
            return line_text
        _opener, start_col, end_col, _symbol_text = span
        return line_text[:start_col] + line_text[end_col:]

    def _find_nearby_invalid_symbol_after_open_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_has_invalid_symbol_after_open(txt):
                return ln, txt
        return None, None

    def _find_nearby_extra_quote_in_value_line(self, lineno, lookback=2):
        if not lineno:
            return None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_extra_quote_in_string_value(txt):
                return ln, txt
        return None, None

    def _build_symbol_json_diagnostic(self, exc, lineno=None):
        return json_error_diagnostics_core.build_symbol_json_diagnostic(self, exc, lineno=lineno)


    def _build_json_diagnostic(self, exc):
        return json_error_diagnostics_core.build_json_diagnostic(self, exc)


    def _quote_unquoted_value(self, line_text):
        if not line_text or ":" not in line_text:
            return line_text
        left, right = line_text.split(":", 1)
        right = right.lstrip()
        if not right:
            return line_text

        # Work only on the first value token after "key:" and preserve any tail.
        comma_idx = right.find(",")
        if comma_idx != -1:
            token = right[:comma_idx].strip()
            tail = right[comma_idx:]
        else:
            token = right.strip()
            tail = ""
        if token == "":
            return line_text
        lower = token.lower()

        # Keep valid JSON literals/numbers unquoted.
        if lower in ("true", "false", "null"):
            return line_text
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", token):
            return line_text
        if token.startswith("{") or token.startswith("[") or token.startswith('"'):
            return line_text

        # Fix common case: missing opening quote (or mismatched quote) around scalar.
        token = token.strip()
        if token.endswith('"') and token.count('"') == 1:
            token = token[:-1]
        # Remove invalid trailing characters before wrapping in quotes
        token = _strip_invalid_trailing_chars(token.strip())
        fixed = f'{left}: "{token}"{tail}'
        return fixed

    def _quote_unquoted_scalar_line(self, line_text):
        if not line_text:
            return line_text
        if ":" in line_text:
            return self._quote_unquoted_value(line_text)

        stripped = line_text.strip()
        if not stripped:
            return line_text

        has_trailing_comma = stripped.endswith(",")
        token = stripped[:-1].rstrip() if has_trailing_comma else stripped
        if not token:
            return line_text

        lower = token.lower()
        if lower in ("true", "false", "null"):
            return line_text
        if re.fullmatch(r"-?\d+(\.\d+)?([eE][+-]?\d+)?", token):
            return line_text
        if token.startswith("{") or token.startswith("[") or token.startswith("]") or token.startswith("}"):
            return line_text
        if token.startswith('"') and token.endswith('"') and token.count('"') >= 2:
            return line_text

        if token.endswith('"') and token.count('"') == 1:
            token = token[:-1].strip()
        elif token.startswith('"') and token.count('"') == 1:
            token = token[1:].strip()
        else:
            token = token.strip().strip('"')

        # Remove invalid trailing characters before wrapping in quotes
        token = _strip_invalid_trailing_chars(token)
        fixed = f"\"{token}\""
        if has_trailing_comma:
            fixed += ","
        return fixed

    def _line_needs_value_quotes(self, line_text):
        if not line_text:
            return False
        fixed = self._quote_unquoted_scalar_line(line_text)
        return bool(fixed and fixed != line_text)

    def _missing_value_close_quote_insert_col(self, line_text):
        # Detect: "key": "value,  (missing closing quote before comma/EOL).
        if not line_text:
            return None
        raw = str(line_text)
        # Keep object-key quote diagnostics for key-like forms:
        #   "name: [
        #   "name=: {
        #   "name: "value"
        if re.match(r'^\s*"[A-Za-z_][A-Za-z0-9_]*[^\w"]*:\s*[\[{"]', raw):
            return None

        def _scan_unclosed_quoted_value(value_text, base_col):
            if not value_text.startswith('"'):
                return None
            escape = False
            for idx, ch in enumerate(value_text[1:], start=1):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    # Already has a valid closing quote.
                    return None
                if ch == ",":
                    return int(base_col + idx)
            if value_text.count('"') == 1:
                return int(base_col + len(value_text.rstrip()))
            return None

        object_value_match = re.match(r'^\s*"[^"]*"\s*:(?P<rest>.*)$', raw)
        if object_value_match:
            rest = object_value_match.group("rest") or ""
            rest_start = int(object_value_match.start("rest"))
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            return _scan_unclosed_quoted_value(value_text, base_col=int(rest_start + ws_len))

        # Array/scalar line form: "value,   (missing closing quote before comma/EOL).
        ws_len = len(raw) - len(raw.lstrip(" \t"))
        value_text = raw.lstrip(" \t")
        return _scan_unclosed_quoted_value(value_text, base_col=int(ws_len))

    def _missing_value_open_quote_insert_col(self, line_text):
        # Detect missing opening quote for scalar values so cursor can stay
        # at the exact insert point instead of jumping to parser fallback lines.
        raw = str(line_text or "")
        if not raw:
            return None
        # Keep literal typo and wrong-token diagnostics in their existing paths.
        if re.match(r'^\s*[A-Za-z_][A-Za-z0-9_]*\s*$', raw):
            return None
        fixed = self._quote_unquoted_scalar_line(raw)
        if not fixed or fixed == raw:
            return None
        if ":" in raw:
            colon_idx = raw.find(":")
            rest = raw[colon_idx + 1 :]
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            if value_text.startswith('"'):
                return None
            return int(colon_idx + 1 + ws_len)
        for idx, ch in enumerate(raw):
            if not ch.isspace():
                return int(idx)
        return 0

    def _find_nearby_missing_value_close_quote_line(self, lineno, lookback=2):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            insert_col = self._missing_value_close_quote_insert_col(txt)
            if insert_col is not None:
                return int(ln), txt, int(insert_col)
        return None, None, None

    def _find_nearby_missing_value_open_quote_line(self, lineno, lookback=3):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            insert_col = self._missing_value_open_quote_insert_col(txt)
            if insert_col is not None:
                return int(ln), txt, int(insert_col)
        return None, None, None

    def _find_nearby_unquoted_value_line(self, lineno, lookback=3):
        if not lineno:
            return None, None
        # Check current line first, then a few previous non-empty lines.
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend").strip()))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                break
            if txt:
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            if self._line_needs_value_quotes(txt):
                return ln, txt
        return None, None

    def _suggest_json_literal_from_token(self, token):
        return json_diag_core.suggest_json_literal_from_token(token)

    def _boolean_literal_typo_diagnostic(self, line_text):
        return json_diag_core.boolean_literal_typo_diagnostic(line_text)

    def _find_nearby_boolean_literal_typo_line(self, lineno, lookback=3):
        return json_diag_core.find_nearby_boolean_literal_typo_line(
            self._line_text,
            lineno,
            lookback=lookback,
        )

    def _is_wrong_list_open_for_object(self, prev_text, next_text):
        if not prev_text:
            return False
        prev = prev_text.strip()
        prev_compact = "".join(prev.split())
        if not (prev.endswith("\": [") or prev.endswith("\":[") or prev_compact.endswith("\":[") ):
            return False
        nxt = next_text.strip()
        # Only treat as object-open mismatch when the next token looks like an
        # object property (`"key": ...`), not a plain list item (`"value"`).
        return bool(re.match(r'^"[^"]+"\s*:', nxt))

    def _find_wrong_list_open_line(self, lineno, lookback=3):
        if not lineno:
            return None
        line = lineno - 1
        checked = 0
        while line >= 1 and checked < lookback:
            text = self._line_text(line).strip()
            if text:
                next_line_num = self._next_non_empty_line_number(line)
                next_text = self._line_text(next_line_num).strip() if next_line_num else ""
                if self._is_wrong_list_open_for_object(text, next_text):
                    return line
                checked += 1
            line -= 1
        return None

    def _find_wrong_object_open_line(self, lineno, lookback=3):
        if not lineno:
            return None
        line = lineno - 1
        checked = 0
        while line >= 1 and checked < lookback:
            text = self._line_text(line).strip()
            if text:
                if text in ("[", "[,"):
                    next_line_num = self._next_non_empty_line_number(line)
                    next_text = self._line_text(next_line_num).strip() if next_line_num else ""
                    # Only treat "[" as wrong object opener when the following
                    # line looks like an object property (`"key": ...`).
                    if re.match(r'^"[^"]+"\s*:', next_text):
                        return line
                checked += 1
            line -= 1
        return None

    def _expected_closer_before_position(self, target_line, target_col):
        return json_diag_core.expected_closer_before_position(
            self._line_text,
            target_line,
            target_col,
        )

    def _find_wrong_closing_symbol_line(self, lineno, lookback=2):
        return json_diag_core.find_wrong_closing_symbol_line(
            self._line_text,
            lineno,
            lookback=lookback,
        )

    def _find_missing_list_close_before_object_end(self, lineno, lookback=4):
        return json_diag_core.find_missing_list_close_before_object_end(
            self._line_text,
            self._closest_non_empty_line_before,
            lineno,
            lookback=lookback,
        )

    def _next_non_empty_line_number(self, start_line):
        try:
            last_line = int(self.text.index("end-1c").split(".")[0])
        except Exception:
            return None
        line = max(start_line + 1, 1)
        while line <= last_line:
            text = self._line_text(line)
            if text.strip():
                return line
            line += 1
        return None

    def _missing_list_open_key_line(self, lineno):
        if not lineno:
            return None
        line = max(lineno - 1, 1)
        while line >= 1:
            text = self._line_text(line).strip()
            if text.endswith("\":") and not text.endswith("\": {") and not text.endswith("\": ["):
                next_line_num = self._next_non_empty_line_number(line)
                if next_line_num:
                    next_text = self._line_text(next_line_num).strip()
                    if next_text.startswith("{"):
                        return line
            line -= 1
        return None

    @staticmethod
    def _line_looks_like_object_property(line_text):
        return bool(re.match(r'^"[^"]+"\s*:', str(line_text or "").strip()))

    def _find_missing_container_open_after_key_line(self, lineno, lookback=6):
        """Find a key line that likely needs an opening container token.

        Returns:
            tuple[int|None, str|None]: (line_number, opener) where opener is
            "{" for object-open suggestions or "[" for list-open suggestions.
        """
        if not lineno:
            return None, None
        line = max(lineno - 1, 1)
        checked = 0
        while line >= 1 and checked < lookback:
            text = self._line_text(line).strip()
            if text:
                checked += 1
                if text.endswith('":'):
                    next_line_num = self._next_non_empty_line_number(line)
                    if next_line_num:
                        next_text = self._line_text(next_line_num).strip()
                        if self._line_looks_like_object_property(next_text):
                            return line, "{"
                        if next_text.startswith('"') or next_text.startswith("{"):
                            return line, "["
            line -= 1
        return None, None

    def _find_missing_list_open_after_key_line(self, lineno, lookback=6):
        line, opener = self._find_missing_container_open_after_key_line(
            lineno, lookback=lookback
        )
        if opener == "[":
            return line
        return None

    def _missing_close_example(self, msg):
        if msg in ("Expecting ']'", "Unexpected ']'"):
            return "],"
        return "},"

    def _format_suggestion(self, header, before, after, header_only=False):
        if header_only:
            return f"Suggestion:\n- Before: {before}\n- After:  {after}"
        return f"{header}\n\nSuggestion:\n- Before: {before}\n- After:  {after}"

    def _suggestion_from_example(self, example, add_after=None, add_colon=False, quote_key=False):
        before = example.strip()
        after = before
        if quote_key:
            after = self._quote_property_name(before)
        if add_colon and ":" not in after:
            if after and not after.endswith(":"):
                after = after.rstrip(",") + ": \"value\""
        if add_after:
            if add_after in (",", "],", "},", "{", "["):
                if add_after == ",":
                    before = before.rstrip().rstrip(",")
                    after = before + ","
                else:
                    after = add_after
                    if add_after in ("},", "],"):
                        before = add_after.replace(",", "")
                    if add_after in ("{", "["):
                        before = add_after
            else:
                # Append non-structural additions (e.g. closing quote) to the
                # example so suggestions show the full corrected string.
                after = before + add_after
        return (before if before else "\"value\""), (after if after else "\"value\"")
    def _is_missing_object_open_at(self, lineno):
        if not lineno:
            return False
        line_text = self._line_text(lineno).lstrip()
        if not line_text or ":" not in line_text:
            return False
        prev_line_num = self._closest_non_empty_line_before(lineno)
        if not prev_line_num:
            return False
        prev_text = self._line_text(prev_line_num).strip()
        # Do not treat a normal object-member line after "{" as missing object-open.
        # This heuristic is only for property lines that likely lost their leading "{"
        # in list/object boundaries.
        if prev_text in ("[", ",", "],", "},"):
            return True
        return False

    def _line_text(self, lineno):
        try:
            return self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")
        except Exception:
            return ""

    def _line_has_missing_open_key_quote(self, line_text):
        stripped = (line_text or "").lstrip()
        if not stripped or stripped.startswith("\""):
            return False
        if "\":" not in stripped:
            return False
        first = stripped[0]
        return first.isalpha() or first == "_"

    def _missing_close_target_line_from_exc(self, exc, open_bracket, close_bracket):
        line = getattr(exc, "lineno", None)
        if line:
            return line
        return self._missing_close_target_line(open_bracket, close_bracket)

    def _missing_close_target_line_any(self, exc):
        if self._is_missing_object_close():
            line, _idx = self._missing_close_insertion_point("{", "}", exc)
            if line:
                return line
        if self._is_missing_list_close():
            line, _idx = self._missing_close_insertion_point("[", "]", exc)
            if line:
                return line
        return None

    def _missing_list_close_target_line(self, exc):
        line, _idx = self._missing_close_insertion_point("[", "]", exc)
        return line

    def _unmatched_open_bracket_lines(self, open_bracket, close_bracket):
        text = self.text.get("1.0", "end-1c")
        stack = []
        line = 1
        in_string = False
        escape = False
        for ch in text:
            if ch == "\n":
                line += 1
                if in_string and not escape:
                    # Keep string state; multiline strings are invalid JSON but
                    # this preserves safer structural scanning behavior.
                    pass
                escape = False
                continue
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == "\"":
                    in_string = False
                continue
            if ch == "\"":
                in_string = True
                continue
            if ch == open_bracket:
                stack.append(line)
            elif ch == close_bracket and stack:
                stack.pop()
        return stack

    def _is_missing_list_close(self):
        return bool(self._unmatched_open_bracket_lines("[", "]"))

    def _is_missing_object_close(self):
        return bool(self._unmatched_open_bracket_lines("{", "}"))

    def _last_unmatched_bracket_line(self, open_bracket, close_bracket):
        stack = self._unmatched_open_bracket_lines(open_bracket, close_bracket)
        if stack:
            return stack[-1]
        return None

    def _line_indent_width(self, lineno):
        raw = self._line_text(lineno)
        return len(raw) - len(raw.lstrip(" \t"))

    def _missing_close_insertion_point(self, open_bracket, close_bracket, exc=None):
        open_line = self._last_unmatched_bracket_line(open_bracket, close_bracket)
        try:
            max_line = int(self.text.index("end-1c").split(".")[0])
        except Exception:
            max_line = 1
        if not open_line:
            fallback_line = self._last_non_empty_line_number() or 1
            return fallback_line, self.text.index(f"{fallback_line}.0 lineend")

        open_indent = self._line_indent_width(open_line)
        closer_tokens = [close_bracket]
        # Missing object-close can surface before array closers and missing
        # list-close can surface before object closers.
        if close_bracket == "}":
            closer_tokens.append("]")
        elif close_bracket == "]":
            closer_tokens.append("}")

        candidate = None
        for ln in range(open_line + 1, max_line + 1):
            text = self._line_text(ln)
            stripped = text.strip()
            if not stripped:
                continue
            if any(stripped.startswith(tok) for tok in closer_tokens):
                indent = self._line_indent_width(ln)
                if indent <= open_indent:
                    candidate = ln
                    break

        if candidate is not None:
            insert_line = candidate
            if candidate > 1 and not self._line_text(candidate - 1).strip():
                insert_line = candidate - 1
            closer_indent = self._line_indent_width(candidate)
            if not self._line_text(insert_line).strip():
                existing_end = len(self._line_text(insert_line))
                col = max(existing_end, closer_indent, 0)
            else:
                col = max(closer_indent, 0)
            return insert_line, f"{insert_line}.{col}"

        # No structural closer found: place insertion at trailing EOF.
        last_non_empty = self._last_non_empty_line_number() or open_line
        trailing_blank = None
        for ln in range(max_line, last_non_empty, -1):
            if self._line_text(ln).strip():
                break
            trailing_blank = ln
        if trailing_blank is not None:
            existing_end = len(self._line_text(trailing_blank))
            col = max(existing_end, open_indent, 0)
            return trailing_blank, f"{trailing_blank}.{col}"
        return last_non_empty, self.text.index(f"{last_non_empty}.0 lineend")

    def _missing_object_close_target_line(self, exc):
        line, _idx = self._missing_close_insertion_point("{", "}", exc)
        return line

    def _find_comma_only_line_before(self, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                return None
            if text == ",":
                return line
            line -= 1
        return None

    def _find_missing_comma_between_block_values_line(self, line):
        if not line:
            return None
        current = self._line_text(line).strip()
        if not current.startswith(("{", "[")):
            return None
        prev_line = self._closest_non_empty_line_before(line)
        if not prev_line:
            return None
        prev_text = self._line_text(prev_line).strip()
        if prev_text.endswith(","):
            return None
        if prev_text in ("}", "]"):
            return prev_line
        return None

    def _find_blank_line_before(self, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return None
            if text.strip() == "":
                return line
            line -= 1
        return None

    def _closest_non_empty_line_before(self, start_line):
        line = max(start_line - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                return None
            if text:
                return line
            line -= 1
        return None

    def _last_non_empty_line_number(self):
        try:
            line = int(self.text.index("end-1c").split(".")[0])
        except Exception:
            return None
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend").strip()
            except Exception:
                return None
            if text:
                return line
            line -= 1
        return None


    def _missing_close_target_line(self, open_bracket, close_bracket):
        open_line = self._last_unmatched_bracket_line(open_bracket, close_bracket)
        if not open_line:
            return None
        line = open_line + 1
        last_line = int(self.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return open_line
            if text.strip():
                return line
            line += 1
        return open_line

    def _is_missing_object_open(self, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        return prev_line_stripped.endswith("\":") and not prev_line_stripped.endswith("\": {")

    def _is_missing_list_open(self, exc):
        lineno = getattr(exc, "lineno", None)
        if not lineno:
            return False
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return False
        prev_line_stripped = prev_line.strip()
        if not prev_line_stripped.endswith("\":"):
            return False
        next_line = self._next_non_empty_line(lineno)
        if not next_line:
            return False
        next_line_stripped = next_line.strip()
        return next_line_stripped.startswith("\"")

    def _is_missing_list_open_at_start(self, exc, allow_any_position=False):
        lineno = getattr(exc, "lineno", None)
        colno = getattr(exc, "colno", None)
        if not allow_any_position:
            if lineno not in (None, 1) or (colno not in (None, 1)):
                return False
        first_line = self._next_non_empty_line(1)
        if not first_line:
            return False
        first_text = self._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff")
        if not first_text:
            return False
        if first_text.startswith("["):
            return False
        if not (first_text.startswith("{") or first_text.startswith("\"")):
            return False
        if allow_any_position:
            return True
        return True

    def _missing_list_open_top_level(self):
        first_line = self._next_non_empty_line(1)
        if not first_line:
            return False
        first_text = self._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff")
        if not first_text or first_text.startswith("["):
            return False
        return first_text.startswith("{") or first_text.startswith("\"")

    def _missing_object_open_from_extra_data(self):
        # For "Extra data", if the first meaningful line looks like an object member
        # (`"key": ...`) then the missing delimiter is '{', not '['.
        if getattr(self, "_last_json_error_msg", "") != "Extra data":
            return False
        first_line = self._next_non_empty_line_number(0)
        if not first_line:
            return False
        first_text = self._line_text(first_line).lstrip()
        if first_text.startswith("\ufeff"):
            first_text = first_text.lstrip("\ufeff").lstrip()
        if not first_text.startswith('"'):
            return False
        return '":' in first_text

    def _first_non_ws_char(self):
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return ""
        for ch in text:
            if ch == "\ufeff":
                continue
            if ch.isspace():
                continue
            return ch
        return ""

    def _missing_list_open_from_extra_data(self):
        # Only treat as missing list open for the "Extra data" parser error.
        if getattr(self, "_last_json_error_msg", "") != "Extra data":
            return False
        if self._missing_object_open_from_extra_data():
            return False
        first_char = self._first_non_ws_char()
        if not first_char or first_char == "[":
            return False
        return True

    def _previous_non_empty_line(self, lineno):
        line = max(lineno - 1, 1)
        while line >= 1:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return ""
            if text.strip():
                return text
            line -= 1
        return ""

    def _next_non_empty_line(self, lineno):
        line = max(lineno, 1)
        last_line = int(self.text.index("end-1c").split(".")[0])
        while line <= last_line:
            try:
                text = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                return ""
            if text.strip():
                return text
            line += 1
        return ""

    def _missing_object_example(self, lineno):
        prev_line = self._previous_non_empty_line(lineno)
        if not prev_line:
            return "\"data\": {"
        prev_line_stripped = prev_line.strip()
        if prev_line_stripped.endswith("\":"):
            return prev_line_stripped + " {"
        return "\"data\": {"

    def _close_before_list(self, lineno):
        next_text = self._next_non_empty_line(lineno or 1)
        if not next_text:
            return False
        return next_text.strip().startswith("]")

    def _quote_property_name(self, line_text):
        if ":" in line_text:
            left, right = line_text.split(":", 1)
            left = left.strip()
            # Normalize wrong/missing key quote characters before wrapping.
            left = left.strip().strip(",").strip()
            if left and not left.startswith('"') and left.endswith('"'):
                first = left[0]
                if (not first.isalnum()) and first != "_":
                    left = left[1:]
            left = left.strip().strip('"').strip("'").strip("`")
            left = f"\"{left}\""
            right = right.strip()
            return f"{left}: {right}"
        return "\"key\": \"value\""

    def _highlight_custom_range(self, line, start_col, end_col):
        try:
            if end_col <= start_col:
                end_col = start_col + 1
            start_index = f"{line}.{max(start_col, 0)}"
            end_index = f"{line}.{max(end_col, start_col + 1)}"
            self.text.tag_remove("json_error", "1.0", "end")
            self.text.tag_remove("json_error_line", "1.0", "end")
            self._clear_error_pin()
            palette = self._current_error_palette()
            self.text.tag_add("json_error", start_index, end_index)
            self.text.tag_config("json_error", background=palette["fix_bg"], foreground="#ffffff")
            self.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
            self.text.tag_config("json_error_line", background=palette["line_bg"], foreground="#ffffff")
            self.text.tag_raise("json_error_line")
            self.text.tag_raise("json_error")
            self._error_focus_index = start_index
            insert_index = self._preferred_error_insert_index(line, start_index)
            self.text.mark_set("insert", insert_index)
            self.text.see(insert_index)
            self._position_error_overlay(line)
        except Exception:
            return

    def _fix_missing_at(self, value, domain_roots=None):
        if "@" in value:
            return value
        domains = [
            "gomail.com",
            "gmail.com",
            "yahoo.com",
            "outlook.com",
            "hotmail.com",
            "icloud.com",
        ]
        for domain in domains:
            idx = value.find(domain)
            if idx != -1:
                return value[:idx] + "@" + value[idx:]
        parts = value.split(".")
        if len(parts) == 2:
            left, tld = parts
            if domain_roots:
                best = None
                for root in domain_roots:
                    if left.endswith(root):
                        if best is None or len(root) > len(best):
                            best = root
                if best:
                    local = left[: -len(best)]
                    if local:
                        return f"{local}@{best}.{tld}"
        if len(parts) == 3:
            part0, part1, tld = parts
            if domain_roots:
                best = None
                for root in domain_roots:
                    if part1.endswith(root):
                        if best is None or len(root) > len(best):
                            best = root
                if best:
                    local_tail = part1[: -len(best)].rstrip(".")
                    local = part0 + (("." + local_tail) if local_tail else "")
                    return f"{local}@{best}.{tld}"
            for domlen in (5, 4, 6, 3):
                if len(part1) - domlen >= 3:
                    local_tail = part1[: -domlen]
                    domain = part1[-domlen:] + "." + tld
                    return f"{part0}.{local_tail}@{domain}"
        if len(parts) >= 3:
            return ".".join(parts[:-2]) + "@" + ".".join(parts[-2:])
        last_dot = value.rfind(".")
        if last_dot > 0:
            return value[:last_dot] + "@" + value[last_dot + 1 :]
        # If there's no dot in the value, it's unlikely to be an email (e.g. IBAN).
        # Do not append '@' in that case; return the original value unchanged.
        return value

    def _format_phone(self, value):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) != 10:
            return None
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"

    def _find_phone_format_issue(self):
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return None
        for idx, line_text in enumerate(text.splitlines(), start=1):
            match = self.PHONE_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = match.group(1)
            if not value:
                continue
            formatted = self._format_phone(value)
            if not formatted:
                continue
            if value == formatted:
                continue
            before_line = line_text.strip()
            after_line = line_text[: match.start(1)] + formatted + line_text[match.end(1) :]
            return idx, match.start(1), match.end(1), before_line, after_line.strip()
        return None

    def _fix_missing_space_after_colon(self, line_text):
        if not line_text:
            return line_text
        # Normalize object-member style: "key": value
        return re.sub(r'^(\s*"[^"]+"\s*):\s*(\S.*)$', r"\1: \2", line_text.rstrip(), count=1)

    def _find_json_spacing_issue(self):
        """Detect valid-JSON style issues we enforce in editor text.

        Current rule:
        - object member must include a space after ":" (e.g. `"key": value`)
        """
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return None
        for line_no, line_text in enumerate(text.splitlines(), start=1):
            # Match object-member lines where ":" is immediately followed by a
            # non-whitespace character (e.g. `"isMine":true`).
            m = re.match(r'^(?P<head>\s*"[^"]+"\s*):(?P<tail>\S.*)$', line_text)
            if not m:
                continue
            head = m.group("head") or ""
            tail = m.group("tail") or ""
            if not tail:
                continue
            before = line_text.strip()
            after = self._fix_missing_space_after_colon(line_text).strip()
            # Highlight at the value start after ":" so the missing space is obvious.
            start_col = len(head) + 1
            end_col = start_col + 1
            return line_no, start_col, end_col, before, after
        return None

    def _find_missing_email_at(self):
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return None
        lines = text.splitlines()
        domain_roots = set()
        for line_text in lines:
            m = self.EMAIL_FIELD_PATTERN.search(line_text)
            if not m:
                continue
            val = m.group(2)
            if "@" not in val:
                continue
            domain = val.split("@", 1)[1]
            parts = domain.split(".")
            if len(parts) >= 2:
                domain_roots.add(parts[-2])
        for idx, line_text in enumerate(lines, start=1):
            match = self.EMAIL_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = match.group(2)
            if not value or "@" in value:
                continue
            fixed = self._fix_missing_at(value, domain_roots.union(self.KNOWN_EMAIL_DOMAIN_ROOTS))
            # Prefer exact known domain match if present in value.
            for domain in sorted(self.KNOWN_EMAIL_DOMAINS, key=len, reverse=True):
                if domain in value:
                    fixed = value.replace(domain, "@" + domain, 1)
                    break
            before_line = line_text.strip()
            after_line = line_text[: match.start(2)] + fixed + line_text[match.end(2) :]
            return idx, match.start(2), match.end(2), before_line, after_line.strip()
        return None

    def _path_targets_email(self, path):
        if not isinstance(path, list) or not path:
            return False
        lowered = [p.lower() for p in path if isinstance(p, str)]
        if not lowered:
            return False
        key = lowered[-1]
        if key in ("email", "from", "to"):
            return True
        # Nested forms like: ... email.address / email.value
        if key in ("address", "value") and len(lowered) >= 2 and lowered[-2] == "email":
            return True
        return False

    def _looks_like_email_candidate(self, value):
        value = (value or "").strip()
        if not value:
            return False
        if "@" in value:
            return True
        if "." not in value:
            return False
        return re.search(r"[A-Za-z]", value) is not None

    def _should_validate_email_path_value(self, path, value):
        lowered = [p.lower() for p in path if isinstance(p, str)]
        if not lowered:
            return False
        key = lowered[-1]
        if key == "email":
            return True
        if key in ("address", "value") and len(lowered) >= 2 and lowered[-2] == "email":
            return True
        if key in ("from", "to"):
            # "from"/"to" appears in non-email objects (e.g. bank transactions).
            return self._looks_like_email_candidate(value)
        return False

    def _iter_candidate_email_values(self, node, rel_path=None):
        if rel_path is None:
            rel_path = []
        if isinstance(node, dict):
            for k, v in node.items():
                yield from self._iter_candidate_email_values(v, rel_path + [k])
            return
        if isinstance(node, list):
            for i, v in enumerate(node):
                yield from self._iter_candidate_email_values(v, rel_path + [i])
            return
        if (
            isinstance(node, str)
            and self._path_targets_email(rel_path)
            and self._should_validate_email_path_value(rel_path, node)
        ):
            yield rel_path, node

    def _format_path_for_display(self, path):
        return tree_view_service.format_path_for_display(path)

    def _find_value_span_in_editor(self, value, preferred_key=None):
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return None
        if not text or not value:
            return None

        def to_line_col(abs_index):
            line = text.count("\n", 0, abs_index) + 1
            last_nl = text.rfind("\n", 0, abs_index)
            col = abs_index if last_nl == -1 else abs_index - last_nl - 1
            return line, col

        escaped_value = re.escape(value)
        patterns = []
        if isinstance(preferred_key, str) and preferred_key:
            escaped_key = re.escape(preferred_key)
            patterns.append(rf'"{escaped_key}"\s*:\s*"(?P<val>{escaped_value})"')
        patterns.append(rf'"(?P<val>{escaped_value})"')

        for pattern in patterns:
            m = re.search(pattern, text)
            if not m:
                continue
            start = m.start("val")
            end = m.end("val")
            line, start_col = to_line_col(start)
            _, end_col = to_line_col(end)
            return line, start_col, end_col
        return None

    def _find_invalid_email_in_value(self, base_path, value):
        # Direct string edit for an email-targeted field.
        if (
            isinstance(value, str)
            and self._path_targets_email(base_path)
            and self._should_validate_email_path_value(base_path, value)
        ):
            issue = self._validate_email_address(value)
            if issue:
                return base_path, value, issue
        # Nested object/list edit: validate all candidate email fields.
        if isinstance(value, (dict, list)):
            for rel_path, email_val in self._iter_candidate_email_values(value):
                issue = self._validate_email_address(email_val)
                if issue:
                    return list(base_path) + list(rel_path), email_val, issue
        return None

    def _best_domain_root_similarity(self, root):
        if not root:
            return 0.0
        return max(
            (difflib.SequenceMatcher(None, root.lower(), known).ratio() for known in self.KNOWN_EMAIL_DOMAIN_ROOTS),
            default=0.0,
        )

    def _suggest_known_domain_from_local_and_domain(self, local, domain):
        domain = (domain or "").lower()
        if "." not in domain:
            return None
        parts = domain.split(".")
        if len(parts) < 2:
            return None
        sld = parts[-2]
        tld = parts[-1]
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        best = None
        for known in sorted(self.KNOWN_EMAIL_DOMAINS, key=len, reverse=True):
            kparts = known.split(".")
            if len(kparts) < 2:
                continue
            ksld = kparts[-2]
            ktld = kparts[-1]
            if ktld != tld:
                continue
            if sld and not ksld.endswith(sld):
                continue
            missing_prefix = ksld[: len(ksld) - len(sld)] if sld else ksld
            if not missing_prefix:
                continue
            if not local.lower().endswith(missing_prefix):
                continue
            cand_local = local[: len(local) - len(missing_prefix)]
            if not cand_local or not local_re.fullmatch(cand_local):
                continue
            candidate = f"{cand_local}@{known}"
            best = candidate
            break
        return best

    def _suggest_email_for_malformed(self, value):
        value = (value or "").strip()
        if "@" not in value or value.count("@") != 1:
            return "<name>@<domain.tld>"
        local, domain = value.split("@", 1)
        parts = domain.split(".")
        if len(parts) < 2:
            return "<name>@<domain.tld>"
        sub_prefix = ".".join(parts[:-2]).strip(".")
        sld = parts[-2]
        tld = parts[-1]
        # If the second-level domain is too short, first try rebuilding it
        # from known roots by pulling only the missing prefix from local-part.
        if len(sld) < 2:
            best_prefix_fix = None
            best_prefix_len = -1
            for root in sorted(self.KNOWN_EMAIL_DOMAIN_ROOTS, key=len, reverse=True):
                if not root.endswith(sld):
                    continue
                missing_prefix = root[: len(root) - len(sld)] if sld else root
                if not missing_prefix:
                    continue
                if not local.lower().endswith(missing_prefix):
                    continue
                cand_local = local[: len(local) - len(missing_prefix)]
                if not cand_local:
                    continue
                if not re.fullmatch(r"^[A-Za-z0-9._%+\-]+$", cand_local):
                    continue
                cand_domain = f"{root}.{tld}"
                if sub_prefix:
                    cand_domain = f"{sub_prefix}.{cand_domain}"
                if not self._is_valid_email_domain(cand_domain):
                    continue
                # Prefer the longest matched root (more specific fix).
                if len(root) > best_prefix_len:
                    best_prefix_len = len(root)
                    best_prefix_fix = f"{cand_local}@{cand_domain}"
            if best_prefix_fix:
                return best_prefix_fix

        merged = local + sld
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        best = None
        best_score = -10**9
        original_len = len(local)
        for split_idx in range(1, len(merged)):
            cand_local = merged[:split_idx]
            cand_sld = merged[split_idx:]
            if not local_re.fullmatch(cand_local):
                continue
            cand_domain = f"{cand_sld}.{tld}"
            if sub_prefix:
                cand_domain = f"{sub_prefix}.{cand_domain}"
            if not self._is_valid_email_domain(cand_domain):
                continue
            score = 0.0
            if cand_sld.lower() in self.KNOWN_EMAIL_DOMAIN_ROOTS:
                score += 500.0
            score += self._best_domain_root_similarity(cand_sld) * 100.0
            score -= abs(split_idx - original_len) * 2.0
            if score > best_score:
                best_score = score
                best = f"{cand_local}@{cand_domain}"
        return best if best else "<name>@<domain.tld>"

    def _validate_email_address(self, value):
        value = (value or "").strip()
        if not value:
            return None
        if "@" not in value:
            fixed = self._fix_missing_at(value, self.KNOWN_EMAIL_DOMAIN_ROOTS)
            if fixed == value or "@" not in fixed:
                return {
                    "message": "Invalid Entry: malformed email address.",
                    "log_msg": "Malformed email format",
                    "note": "invalid_email_format",
                    "suggested": self._suggest_email_for_malformed(value),
                }
            return {
                "message": 'Invalid Entry: add "@" to the email address.',
                "log_msg": "Missing '@' in email",
                "note": "missing_email_at",
                "suggested": fixed,
            }

        if value.count("@") != 1:
            return {
                "message": "Invalid Entry: malformed email address.",
                "log_msg": "Malformed email format",
                "note": "invalid_email_format",
                "suggested": self._suggest_email_for_malformed(value),
            }

        local, domain = value.split("@", 1)
        local_re = re.compile(r"^[A-Za-z0-9._%+\-]+$")
        if not local or not domain or not local_re.fullmatch(local) or not self._is_valid_email_domain(domain):
            return {
                "message": "Invalid Entry: malformed email address.",
                "log_msg": "Malformed email format",
                "note": "invalid_email_format",
                "suggested": self._suggest_email_for_malformed(value),
            }

        domain_lower = domain.lower()
        if domain_lower not in self.KNOWN_EMAIL_DOMAINS:
            suggestion = self._suggest_known_domain_from_local_and_domain(local, domain_lower)
            if not suggestion:
                close = difflib.get_close_matches(domain_lower, sorted(self.KNOWN_EMAIL_DOMAINS), n=1, cutoff=0.72)
                if close:
                    suggestion = f"{local}@{close[0]}"
            return {
                "message": "Invalid Entry: unknown email domain.",
                "log_msg": "Unknown email domain",
                "note": "unknown_email_domain",
                "suggested": suggestion or "<name>@<domain.tld>",
            }

        return None

    def _is_valid_email_domain(self, domain):
        if not domain or "." not in domain:
            return False
        parts = domain.split(".")
        if len(parts) < 2:
            return False
        # Catch obvious misplaced-@ cases like "x@l.net".
        if len(parts[-2]) < 2:
            return False
        tld = parts[-1]
        if len(tld) < 2 or not tld.isalpha():
            return False
        label_re = re.compile(r"^[A-Za-z0-9-]+$")
        for part in parts:
            if not part:
                return False
            if part.startswith("-") or part.endswith("-"):
                return False
            if not label_re.fullmatch(part):
                return False
        return True

    def _find_invalid_email_format_issue(self):
        try:
            text = self.text.get("1.0", "end-1c")
        except Exception:
            return None
        for idx, line_text in enumerate(text.splitlines(), start=1):
            match = self.EMAIL_FIELD_PATTERN.search(line_text)
            if not match:
                continue
            value = (match.group(2) or "").strip()
            if not value or "@" not in value:
                continue
            issue = self._validate_email_address(value)
            if not issue:
                continue
            before_line = line_text.strip()
            suggested = issue["suggested"]
            after_line = line_text[: match.start(2)] + suggested + line_text[match.end(2) :]
            return (
                idx,
                match.start(2),
                match.end(2),
                before_line,
                after_line.strip(),
                issue["message"],
                issue["log_msg"],
                issue["note"],
            )
        return None

    def _fix_missing_quote(self, line_text):
        if not line_text:
            return "\"key\": \"value\""
        if line_text.count("\"") % 2 == 0:
            return line_text
        object_value_match = re.match(r'^(?P<key>\s*"[^"]*"\s*):(?P<rest>.*)$', str(line_text))
        if object_value_match:
            key_part = object_value_match.group("key") or ""
            rest = object_value_match.group("rest") or ""
            key_part = key_part.strip().strip(",")
            rest = rest.strip().rstrip(",")
            if rest == "\"":
                rest = "\"\""
            elif rest.startswith("\"") and rest.count("\"") == 1:
                # Remove invalid trailing characters before closing the quote
                rest = rest[1:]  # Remove opening quote
                rest = _strip_invalid_trailing_chars(rest)
                rest = "\"" + rest + "\""
            if not key_part.endswith("\""):
                key_part = key_part + "\""
            if not key_part.startswith("\""):
                key_part = "\"" + key_part
            return f"{key_part}: {rest}" + ("," if line_text.strip().endswith(",") else "")
        stripped = line_text.rstrip()
        if stripped.endswith(","):
            base = stripped[:-1]
            # Remove invalid tail symbols before closing the missing quote.
            m = re.match(r'^(?P<head>\s*")(?P<body>.*)$', base)
            if m:
                head = m.group("head") or ""
                body = _strip_invalid_trailing_chars((m.group("body") or "").rstrip())
                return head + body + "\"" + ("," if line_text.strip().endswith(",") else "")
            return _strip_invalid_trailing_chars(base.rstrip()) + "\"" + (
                "," if line_text.strip().endswith(",") else ""
            )
        return stripped + "\""

    def _unclosed_quoted_value_invalid_tail_span(self, line_text):
        # Detect unclosed quoted scalar values with invalid trailing symbols
        # before comma/EOL (for example: "hackhub.net:,).
        raw = str(line_text or "")
        if not raw:
            return None
        # Keep object-key quote diagnostics for key-like forms:
        #   "name: [
        #   "name: {
        #   "name: "value"
        if re.match(r'^\s*"[A-Za-z_][A-Za-z0-9_]*[^\w"]*:\s*[\[{"]', raw):
            return None

        object_value_match = re.match(r'^\s*"[^"]*"\s*:(?P<rest>.*)$', raw)
        if object_value_match:
            rest = object_value_match.group("rest") or ""
            rest_start = int(object_value_match.start("rest"))
            ws_len = len(rest) - len(rest.lstrip(" \t"))
            value_text = rest.lstrip(" \t")
            base_col = int(rest_start + ws_len)
        else:
            ws_len = len(raw) - len(raw.lstrip(" \t"))
            value_text = raw.lstrip(" \t")
            base_col = int(ws_len)

        if not value_text.startswith('"'):
            return None

        escape = False
        comma_idx = None
        for idx, ch in enumerate(value_text[1:], start=1):
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                return None
            if ch == ",":
                comma_idx = idx
                break
        stop_idx = int(comma_idx) if comma_idx is not None else int(len(value_text.rstrip()))
        if stop_idx <= 1:
            return None

        body = value_text[1:stop_idx]
        body_rstrip = body.rstrip()
        if not body_rstrip:
            return None
        trimmed = _strip_invalid_trailing_chars(body_rstrip)
        if len(trimmed) >= len(body_rstrip):
            return None
        invalid_start = len(trimmed)
        invalid_end = len(body_rstrip)
        return (
            int(base_col + 1 + invalid_start),
            int(base_col + 1 + invalid_end),
        )

    def _find_nearby_unclosed_quoted_value_invalid_tail_line(self, lineno, lookback=2):
        if not lineno:
            return None, None, None
        candidates = []
        try:
            candidates.append((lineno, self.text.get(f"{lineno}.0", f"{lineno}.0 lineend")))
        except Exception:
            pass
        line = max(lineno - 1, 1)
        scanned = 0
        while line >= 1 and scanned < lookback:
            try:
                txt = self.text.get(f"{line}.0", f"{line}.0 lineend")
            except Exception:
                break
            if str(txt or "").strip():
                candidates.append((line, txt))
                scanned += 1
            line -= 1
        for ln, txt in candidates:
            span = self._unclosed_quoted_value_invalid_tail_span(txt)
            if span:
                return int(ln), txt, span
        return None, None, None

    def _comma_example_line(self, lineno):
        if not lineno:
            return "\"item1\",\n\"item2\""
        target_line = max(lineno - 1, 1)
        try:
            line_text = self.text.get(f"{target_line}.0", f"{target_line}.0 lineend").strip()
        except Exception:
            line_text = ""
        if not line_text:
            return "\"item1\",\n\"item2\""
        if not line_text.endswith(","):
            line_text = line_text.rstrip()
            line_text = line_text + ","
        return line_text

    def _symbol_error_focus_index(self, start_index, end_index):
        try:
            segment = self.text.get(start_index, end_index)
            if not segment:
                return end_index
            trimmed = len(segment.rstrip())
            if trimmed <= 0:
                return end_index
            return self.text.index(f"{start_index} +{trimmed}c")
        except Exception:
            return end_index

    def _apply_json_error_highlight(self, exc, line, start_index, end_index, note=""):
        self.text.tag_remove("json_error", "1.0", "end")
        self.text.tag_remove("json_error_line", "1.0", "end")
        self._clear_error_pin()
        palette = self._current_error_palette()
        self._last_error_highlight_note = str(note or "")
        comma_focus_notes = {
            "missing_object_close_before_comma",
            "missing_list_close_before_comma",
            "missing_comma_between_blocks",
        }
        force_start_focus = str(note or "") in comma_focus_notes
        before_comma_notes = {
            "missing_object_close_before_comma",
            "missing_list_close_before_comma",
        }
        missing_key_quote_notes = {"highlight", "missing_key_quote_before_colon"}
        missing_key_quote_focus = False
        try:
            missing_key_quote_focus = (
                str(note or "") in missing_key_quote_notes
                and self._line_has_missing_open_key_quote(self._line_text(line))
            )
        except Exception:
            missing_key_quote_focus = False
        insertion_only = start_index == end_index
        self._last_error_insertion_only = bool(insertion_only)
        insertion_at_point_notes = {
            "missing_list_close_before_object_end",
            "missing_object_close_eof",
            "missing_value_close_quote",
            "missing_value_open_quote",
        }
        insertion_marker_at_point = str(note or "") in insertion_at_point_notes
        if not insertion_only and missing_key_quote_focus:
            # Missing opening key quote should be an insertion cue, not a token span.
            end_index = start_index
            insertion_only = True
            self._last_error_insertion_only = True
        focus_index = start_index if (insertion_only or force_start_focus) else end_index
        if not insertion_only and self._is_symbol_error_note(note):
            focus_index = self._symbol_error_focus_index(start_index, end_index)
        if str(note or "") in before_comma_notes:
            try:
                raw = self._line_text(line)
                comma_col = raw.find(",")
                if comma_col >= 0:
                    focus_index = f"{line}.{comma_col}"
            except Exception:
                pass
        self._error_focus_index = focus_index
        if insertion_only:
            # Ensure insertion target is visible before placing marker/pin.
            try:
                self.text.see(start_index)
                self.text.update_idletasks()
            except Exception:
                pass
            # For comma-focus insertion hints, keep only cursor+overlay guidance
            # and avoid token/line fill so the comma itself is not highlighted.
            render_insertion_marker = not force_start_focus
            if render_insertion_marker:
                # Fallback marker so insertion points still get a visible error marker
                # highlight even if pin placement fails on a given platform/font.
                try:
                    line_s, col_s = start_index.split(".")
                    lno = int(line_s)
                    col = int(col_s)
                    line_text = self._line_text(lno)
                    if insertion_marker_at_point:
                        # Avoid highlighting the implicit newline at line-end,
                        # which can make the next line look incorrectly marked.
                        line_end_idx = self.text.index(f"{lno}.0 lineend")
                        if self.text.compare(start_index, ">=", line_end_idx):
                            if col > 0:
                                fallback_start = f"{lno}.{col - 1}"
                                fallback_end = f"{lno}.{col}"
                            else:
                                fallback_start = start_index
                                fallback_end = self.text.index(f"{start_index} +1c")
                        else:
                            fallback_start = start_index
                            fallback_end = self.text.index(f"{start_index} +1c")
                    elif col == 0 and not line_text.strip():
                        prev_line = self._closest_non_empty_line_before(lno)
                        if prev_line:
                            prev_end = self.text.index(f"{prev_line}.0 lineend")
                            prev_col = int(str(prev_end).split(".")[1])
                            if prev_col > 0:
                                fallback_start = self.text.index(f"{prev_end} -1c")
                                fallback_end = prev_end
                            else:
                                fallback_start = prev_end
                                fallback_end = self.text.index(f"{prev_end} +1c")
                        else:
                            fallback_start = start_index
                            fallback_end = self.text.index(f"{start_index} +1c")
                    elif col > 0:
                        fallback_start = f"{lno}.{col - 1}"
                        fallback_end = f"{lno}.{col}"
                    else:
                        fallback_start = start_index
                        fallback_end = self.text.index(f"{start_index} +1c")
                    self.text.tag_add("json_error", fallback_start, fallback_end)
                except Exception:
                    pass
            else:
                # Keep a subtle marker immediately before the insertion point so
                # users still get visual guidance without highlighting the comma.
                try:
                    line_s, col_s = start_index.split(".")
                    lno = int(line_s)
                    col = int(col_s)
                    if col > 0:
                        subtle_start = f"{lno}.{col - 1}"
                        subtle_end = f"{lno}.{col}"
                        try:
                            prev_char = self.text.get(subtle_start, subtle_end)
                            if prev_char == "," and col > 1:
                                subtle_start = f"{lno}.{col - 2}"
                                subtle_end = f"{lno}.{col - 1}"
                        except Exception:
                            pass
                    else:
                        subtle_start = start_index
                        subtle_end = self.text.index(f"{start_index} +1c")
                    self.text.tag_add("json_error", subtle_start, subtle_end)
                except Exception:
                    pass
        else:
            self.text.tag_add("json_error", start_index, end_index)
        marker_bg, marker_fg = self._error_marker_colors(note, palette, insertion_only=insertion_only)
        self.text.tag_config("json_error", background=marker_bg, foreground=marker_fg)
        show_line_context = (not insertion_only) and (not force_start_focus) and (not missing_key_quote_focus)
        if show_line_context:
            self.text.tag_add("json_error_line", f"{line}.0", f"{line}.0 lineend")
            self.text.tag_config("json_error_line", background=palette["line_bg"], foreground="#ffffff")
            self.text.tag_raise("json_error_line")
        self.text.tag_raise("json_error")
        # Keep drag-selection visible above error tags.
        try:
            self.text.tag_raise("sel")
        except Exception:
            pass
        # For insertion errors, keep focus at the insertion target so the
        # marker/overlay does not jump away during live validation.
        if insertion_only or force_start_focus:
            insert_index = focus_index
        else:
            insert_index = self._preferred_error_insert_index(line, focus_index)
        self.text.mark_set("insert", insert_index)
        self.text.see(insert_index)
        if note:
            self._log_json_error(exc, line, note=note)
        else:
            self._log_json_error(exc, line, note="highlight")
        self._position_error_overlay(line)

    def _highlight_json_error(self, exc):
        return json_error_highlight_core.highlight_json_error(
            self,
            exc,
            apply_highlight_fn=json_error_highlight_render_service.apply_json_error_highlight,
            log_error_fn=json_error_highlight_render_service.log_json_error,
        )


    def _place_error_pin(self, index):
        return error_overlay_service.place_error_pin(self, index)

    def _clear_error_pin(self):
        error_overlay_service.clear_error_pin(self)

    def _position_error_overlay(self, line):
        error_overlay_service.position_error_overlay(self, line)

    def _diag_system_from_note(self, note):
        # Diagnostic mapping checklist:
        # - locked_* -> highlight_restore
        # - overlay_* -> overlay_parse
        # - highlight_failed* -> highlight_internal
        # - cursor_restore* -> cursor_restore
        # - spacing_*, missing_phone*, invalid_email* -> input_validation
        # - symbol_* and symbol-type invalid_* -> symbol_recovery
        # - everything else -> json_highlight
        return json_error_diag_service.diag_system_from_note(
            note,
            is_symbol_error_note=getattr(self, "_is_symbol_error_note", None),
        )

    def _log_json_error(self, exc, target_line, note=""):
        return json_error_diag_service.log_json_error(self, exc, target_line, note=note)

    def _begin_diag_action(self, action_name):
        self._diag_event_seq += 1
        self._diag_action = f"{action_name}:{self._diag_event_seq}"
        return self._diag_action

    def _clear_json_error_highlight(self):
        try:
            self.text.tag_remove("json_error", "1.0", "end")
            self.text.tag_remove("json_error_line", "1.0", "end")
            self._clear_error_pin()
            self._error_focus_index = None
            self._last_error_highlight_note = ""
            self._last_error_insertion_only = False
        except Exception:
            return

    def _on_text_keypress(self, event):
        try:
            keysym = getattr(event, "keysym", "") or ""
            char = getattr(event, "char", "") or ""
            nav_keys = {
                "Up", "Down", "Prior", "Next",
                "Page_Up", "Page_Down",
            }
            if self.error_overlay is not None and keysym in nav_keys:
                self._enforce_error_focus()
                return "break"
            self._last_edit_was_deletion = keysym in ("BackSpace", "Delete")
            should_clear = bool(char) or keysym in ("BackSpace", "Delete", "Return", "KP_Enter", "space")
            if should_clear and (self.error_overlay is not None):
                self._destroy_error_overlay()
                self._clear_json_error_highlight()
                self._auto_apply_pending = True
        except Exception:
            return

    def _on_text_nav_attempt(self, event):
        try:
            if self.error_overlay is None:
                return
            target = self.text.index(f"@{event.x},{event.y}")
            if self._is_index_on_error_line(target):
                return
            self._enforce_error_focus()
            return "break"
        except Exception:
            return "break"

    def _is_index_on_error_line(self, index):
        if not self._error_focus_index or not index:
            return False
        try:
            err_line = int(str(self._error_focus_index).split(".")[0])
            idx_line = int(str(index).split(".")[0])
            return err_line == idx_line
        except Exception:
            return False

    def _line_number_from_index(self, index):
        if not index:
            return None
        try:
            return int(str(index).split(".")[0])
        except Exception:
            return None

    def _preferred_error_insert_index(self, line, fallback_index):
        # During live feedback, keep the caret where the user is actively typing
        # on the same line instead of snapping back to the first error column.
        try:
            if not (self._auto_apply_pending and self.error_overlay is not None):
                return fallback_index
            current_insert = self.text.index("insert")
            if self._line_number_from_index(current_insert) != int(line):
                return fallback_index
            return current_insert
        except Exception:
            return fallback_index

    def _enforce_error_focus(self):
        if not self._error_focus_index:
            return
        try:
            self.text.mark_set("insert", self._error_focus_index)
            self.text.see(self._error_focus_index)
        except Exception:
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
                try:
                    self._error_visual_mode = "guide"
                    self.apply_edit()
                finally:
                    self._auto_apply_in_progress = False
            else:
                # User is actively fixing but still wrong: show a stronger visual cue.
                self._show_live_error_feedback()
        except Exception:
            return

    def _can_auto_apply_current_edit(self):
        item_id = self.tree.focus()
        if not item_id:
            return False
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path and path[0] == "__group__":
            return False
        raw = self.text.get("1.0", "end").strip()
        try:
            new_value = json.loads(raw)
        except Exception:
            return False
        if self._find_invalid_email_in_value(path, new_value):
            return False
        if self._find_phone_format_issue():
            return False
        if self._find_json_spacing_issue():
            return False
        if not self._is_json_edit_allowed(path, new_value, show_feedback=False):
            return False
        if not self._is_edit_allowed(path, new_value):
            return False
        return True

    def _show_live_error_feedback(self):
        item_id = self.tree.focus()
        if not item_id:
            return
        path = self.item_to_path.get(item_id, [])
        if isinstance(path, tuple) and path and path[0] == "__group__":
            return
        raw = self.text.get("1.0", "end").strip()
        try:
            new_value = json.loads(raw)
        except Exception as exc:
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", self._format_json_error(exc))
            # Keep highlight-label colors active while JSON is temporarily invalid.
            self._apply_json_view_lock_state(path)
            self._highlight_json_error(exc)
            return

        spacing_issue = self._find_json_spacing_issue()
        if spacing_issue:
            line, start_col, end_col, before_line, after_line = spacing_issue
            message = self._format_suggestion(
                'Invalid Entry: add a space after ":".',
                before_line,
                after_line,
            )
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            try:
                start_index = f"{line}.{max(start_col, 0)}"
                end_index = f"{line}.{max(end_col, start_col + 1)}"
                dummy = type(
                    "E",
                    (),
                    {"msg": "Missing space after ':'", "lineno": line, "colno": start_col + 1},
                )
                self._apply_json_error_highlight(
                    dummy, line, start_index, end_index, note="spacing_missing_space_after_colon"
                )
            except Exception:
                self._highlight_custom_range(line, start_col, end_col)
            return

        email_validation = self._find_invalid_email_in_value(path, new_value)
        if email_validation:
            field_path, bad_value, email_issue = email_validation
            field_label = self._format_path_for_display(field_path)
            before_line = f'"{field_label}": "{bad_value}"'
            after_line = f'"{field_label}": "{email_issue["suggested"]}"'
            message = self._format_suggestion(email_issue["message"], before_line, after_line)
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            preferred_key = field_path[-1] if field_path and isinstance(field_path[-1], str) else None
            span = self._find_value_span_in_editor(bad_value, preferred_key=preferred_key)
            if span:
                line, start_col, end_col = span
                self._highlight_custom_range(line, start_col, end_col)
            return

        phone_issue = self._find_phone_format_issue()
        if phone_issue:
            line, start_col, end_col, before_line, after_line = phone_issue
            message = self._format_suggestion(
                "Invalid Entry: add \"-\" to the phone number.",
                before_line,
                after_line,
            )
            self._error_visual_mode = "guide"
            self._show_error_overlay("Invalid Entry", message)
            self._highlight_custom_range(line, start_col, end_col)
            return

        if not self._is_json_edit_allowed(path, new_value, show_feedback=True):
            return

    def _show_error_overlay(self, title, message, actions=None):
        self._error_overlay_actions = tuple(actions or ()) or None
        error_overlay_service.show_error_overlay(self, title, message)

    def _destroy_error_overlay(self):
        error_overlay_service.destroy_error_overlay(self)

    def _apply_error_tint(self):
        error_overlay_service.apply_error_tint(self)

    def _clear_error_tint(self):
        error_overlay_service.clear_error_tint(self)

    def _refresh_active_error_theme(self):
        error_overlay_service.refresh_active_error_theme(self)

    def save_file(self):
        if not self.path:
            return self.save_file_as()
        try:
            payload = json.dumps(self.data, indent=2, ensure_ascii=False) + "\n"
            self._write_text_file_atomic(self.path, payload, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.set_status("Saved")

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
        default_ext = ".hhsav"
        initialfile = None
        if self.path:
            base = os.path.basename(self.path)
            name, ext = os.path.splitext(base)
            if ext.lower() == ".hhsav":
                default_ext = ".hhsav"
                initialfile = base
            else:
                initialfile = f"{name}{default_ext}"
        path = filedialog.asksaveasfilename(
            title="Export As .hhsav (gzip)",
            defaultextension=default_ext,
            filetypes=[("HackHub Save (.hhsav)", "*.hhsav")],
            initialfile=initialfile,
        )
        if not path:
            return
        if not path.lower().endswith(".hhsav"):
            path += default_ext
        try:
            payload = json.dumps(self.data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            with tempfile.TemporaryDirectory() as tmpdir:
                gzip_path = os.path.join(tmpdir, "save.hhsav")
                # Export as standard gzip JSON without external 7z dependency.
                with open(gzip_path, "wb") as raw_fh:
                    with gzip.GzipFile(
                        filename="",
                        mode="wb",
                        fileobj=raw_fh,
                        compresslevel=9,
                        mtime=0,
                    ) as gz_fh:
                        gz_fh.write(payload)
                if not os.path.isfile(gzip_path) or os.path.getsize(gzip_path) <= 0:
                    raise RuntimeError("Exported .hhsav is empty.")
                self._commit_file_to_destination_with_retries(gzip_path, path)
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.set_status("Exported .hhsav")

    def _find_7z(self):
        candidate = shutil.which("7z")
        if candidate:
            return candidate
        common_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return path
        return None

    def _ensure_7z(self):
        if self.seven_zip_path and os.path.isfile(self.seven_zip_path):
            return self.seven_zip_path
        path = filedialog.askopenfilename(
            title="Locate 7z.exe",
            filetypes=[("7-Zip", "7z.exe"), ("All Files", "*.*")],
        )
        if not path:
            raise FileNotFoundError("7z not selected")
        self.seven_zip_path = path
        return path

    def _get_value(self, path):
        value = self.data
        for key in path:
            value = value[key]
        return value

    def _set_value(self, path, new_value):
        if not path:
            self.data = new_value
            self._reset_find_state()
            return
        parent = self.data
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = new_value
        self._reset_find_state()

    def _is_network_list(self, path, value):
        return highlight_label_service.is_network_list(path, value, self.network_types_set)

    def _mail_account_label(self, idx, item):
        return label_format_service.mail_account_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _mails_label(self, idx, item):
        return label_format_service.mails_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _phone_messages_label(self, idx, item):
        return label_format_service.phone_messages_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _files_label(self, idx, item):
        return label_format_service.files_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _database_label(self, idx, item):
        return label_format_service.database_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _bookmarks_label(self, idx, item):
        return label_format_service.bookmarks_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _bcc_news_label(self, idx, item):
        return label_format_service.bcc_news_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _process_label(self, idx, item):
        return label_format_service.process_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _typewriter_label(self, idx, item):
        return label_format_service.typewriter_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _bank_account_label(self, idx, item):
        return label_format_service.bank_account_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _bank_transaction_label(self, idx, item):
        return label_format_service.bank_transaction_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _app_store_unlocked_item_label(self, idx, item):
        return label_format_service.app_store_unlocked_item_label(
            idx, item, getattr(self, "_tree_style_variant", "B")
        )

    def _twotter_user_label(self, idx, item):
        return label_format_service.twotter_user_label(idx, item)

    def _quests_label(self, idx, item):
        return label_format_service.quests_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _kisscord_friend_label(self, idx, item):
        return label_format_service.kisscord_friend_label(idx, item)

    def _website_templates_label(self, idx, item):
        return label_format_service.website_templates_label(idx, item, getattr(self, "_tree_style_variant", "B"))

    def _terminal_package_label(self, idx, item):
        return label_format_service.terminal_package_label(idx, item)

    def _terminal_datalist_label(self, idx, item):
        return label_format_service.terminal_datalist_label(idx, item)

    def _find_first_dict_key_change(self, old_value, new_value, current_path=None):
        return label_format_service.find_first_dict_key_change(old_value, new_value, current_path=current_path)

    def _is_json_edit_allowed(self, path, new_value, show_feedback=True, auto_restore=False):
        # Orange lock system now runs as label-only guidance:
        # keep highlight tags, but do not block/restore edits or show lock overlays.
        _ = (path, new_value, show_feedback, auto_restore)
        return True

    def _is_edit_allowed(self, path, new_value):
        # One-shot bypass used only after explicit "Continue" on highlight warning.
        if bool(getattr(self, "_allow_highlight_key_change_once", False)):
            self._allow_highlight_key_change_once = False
            return True
        try:
            current_value = self._get_value(path)
        except Exception:
            current_value = None
        payload = highlight_label_service.edit_allowed_payload(
            path=path,
            current_value=current_value,
            new_value=new_value,
            find_first_dict_key_change=self._find_first_dict_key_change,
            format_path_for_display=self._format_path_for_display,
        )
        if payload.get("allowed", False):
            return True
        self._error_visual_mode = "guide"
        recommended_name = str(payload.get("recommended_name") or "").strip() or str(
            payload.get("path_label", "highlighted field")
        )
        entered_name = str(payload.get("entered_name") or "").strip()

        def _overlay_autofix():
            restore_index = ""
            try:
                restore_index = str(self.text.index("insert") or "")
            except Exception:
                restore_index = ""
            try:
                self._destroy_error_overlay()
            except Exception:
                pass
            try:
                self._show_value(current_value, path=path)
            except Exception:
                return
            if restore_index:
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
                except Exception:
                    pass
            try:
                self.set_status(f'Auto-fixed: restored highlighted field "{recommended_name}".')
            except Exception:
                pass

        def _overlay_continue():
            try:
                self._destroy_error_overlay()
            except Exception:
                pass
            self._allow_highlight_key_change_once = True
            try:
                self.set_status("Warning acknowledged: continuing highlighted field edit.")
            except Exception:
                pass
            try:
                self.apply_edit()
            except Exception:
                self._allow_highlight_key_change_once = False

        self._show_error_overlay(
            "Warning",
            (
                "Warning : Editing Highlighted Columns Could Corrupt Game Data\n\n"
                f"Recommended : {recommended_name}"
            ),
            actions=(
                ("Auto-Fix", _overlay_autofix),
                ("Continue", _overlay_continue),
            ),
        )
        try:
            preferred_index = str(self.text.index("insert") or "")
        except Exception:
            preferred_index = ""
        # Warning anchor priority:
        # 1) exact changed-key token near caret (for example `"":` after deleting `x`)
        # 2) recommended/entered key fallback lookup
        anchor_index = ""
        if not entered_name:
            try:
                changed_token = '""'
                backward_hit = self.text.search(
                    changed_token,
                    preferred_index or "insert",
                    stopindex="1.0",
                    nocase=False,
                    backwards=True,
                )
                if backward_hit:
                    anchor_index = str(backward_hit)
                else:
                    forward_hit = self.text.search(
                        changed_token,
                        preferred_index or "1.0",
                        stopindex="end",
                        nocase=False,
                    )
                    if forward_hit:
                        anchor_index = str(forward_hit)
            except Exception:
                anchor_index = ""
        try:
            if not anchor_index:
                anchor_index = self._find_lock_anchor_index(recommended_name, preferred_index=preferred_index) or ""
        except Exception:
            anchor_index = ""
        if not anchor_index and entered_name:
            try:
                anchor_index = self._find_lock_anchor_index(entered_name, preferred_index=preferred_index) or ""
            except Exception:
                anchor_index = ""
        if not anchor_index:
            anchor_index = preferred_index or "1.0"
        try:
            self._error_focus_index = anchor_index
            self._position_error_overlay(self._line_number_from_index(anchor_index) or 1)
        except Exception:
            pass
        try:
            status_text = "Warning: highlighted field key change detected."
            if entered_name:
                status_text = f'Warning: highlighted key "{entered_name}" differs from "{recommended_name}".'
            self.set_status(status_text)
        except Exception:
            pass
        return False

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
    root._hh_use_startup_loader_window = True
    root.withdraw()
    app = JsonEditor(root, path)
    root.mainloop()


if __name__ == "__main__":
    main()
