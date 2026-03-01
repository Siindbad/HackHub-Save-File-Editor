"""Timer and pulse orchestration helpers extracted from JsonEditor."""

from __future__ import annotations

import time
import tkinter as tk

from core.exceptions import EXPECTED_ERRORS
from core.domain_impl.support import telemetry_core as crash_offer_service
from core.domain_impl.ui import text_context_action_service
from core.domain_impl.infra import update_engine_core

update_ui_service = update_engine_core
_EXPECTED_APP_ERRORS = EXPECTED_ERRORS


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
        "_document_load_async_after_id",
    ):
        after_id = getattr(self, attr, None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except _EXPECTED_APP_ERRORS:
                setattr(self, attr, None)
        setattr(self, attr, None)
    self._topbar_align_pending_delay_ms = None

def _update_update_overlay(self, message=None, stage=None, percent=None, pulse=False):
    update_ui_service.update_update_overlay(
        self,
        message=message,
        stage=stage,
        percent=percent,
        pulse=pulse,
    )

def _set_status(self, text):
    if self.status is None:
        return
    try:
        self.root.after(0, lambda: self.status.config(text=text))
    except (RuntimeError, tk.TclError, AttributeError):
        return

def _schedule_crash_report_offer(self, delay_ms=450):
    self._crash_report_offer_after_id = crash_offer_service.schedule_crash_report_offer(
        root=getattr(self, "root", None),
        existing_after_id=getattr(self, "_crash_report_offer_after_id", None),
        delay_ms=delay_ms,
        callback=self._offer_crash_report_if_available,
        expected_errors=_EXPECTED_APP_ERRORS,
    )

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
    text_context_action_service.tick_text_context_menu_pulse(
        self,
        expected_errors=_EXPECTED_APP_ERRORS,
    )

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
