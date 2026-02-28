from tkinter import ttk
import tkinter as tk
from collections import deque
import hashlib
import json
import time
import sys
import os
import ctypes
from typing import Any
from core import startup_loader as startup_loader_core
from core.exceptions import EXPECTED_ERRORS
import core.domain_impl.json.json_io_core as document_io_service

PHASE1_FIND_INDEX_MAX_ITEMS = 1200
PHASE2_DATA_PREWARM_DELAY_MS = 220
PHASE2_DATA_PREWARM_RETRY_DELAY_MS = 320


def is_prewarm_complete(owner: Any) -> bool:
        """Return True when no deferred theme prewarm work is pending."""
        if getattr(owner, "_theme_prewarm_after_id", None):
            return False
        queue = list(getattr(owner, "_theme_prewarm_queue", []) or [])
        if queue:
            return False
        tasks = getattr(owner, "_theme_prewarm_tasks", None)
        if tasks is None:
            return True
        try:
            return len(tasks) == 0
        except EXPECTED_ERRORS:
            return False


def get_cached_rgba_image(owner: Any, path: Any, image_module: Any) -> Any:
        """Load and cache RGBA-converted source images used in theme-render paths."""
        cache = getattr(owner, "_theme_rgba_image_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            owner._theme_rgba_image_cache = cache
        key = os.path.abspath(str(path or ""))
        if not key:
            return None
        cached = cache.get(key)
        if cached is not None:
            try:
                return cached.copy()
            except (OSError, ValueError, TypeError, AttributeError):
                return cached
        with image_module.open(key) as source_file:
            rgba = source_file.convert("RGBA")
        put = getattr(owner, "_bounded_cache_put", None)
        if callable(put):
            put(cache, key, rgba, max_items=64)
        else:
            cache[key] = rgba
        try:
            return rgba.copy()
        except (OSError, ValueError, TypeError, AttributeError):
            return rgba


def _bounded_sequence(entries: Any, max_items: int) -> list[Any]:
        if not isinstance(entries, list):
            return []
        use_max_items = max(1, int(max_items or 1))
        if len(entries) <= use_max_items:
            return list(entries)
        return list(entries[:use_max_items])


def _is_toolbar_interaction_active(owner: Any) -> bool:
        try:
            toolbar_buttons = dict(getattr(owner, "_toolbar_buttons", {}) or {})
            pointer_fn = getattr(owner, "_pointer_within_widget", None)
            for button in toolbar_buttons.values():
                if button is None:
                    continue
                try:
                    if not button.winfo_exists():
                        continue
                except (tk.TclError, RuntimeError, AttributeError):
                    continue
                if bool(getattr(button, "_siindbad_scan_running", False)):
                    return True
                if callable(pointer_fn):
                    try:
                        if pointer_fn(button):
                            return True
                    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                        pass
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return False
        return False


def _is_document_load_active_or_cooling(owner: Any) -> bool:
        if bool(getattr(owner, "_document_load_in_progress", False)):
            return True
        cooldown_checker = getattr(owner, "_is_document_load_cooldown_active", None)
        if callable(cooldown_checker):
            try:
                return bool(cooldown_checker())
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                return False
        last_completed_ts = float(getattr(owner, "_document_load_last_completed_ts", 0.0) or 0.0)
        if last_completed_ts <= 0.0:
            return False
        quiet_window_ms = max(0.0, float(getattr(owner, "_document_load_quiet_window_ms", 220) or 220))
        if quiet_window_ms <= 0.0:
            return False
        elapsed_ms = max(0.0, (time.perf_counter() - last_completed_ts) * 1000.0)
        return elapsed_ms < quiet_window_ms


def theme_palette_for_variant(variant: Any) -> Any:
    use_variant = str(variant).upper()
    match use_variant:
        case "KAMUE":
            return {
                "bg": "#06040d",
                "fg": "#e9e2f6",
                "tree_fg": "#ead9ff",
                "tree_selected_fg": "#ffffff",
                "panel": "#0d061c",
                "accent": "#180c31",
                "button_active": "#25124f",
                "button_pressed": "#0f071f",
                "select_bg": "#2d155f",
                "select_fg": "#ffffff",
                "title_bar_bg": "#180c32",
                "title_bar_fg": "#eee8ff",
                "title_bar_border": "#30195c",
                "credit_bg": "#06030d",
                "credit_border": "#170c31",
                "credit_label_fg": "#c9b9e8",
                "find_border": "#cfb5ee",
                "logo_border_outer": "#6b37b6",
                "logo_border_inner": "#b678ea",
            }
        case _:
            return {
                "bg": "#0f131a",
                "fg": "#e6e6e6",
                "tree_fg": "#d7f2ff",
                "tree_selected_fg": "#ffffff",
                "panel": "#161b24",
                "accent": "#2a3342",
                "button_active": "#3a465c",
                "button_pressed": "#222a36",
                "select_bg": "#2f3a4d",
                "select_fg": "#ffffff",
                "title_bar_bg": "#122639",
                "title_bar_fg": "#d7ebf7",
                "title_bar_border": "#264b64",
                "credit_bg": "#0b1118",
                "credit_border": "#1f2f3f",
                "credit_label_fg": "#b5cade",
                "find_border": "#ffffff",
                "logo_border_outer": "#349fc7",
                "logo_border_inner": "#a9ddf0",
            }


def theme_chip_palette(variant: Any) -> Any:
    use_variant = str(variant).upper()
    match use_variant:
        case "KAMUE":
            return {"bg": "#2a1450", "fg": "#e7dcff", "border": "#6b37b6"}
        case _:
            return {"bg": "#132230", "fg": "#d4e3ee", "border": "#4e6e86"}


def tree_variant_chip_palette(variant: Any) -> Any:
    use_variant = str(variant).upper()
    match use_variant:
        case "B":
            return {"bg": "#173042", "fg": "#e8f5ff", "border": "#6bbde3"}
        case _:
            return {"bg": "#0f1b29", "fg": "#9db9cf", "border": "#2f4a61"}


def bug_chip_palette(variant: Any, footer_style_variant: Any="B") -> Any:
    use_variant = str(variant).upper()
    use_footer = str(footer_style_variant).upper()
    match (use_footer, use_variant):
        case ("B", "KAMUE"):
            return {"bg": "#2a1450", "fg": "#f0e7ff", "border": "#6b37b6", "active_bg": "#2a1450"}
        case ("B", _):
            return {"bg": "#132230", "fg": "#e6f6ff", "border": "#4e6e86", "active_bg": "#132230"}
        case (_, "KAMUE"):
            return {"bg": "#23103c", "fg": "#f0e6ff", "border": "#6b37b6", "active_bg": "#4a2781"}
        case _:
            return {"bg": "#10212f", "fg": "#e6f6ff", "border": "#4e6e86", "active_bg": "#1f4a67"}


def footer_badge_palette(variant: Any, footer_style_variant: Any="B") -> Any:
    use_variant = str(variant).upper()
    use_footer = str(footer_style_variant).upper()
    match (use_footer, use_variant):
        case ("B", "KAMUE"):
            return {"bg": "#2a1450", "fg": "#d8ccec", "border": "#6b37b6"}
        case ("B", _):
            return {"bg": "#132230", "fg": "#c2d4e2", "border": "#4e6e86"}
        case (_, "KAMUE"):
            return {"bg": "#2a1450", "fg": "#d8ccec", "border": "#6b37b6"}
        case _:
            return {"bg": "#132230", "fg": "#c2d4e2", "border": "#4e6e86"}


def tree_marker_palette(theme_variant: Any) -> Any:
    match str(theme_variant).upper():
        case "KAMUE":
            return {
                "main_fill": "#b57bff",
                "main_edge": "#ecd8ff",
                "sub_edge": "#d5b8ff",
                "sub_fill": "#dcbfff",
            }
        case _:
            return {
                "main_fill": "#6ecdf6",
                "main_edge": "#b8ecff",
                "sub_edge": "#9fdcf7",
                "sub_fill": "#8fe7ff",
            }


def _apply_dark_theme(owner: Any):
        palette = owner._theme_palette_for_variant(getattr(owner, "_app_theme_variant", "SIINDBAD"))
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

        owner.root.configure(bg=bg)

        style = ttk.Style(owner.root)
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
        owner._v_scrollbar_style = "Editor.Vertical.TScrollbar"
        owner._h_scrollbar_style = "Editor.Horizontal.TScrollbar"
        style.configure(
            owner._v_scrollbar_style,
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
            owner._v_scrollbar_style,
            background=[("active", button_active), ("pressed", button_pressed)],
            arrowcolor=[("disabled", "#7a7a7a")],
        )
        style.configure(
            owner._h_scrollbar_style,
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
            owner._h_scrollbar_style,
            background=[("active", button_active), ("pressed", button_pressed)],
            arrowcolor=[("disabled", "#7a7a7a")],
        )

        tree_is_variant_b = str(getattr(owner, "_tree_style_variant", "B")).upper() == "B"
        if tree_is_variant_b:
            tree_fg = owner._blend_hex_color(tree_fg, panel, 0.22)
        owner._apply_tree_style(
            style=style,
            panel=panel,
            tree_fg=tree_fg,
            select_bg=select_bg,
            select_fg=select_fg,
        )
        owner._theme = {
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
        owner._apply_windows_titlebar_theme(bg=title_bar_bg, fg=title_bar_fg, border=title_bar_border)
        owner.root.after(
            0,
            lambda: owner._apply_windows_titlebar_theme(
                bg=title_bar_bg, fg=title_bar_fg, border=title_bar_border
            ),
        )


def _apply_windows_titlebar_theme(owner: Any, bg=None, fg=None, border=None, window_widget=None):
        # Backward compatibility: older call sites passed the window as the first positional arg.
        if window_widget is None and bg is not None and hasattr(bg, "winfo_id"):
            window_widget = bg
            bg = None
        if sys.platform != "win32":
            return
        target = window_widget or owner.root
        try:
            dwmapi = ctypes.windll.dwmapi
            user32 = ctypes.windll.user32
            target.update_idletasks()
            hwnd = user32.GetParent(target.winfo_id()) or target.winfo_id()
        except EXPECTED_ERRORS:
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
            except EXPECTED_ERRORS:
                return False

        theme = getattr(owner, "_theme", {}) or {}
        variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
        default_bg = "#180c32" if variant == "KAMUE" else "#102535"
        default_fg = "#eee8ff" if variant == "KAMUE" else "#e6f6ff"
        default_border = "#30195c" if variant == "KAMUE" else "#2a5a7a"
        effective_bg = bg or theme.get("title_bar_bg", default_bg)
        effective_fg = fg or theme.get("title_bar_fg", default_fg)
        effective_border = border or theme.get("title_bar_border", default_border)
        signature_by_hwnd = getattr(owner, "_titlebar_theme_signature_by_hwnd", None)
        if not isinstance(signature_by_hwnd, dict):
            signature_by_hwnd = {}
            owner._titlebar_theme_signature_by_hwnd = signature_by_hwnd
        signature = (str(effective_bg or ""), str(effective_fg or ""), str(effective_border or ""))
        if signature_by_hwnd.get(int(hwnd)) == signature:
            return
        dark_flag = ctypes.c_int(1)
        if not _set_dwm_attr(20, dark_flag):
            _set_dwm_attr(19, dark_flag)

        if effective_bg:
            caption_color = owner._hex_to_colorref(effective_bg)
            if caption_color is not None:
                _set_dwm_attr(35, ctypes.c_uint(caption_color))
        if effective_border:
            border_color = owner._hex_to_colorref(effective_border)
            if border_color is not None:
                _set_dwm_attr(34, ctypes.c_uint(border_color))
        if effective_fg:
            text_color = owner._hex_to_colorref(effective_fg)
            if text_color is not None:
                _set_dwm_attr(36, ctypes.c_uint(text_color))
        signature_by_hwnd[int(hwnd)] = signature


def _schedule_footer_theme_refresh(owner: Any):
        root = getattr(owner, "root", None)
        if root is None:
            return
        after_id = getattr(owner, "_theme_footer_refresh_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
            owner._theme_footer_refresh_after_id = None

        def _run():
            owner._theme_footer_refresh_after_id = None
            if owner._credit_badge_host and owner._credit_badge_host.winfo_exists():
                try:
                    owner._render_credit_badges()
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    pass
            if owner._credit_discord_badge_host and owner._credit_discord_badge_host.winfo_exists():
                try:
                    owner._render_credit_discord_badges()
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    pass
            if owner._bug_report_chip and owner._bug_report_chip.winfo_exists():
                try:
                    owner._sync_bug_report_chip_colors()
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    pass
            try:
                owner._apply_footer_layout_variant()
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass

        try:
            owner._theme_footer_refresh_after_id = root.after_idle(_run)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            owner._theme_footer_refresh_after_id = None


def _refresh_runtime_theme_widgets(owner: Any):
        theme = getattr(owner, "_theme", None)
        if not theme:
            return
        try:
            owner.root.configure(bg=theme["bg"])
        except (tk.TclError, RuntimeError, AttributeError, KeyError, TypeError):
            pass

        owner._update_logo_for_theme(force=False)

        if owner._font_stepper_label and owner._font_stepper_label.winfo_exists():
            try:
                owner._font_stepper_label.configure(bg=theme["bg"])
            except (tk.TclError, RuntimeError, AttributeError, KeyError, TypeError):
                pass
        if owner.logo_label and owner.logo_label.winfo_exists():
            try:
                owner.logo_label.configure(bg=theme["bg"])
            except (tk.TclError, RuntimeError, AttributeError, KeyError, TypeError):
                pass
        owner._apply_logo_frame_theme()

        if hasattr(owner, "find_entry") and owner.find_entry:
            try:
                owner.find_entry.configure(
                    bg=theme.get("panel", "#161b24"),
                    fg=theme.get("fg", "#e6e6e6"),
                    insertbackground=theme.get("fg", "#e6e6e6"),
                    selectbackground=theme.get("select_bg", "#2f3a4d"),
                    selectforeground=theme.get("select_fg", "#ffffff"),
                    highlightbackground=theme.get("find_border", "#ffffff"),
                    highlightcolor=theme.get("find_border", "#ffffff"),
                )
            except (tk.TclError, RuntimeError, AttributeError, TypeError):
                pass
        toolbar_center = getattr(owner, "_toolbar_center_frame", None)
        if toolbar_center and toolbar_center.winfo_exists():
            try:
                toolbar_center.configure(bg=theme.get("bg", "#0f131a"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        separator = getattr(owner, "_body_top_separator", None)
        if separator and separator.winfo_exists():
            try:
                border = theme.get("logo_border_outer", "#349fc7")
                separator.configure(
                    bg=theme.get("bg", "#0f131a"),
                    highlightbackground=border,
                    highlightcolor=border,
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        separator_inner = getattr(owner, "_body_top_separator_inner", None)
        if separator_inner and separator_inner.winfo_exists():
            try:
                inner = theme.get("logo_border_inner", "#a9ddf0")
                separator_inner.configure(
                    bg=theme.get("bg", "#0f131a"),
                    highlightbackground=inner,
                    highlightcolor=inner,
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        owner._refresh_input_mode_theme_widgets()
        owner._update_find_entry_layout()

        if owner._credit_bar and owner._credit_bar.winfo_exists():
            try:
                owner._credit_bar.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    highlightbackground=theme.get("credit_border", "#1f2f3f"),
                    highlightcolor=theme.get("credit_border", "#1f2f3f"),
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._credit_content and owner._credit_content.winfo_exists():
            try:
                owner._credit_content.configure(bg=theme.get("credit_bg", "#0b1118"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._credit_label and owner._credit_label.winfo_exists():
            try:
                owner._credit_label.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    fg=theme.get("credit_label_fg", "#b5cade"),
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._credit_badge_host and owner._credit_badge_host.winfo_exists():
            try:
                owner._credit_badge_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._header_variant_bar and owner._header_variant_bar.winfo_exists():
            try:
                owner._header_variant_bar.configure(bg=theme.get("bg", "#0f131a"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._credit_discord_badge_host and owner._credit_discord_badge_host.winfo_exists():
            try:
                owner._credit_discord_badge_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        divider = getattr(owner, "_credit_badges_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = owner._blend_hex_color(border, label, 0.35)
                glow_line = owner._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(owner, "_credit_badges_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        divider = getattr(owner, "_credit_discord_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = owner._blend_hex_color(border, label, 0.35)
                glow_line = owner._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(owner, "_credit_discord_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        divider = getattr(owner, "_credit_theme_divider", None)
        if divider and divider.winfo_exists():
            try:
                divider.configure(bg=theme.get("credit_bg", "#0b1118"))
                border = theme.get("credit_border", "#1f2f3f")
                label = theme.get("credit_label_fg", "#b5cade")
                main_line = owner._blend_hex_color(border, label, 0.35)
                glow_line = owner._blend_hex_color(label, "#ffffff", 0.18)
                line_ids = tuple(getattr(owner, "_credit_theme_divider_lines", ()) or ())
                if len(line_ids) >= 2:
                    divider.itemconfigure(line_ids[0], fill=main_line)
                    divider.itemconfigure(line_ids[1], fill=glow_line)
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        if owner._theme_selector_host and owner._theme_selector_host.winfo_exists():
            try:
                owner._theme_selector_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._bug_report_host and owner._bug_report_host.winfo_exists():
            try:
                owner._bug_report_host.configure(bg=theme.get("credit_bg", "#0b1118"))
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        if owner._bug_report_label and owner._bug_report_label.winfo_exists():
            try:
                owner._bug_report_label.configure(
                    bg=theme.get("credit_bg", "#0b1118"),
                    fg=theme.get("credit_label_fg", "#b5cade"),
                )
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        _schedule_footer_theme_refresh(owner)
        owner._update_editor_mode_controls()
        bug_dialog = getattr(owner, "_bug_report_dialog", None)
        if bug_dialog is not None:
            try:
                if bug_dialog.winfo_exists():
                    owner._apply_windows_titlebar_theme(bug_dialog)
            except (tk.TclError, RuntimeError, AttributeError):
                pass
        bug_header = getattr(owner, "_bug_report_header_frame", None)
        bug_card = getattr(owner, "_bug_report_card_frame", None)
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
                        widget = getattr(owner, attr, None)
                        if widget is not None and widget.winfo_exists():
                            widget.configure(bg=header_bg, fg=header_fg)
                    bug_icon = getattr(owner, "_bug_report_header_icon", None)
                    if bug_icon is not None and bug_icon.winfo_exists():
                        bug_icon_photo = owner._load_bug_report_chip_icon(max_size=18, tint=header_fg)
                        owner._bug_report_header_icon_photo = bug_icon_photo
                        bug_icon.configure(image=bug_icon_photo if bug_icon_photo is not None else "")
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        if bug_card is not None:
            try:
                if bug_card.winfo_exists():
                    border = theme.get("logo_border_outer", "#4b97c2")
                    bug_card.configure(highlightbackground=border, highlightcolor=border)
                    if bug_dialog is not None and bug_dialog.winfo_exists():
                        bug_dialog.configure(bg=theme.get("bg", "#0f131a"))
                    owner._start_bug_report_header_pulse()
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass

        owner._update_app_theme_controls()
        owner._update_header_variant_controls()
        owner._update_tree_style_controls()
        owner._update_toolbar_style_controls()
        owner._style_text_widget()
        owner._refresh_open_readme_window()
        owner._refresh_tree_item_markers()
        owner._refresh_active_error_theme()


def _execute_theme_prewarm_task(owner: Any, task):
        variant = str(task.get("variant", "")).upper()
        kind = str(task.get("kind", "")).lower()
        if variant not in ("SIINDBAD", "KAMUE"):
            return

        original_variant = getattr(owner, "_app_theme_variant", "SIINDBAD")
        original_theme = getattr(owner, "_theme", None)
        prewarm_render_mode = getattr(owner, "_theme_prewarm_render_mode", None)
        try:
            owner._app_theme_variant = variant
            owner._theme = owner._theme_palette_for_variant(variant)
            if kind == "button":
                key = str(task.get("key", ""))
                text = str(task.get("text", key.title()))
                style = owner._siindbad_effective_style()
                display_text = owner._siindbad_toolbar_label_text(style, key, text)
                palette = owner._siindbad_toolbar_style_palette()
                width = owner._siindbad_toolbar_frame_width(style, key, display_text)
                height = owner._siindbad_b_button_height(key, default_height=34)
                owner._siindbad_b_render_button_bundle(
                    key=key,
                    text=display_text,
                    width=max(1, int(width)),
                    height=max(1, int(height)),
                    palette=palette,
                    # Loader-visible prewarm uses fast sprites to avoid startup hitching.
                    render_mode=prewarm_render_mode,
                )
                return
            if kind == "search":
                search_spec = owner._siindbad_b_search_spec() or {}
                search_width = int(search_spec.get("width", 172) or 172)
                search_height = int(search_spec.get("height", 32) or 32)
                find_height = owner._siindbad_b_button_height("find", default_height=33)
                search_height = max(1, min(search_height, int(find_height)))
                owner._siindbad_b_search_sprite_image(search_width, search_height)
                return
            if kind == "font":
                font_spec = owner._siindbad_b_font_sprite_spec()
                if not font_spec:
                    return
                fw = max(1, int(font_spec.get("width", 146) or 146))
                fh = max(1, int(font_spec.get("height", 34) or 34))
                base_path = font_spec.get("path")
                if base_path:
                    owner._load_toolbar_button_image(base_path, max_width=fw, max_height=fh, stretch_to_fit=True)
                hover_path = str(font_spec.get("hover_path", "") or "")
                if hover_path and os.path.isfile(hover_path):
                    owner._load_toolbar_button_image(hover_path, max_width=fw, max_height=fh, stretch_to_fit=True)
                return
            if kind == "font_metrics":
                # Warm font-family/metric lookups once so first context/find/menu paints stay hot.
                for method_name in (
                    "_preferred_mono_family",
                    "_credit_name_font",
                    "_footer_badge_chip_font",
                    "_font_dropdown_number_font",
                    "_readme_font_for_theme",
                ):
                    method = getattr(owner, method_name, None)
                    if not callable(method):
                        continue
                    try:
                        method()
                    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                return
            if kind == "context_menu":
                build_menu = getattr(owner, "_build_text_context_menu", None)
                if callable(build_menu):
                    try:
                        build_menu()
                    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                style_menu = getattr(owner, "_style_text_context_menu", None)
                if callable(style_menu):
                    try:
                        style_menu()
                    except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                popup = getattr(owner, "_text_context_menu", None)
                if popup is None:
                    return
                try:
                    if popup.winfo_exists():
                        popup.update_idletasks()
                        popup.withdraw()
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    pass
                return
            if kind == "find_index":
                build_index = getattr(owner, "_build_find_search_index", None)
                if not callable(build_index):
                    return
                try:
                    index_entries = build_index()
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    return
                if isinstance(index_entries, list):
                    max_items = max(
                        1,
                        int(
                            getattr(
                                owner,
                                "_theme_prewarm_find_index_max_items",
                                PHASE1_FIND_INDEX_MAX_ITEMS,
                            )
                            or PHASE1_FIND_INDEX_MAX_ITEMS
                        ),
                    )
                    bounded_entries = _bounded_sequence(index_entries, max_items=max_items)
                    owner._find_search_entries = bounded_entries
                    owner._theme_prewarm_find_index_count = len(bounded_entries)
                    owner._theme_prewarm_find_index_truncated = len(index_entries) > len(bounded_entries)
                return
            if kind == "logo":
                logo_path = owner._find_logo_path()
                if logo_path:
                    logo_image = owner._load_logo_image(logo_path)
                    if logo_image is not None:
                        logo_cache = getattr(owner, "_theme_logo_photo_by_variant", None)
                        if not isinstance(logo_cache, dict):
                            logo_cache = {}
                            owner._theme_logo_photo_by_variant = logo_cache
                        owner._bounded_cache_put(logo_cache, variant, logo_image, max_items=8)
                return
            if kind == "badges":
                owner._load_credit_badge_sources()
                owner._load_credit_github_icon(max_size=14, tint="#d8e8f2", with_plate=False)
                owner._load_credit_discord_icon(max_size=14, tint="#d8e8f2", with_plate=False)
                return
            if kind == "tree_integrity":
                owner._check_tree_marker_integrity()
                return
            if kind == "tree_markers":
                marker_states = (
                    ("main", False, False, False),
                    ("main", False, True, False),
                    ("main", False, True, True),
                    ("sub", False, False, False),
                    ("sub", True, False, False),
                    ("sub", False, True, False),
                    ("sub", True, True, True),
                )
                for marker_kind, marker_selected, marker_expandable, marker_expanded in marker_states:
                    owner._load_tree_marker_icon(
                        marker_kind,
                        selected=marker_selected,
                        expandable=marker_expandable,
                        expanded=marker_expanded,
                    )
                owner._load_input_bank_red_arrow_icon(expandable=True, expanded=False)
                owner._load_input_bank_red_arrow_icon(expandable=True, expanded=True)
                return
        finally:
            owner._app_theme_variant = original_variant
            owner._theme = original_theme


def _run_phase1_ui_prewarm(owner: Any) -> None:
        if bool(getattr(owner, "_theme_phase1_ui_prewarm_done", False)):
            return
        active_variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
        if active_variant not in ("SIINDBAD", "KAMUE"):
            active_variant = "SIINDBAD"
        # Keep this one-time warmup scoped to first-use UI interactions.
        for kind in ("font_metrics", "context_menu", "find_index"):
            try:
                _execute_theme_prewarm_task(
                    owner,
                    {"variant": active_variant, "kind": kind},
                )
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                pass
        owner._theme_phase1_ui_prewarm_done = True


def _is_loader_overlay_visible(owner: Any) -> bool:
        try:
            overlay = getattr(owner, "_startup_loader_overlay", None)
            return bool(overlay is not None and overlay.winfo_exists())
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return False


def _run_phase2_data_path_prewarm(owner: Any) -> None:
        if bool(getattr(owner, "_theme_phase2_data_prewarm_done", False)):
            return
        sample_payload = {
            "Meta": {"version": 1, "name": "warmup"},
            "Flags": {"isMine": True},
            "Users": [{"id": 1, "name": "user_1"}],
        }
        try:
            pretty_text = document_io_service.build_pretty_json_payload(sample_payload)
            compact_bytes = document_io_service.build_compact_json_bytes(sample_payload)
            # Parse both text and compact bytes to warm first-open JSON decode paths.
            json.loads(str(pretty_text))
            json.loads(bytes(compact_bytes).decode("utf-8"))
        except (ValueError, TypeError, RuntimeError, AttributeError):
            pass
        prewarm_input_assets = getattr(owner, "_prewarm_input_mode_assets", None)
        if callable(prewarm_input_assets):
            try:
                prewarm_input_assets()
            except (ValueError, TypeError, RuntimeError, AttributeError):
                pass
        owner._theme_phase2_data_prewarm_done = True


def _schedule_phase2_data_path_prewarm(owner: Any) -> None:
        if bool(getattr(owner, "_theme_phase2_data_prewarm_done", False)):
            return
        after_id = getattr(owner, "_theme_phase2_data_prewarm_after_id", None)
        if after_id:
            return
        root = getattr(owner, "root", None)
        if root is None:
            _run_phase2_data_path_prewarm(owner)
            return
        delay_ms = max(
            120,
            int(getattr(owner, "_theme_phase2_data_prewarm_delay_ms", PHASE2_DATA_PREWARM_DELAY_MS) or PHASE2_DATA_PREWARM_DELAY_MS),
        )
        retry_ms = max(
            delay_ms,
            int(
                getattr(
                    owner,
                    "_theme_phase2_data_prewarm_retry_delay_ms",
                    PHASE2_DATA_PREWARM_RETRY_DELAY_MS,
                )
                or PHASE2_DATA_PREWARM_RETRY_DELAY_MS
            ),
        )

        def _run_or_defer() -> None:
            owner._theme_phase2_data_prewarm_after_id = None
            if (
                _is_document_load_active_or_cooling(owner)
                or _is_loader_overlay_visible(owner)
                or _is_toolbar_interaction_active(owner)
            ):
                try:
                    owner._theme_phase2_data_prewarm_after_id = root.after(retry_ms, _run_or_defer)
                except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                    owner._theme_phase2_data_prewarm_after_id = None
                return
            _run_phase2_data_path_prewarm(owner)

        try:
            owner._theme_phase2_data_prewarm_after_id = root.after(delay_ms, _run_or_defer)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            owner._theme_phase2_data_prewarm_after_id = None
            _run_phase2_data_path_prewarm(owner)


def _run_theme_asset_prewarm(owner: Any):
        owner._theme_prewarm_after_id = None
        _run_phase1_ui_prewarm(owner)
        _schedule_phase2_data_path_prewarm(owner)
        queue = list(getattr(owner, "_theme_prewarm_queue", []))
        raw_tasks = getattr(owner, "_theme_prewarm_tasks", None)
        if isinstance(raw_tasks, deque):
            tasks = raw_tasks
        elif raw_tasks:
            tasks = deque(raw_tasks)
        else:
            tasks = deque()
        if not queue or not tasks:
            owner._theme_prewarm_queue = []
            owner._theme_prewarm_tasks = deque()
            owner._update_startup_loader_progress()
            owner._on_startup_full_load_ready()
            return
        loader_visible = False
        try:
            overlay = getattr(owner, "_startup_loader_overlay", None)
            loader_visible = bool(overlay is not None and overlay.winfo_exists())
        except (tk.TclError, RuntimeError, AttributeError):
            loader_visible = False
        budget_ms, max_tasks_this_tick, next_tick_ms = startup_loader_core.prewarm_tick_policy(
            loader_visible=loader_visible,
            loader_budget_ms=int(getattr(owner, "_theme_prewarm_loader_budget_ms", 6) or 6),
            idle_budget_ms=int(getattr(owner, "_theme_prewarm_budget_ms", 10) or 10),
            loader_tick_ms=int(getattr(owner, "_theme_prewarm_loader_tick_ms", 16) or 16),
            idle_tick_ms=int(getattr(owner, "_theme_prewarm_idle_tick_ms", 12) or 12),
        )
        # Build full bundles during startup prewarm so first manual theme switch
        # is truly hot and does not trigger first-use sprite/render spikes.
        owner._theme_prewarm_render_mode = "full"
        # Defer startup prewarm while document-load work is active or in short post-load cooldown.
        if _is_document_load_active_or_cooling(owner):
            try:
                owner._theme_prewarm_after_id = owner.root.after(
                    max(80, int(next_tick_ms) * 2),
                    owner._run_theme_asset_prewarm,
                )
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                owner._theme_prewarm_after_id = None
            return
        # Keep initial toolbar hover smooth: defer prewarm ticks while pointer/scan is active.
        if _is_toolbar_interaction_active(owner):
            try:
                owner._theme_prewarm_after_id = owner.root.after(
                    max(80, int(next_tick_ms) * 2),
                    owner._run_theme_asset_prewarm,
                )
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                owner._theme_prewarm_after_id = None
            return
        deadline = time.perf_counter() + (float(budget_ms) / 1000.0)
        done_counts = dict(getattr(owner, "_theme_prewarm_done_by_variant", {}))
        totals = dict(getattr(owner, "_theme_prewarm_total_by_variant", {}))
        processed = 0
        while tasks and time.perf_counter() < deadline and processed < max_tasks_this_tick:
            task = tasks.popleft()
            variant = str(task.get("variant", "")).upper()
            if variant not in ("SIINDBAD", "KAMUE"):
                continue
            processed += 1
            owner._theme_prewarm_active_variant = variant
            try:
                owner._execute_theme_prewarm_task(task)
            except (tk.TclError, RuntimeError, AttributeError, OSError, TypeError, ValueError, ImportError):
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
                owner._finish_theme_prewarm_variant(variant)

        owner._theme_prewarm_done_by_variant = done_counts
        owner._theme_prewarm_queue = queue
        owner._theme_prewarm_tasks = tasks
        owner._theme_prewarm_render_mode = None
        owner._update_startup_loader_progress()
        if owner._theme_prewarm_tasks:
            owner._theme_prewarm_after_id = owner.root.after(next_tick_ms, owner._run_theme_asset_prewarm)
        else:
            owner._on_startup_full_load_ready()
