from __future__ import annotations

from collections import deque
from typing import Any, Callable
import importlib
import json
import os
import time
import tkinter as tk
from tkinter import ttk

import core.layout_topbar as layout_topbar_core
import core.domain_impl.support.editor_purge_service as editor_purge_service
import core.domain_impl.ui.footer_service as footer_service
import core.domain_impl.ui.theme_asset_service as theme_asset_service
import core.domain_impl.ui.theme_service as theme_service
import core.domain_impl.ui.toolbar_service as toolbar_service
import core.domain_impl.ui.ui_factory_service as ui_factory_service
from core.exceptions import EXPECTED_ERRORS

_EXPECTED_APP_ERRORS = EXPECTED_ERRORS

def _resource_base_dir(self, module_resource_base_dir: Callable[[], str]) -> str:
    return theme_asset_service.resource_base_dir(module_resource_base_dir)

def _siindbad_effective_style(self):
    return editor_purge_service._siindbad_effective_style(self)

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
        if theme_variant == "GLITCH":
            return {
                "button_bg": "#060d0a",
                "button_fg": "#dff5ff",
                "button_active": "#11261c",
                "button_pressed": "#030806",
                "border": find_border,
                "border_active": find_border,
                "slot_bg": "#050b08",
                "size_bg": "#0a1611",
                "inner_border": "#79e89a",
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
    if theme_variant == "GLITCH":
        return {
            "button_bg": "#070f0b",
            "button_fg": "#dff5ff",
            "button_active": "#143022",
            "button_pressed": "#040906",
            "border": border_outer,
            "border_active": border_inner,
            "slot_bg": "#060d0a",
            "size_bg": "#0c1813",
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
            width_value = spec.get("width", 172)
            if isinstance(width_value, int):
                return width_value
            if isinstance(width_value, (float, str)):
                try:
                    return int(width_value)
                except _EXPECTED_APP_ERRORS:
                    return 172
            return 172
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
            width_value = spec.get("width", 172)
            if isinstance(width_value, int):
                search_spec_width = width_value
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
    self._theme_prewarm_total_by_variant = {"SIINDBAD": 0, "KAMUE": 0, "GLITCH": 0}
    self._theme_prewarm_done_by_variant = {"SIINDBAD": 0, "KAMUE": 0, "GLITCH": 0}

def _siindbad_b_render_mode(self, override=None):
    if override in ("fast", "full"):
        return override
    variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
    if variant == "GLITCH":
        # GLITCH uses full hover-frame rendering for smooth scan parity
        # with warmed SIINDBAD/KAMUE/GLITCH Variant-B buttons.
        return "full"
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
    spec: dict[str, object] = {"width": width, "height": height}
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
        if str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper() in ("KAMUE", "GLITCH"):
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
    return ui_factory_service.build_font_control(
        self,
        self._font_control_host,
        tk_module=tk,
        ttk_module=ttk,
        expected_errors=_EXPECTED_APP_ERRORS,
    )

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
    if variant in ("SIINDBAD", "GLITCH") or (variant == "KAMUE" and self._siindbad_effective_style() == "B"):
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
    return ui_factory_service.build_bug_report_chip(
        self,
        parent,
        tk_module=tk,
        expected_errors=_EXPECTED_APP_ERRORS,
    )

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

def load_toolbar_assets(owner: Any) -> None:
    _load_toolbar_button_images(owner)


def refresh_theme_sprites(owner: Any) -> None:
    _refresh_toolbar_button_images(owner)

_DISPATCH: dict[str, Callable[..., Any]] = {
    "_align_topbar_to_logo": _align_topbar_to_logo,
    "_apply_asset_toolbar_button_style": _apply_asset_toolbar_button_style,
    "_apply_max_toolbar_search_compaction": _apply_max_toolbar_search_compaction,
    "_apply_siindbad_toolbar_button_style": _apply_siindbad_toolbar_button_style,
    "_apply_toolbar_layout_max": _apply_toolbar_layout_max,
    "_apply_toolbar_layout_mode": _apply_toolbar_layout_mode,
    "_apply_toolbar_layout_normal": _apply_toolbar_layout_normal,
    "_apply_toolbar_spacing_for_mode": _apply_toolbar_spacing_for_mode,
    "_bounded_cache_put": _bounded_cache_put,
    "_bug_chip_palette": _bug_chip_palette,
    "_build_bug_report_chip": _build_bug_report_chip,
    "_cancel_toolbar_refresh_after": _cancel_toolbar_refresh_after,
    "_collect_toolbar_tokens_from_dir": _collect_toolbar_tokens_from_dir,
    "_draw_siindbad_toolbar_icon": _draw_siindbad_toolbar_icon,
    "_ensure_siindbad_button_icons": _ensure_siindbad_button_icons,
    "_find_entry_base_width": _find_entry_base_width,
    "_find_entry_target_width": _find_entry_target_width,
    "_font_stepper_action": _font_stepper_action,
    "_footer_badge_palette": _footer_badge_palette,
    "_footer_style_variant": _footer_style_variant,
    "_footer_visual_spec": _footer_visual_spec,
    "_init_tree_runtime_state": _init_tree_runtime_state,
    "_invalidate_siindbad_b_sprite_cache": _invalidate_siindbad_b_sprite_cache,
    "_invoke_siindbad_b_button": _invoke_siindbad_b_button,
    "_load_siindbad_b_font_sprite_image": _load_siindbad_b_font_sprite_image,
    "_load_siindbad_toolbar_button_images": _load_siindbad_toolbar_button_images,
    "_load_toolbar_button_images": _load_toolbar_button_images,
    "_load_toolbar_button_images_from_assets": _load_toolbar_button_images_from_assets,
    "_make_font_stepper": _make_font_stepper,
    "_make_siindbad_font_stepper": _make_siindbad_font_stepper,
    "_make_siindbad_stepper_button": _make_siindbad_stepper_button,
    "_make_toolbar_button": _make_toolbar_button,
    "_on_font_stepper_click": _on_font_stepper_click,
    "_on_font_stepper_motion": _on_font_stepper_motion,
    "_point_in_hitbox": _point_in_hitbox,
    "_pointer_within_widget": _pointer_within_widget,
    "_refresh_toolbar_button_images": _refresh_toolbar_button_images,
    "_render_font_control": _render_font_control,
    "_resource_base_dir": _resource_base_dir,
    "_run_toolbar_refresh_after": _run_toolbar_refresh_after,
    "_scale_hitbox": _scale_hitbox,
    "_schedule_toolbar_refresh_after": _schedule_toolbar_refresh_after,
    "_schedule_topbar_alignment": _schedule_topbar_alignment,
    "_set_font_stepper_geometry_from_asset": _set_font_stepper_geometry_from_asset,
    "_siindbad_b_asset_button_path": _siindbad_b_asset_button_path,
    "_siindbad_b_button_height": _siindbad_b_button_height,
    "_siindbad_b_button_hover_enter": _siindbad_b_button_hover_enter,
    "_siindbad_b_button_hover_leave": _siindbad_b_button_hover_leave,
    "_siindbad_b_font_sprite_spec": _siindbad_b_font_sprite_spec,
    "_siindbad_b_render_button_bundle": _siindbad_b_render_button_bundle,
    "_siindbad_b_render_mode": _siindbad_b_render_mode,
    "_siindbad_b_search_spec": _siindbad_b_search_spec,
    "_siindbad_b_search_sprite_image": _siindbad_b_search_sprite_image,
    "_siindbad_b_sprite_bundle": _siindbad_b_sprite_bundle,
    "_siindbad_b_sprite_dir": _siindbad_b_sprite_dir,
    "_siindbad_b_sprite_manifest": _siindbad_b_sprite_manifest,
    "_siindbad_effective_style": _siindbad_effective_style,
    "_siindbad_toolbar_button_width": _siindbad_toolbar_button_width,
    "_siindbad_toolbar_frame_width": _siindbad_toolbar_frame_width,
    "_siindbad_toolbar_label_text": _siindbad_toolbar_label_text,
    "_siindbad_toolbar_style_palette": _siindbad_toolbar_style_palette,
    "_start_siindbad_b_button_scan": _start_siindbad_b_button_scan,
    "_stop_all_siindbad_b_button_scans": _stop_all_siindbad_b_button_scans,
    "_stop_siindbad_b_button_scan": _stop_siindbad_b_button_scan,
    "_style_combobox_popdown": _style_combobox_popdown,
    "_sync_bug_report_chip_colors": _sync_bug_report_chip_colors,
    "_theme_chip_palette": _theme_chip_palette,
    "_tick_siindbad_b_button_scan": _tick_siindbad_b_button_scan,
    "_tree_variant_chip_palette": _tree_variant_chip_palette,
    "_update_find_entry_layout": _update_find_entry_layout,
    "_window_is_maximized": _window_is_maximized,
    "load_toolbar_assets": load_toolbar_assets,
    "refresh_theme_sprites": refresh_theme_sprites,
}

class VisualAssetFacade:
    def __getattr__(self, name: str) -> Callable[..., Any]:
        fn = _DISPATCH.get(str(name))
        if fn is None:
            raise AttributeError(name)
        return fn


VISUALS = VisualAssetFacade()

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
                image=(self.logo_image if self.logo_image is not None else ""),
                bg=bg,
                bd=0,
                highlightthickness=0,
            )
            self.logo_label.pack(anchor="center", pady=0)
    else:
        try:
            if self.logo_label is not None:
                self.logo_label.configure(image=(self.logo_image if self.logo_image is not None else ""))
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
    logo_candidates_by_theme = {
        "GLITCH": (
            "assets/glitch.png",
            "glitch.png",
            "assets/logo2.png",
            "logo2.png",
        ),
        "KAMUE": (
            "assets/klogo.fw.png",
            "assets/klogo.png",
            "klogo.fw.png",
            "klogo.png",
            "assets/logo2.png",
            "logo2.png",
        ),
        "SIINDBAD": (
            "assets/logo2.png",
            "logo2.png",
            "assets/klogo.fw.png",
            "assets/klogo.png",
        ),
    }
    candidates = logo_candidates_by_theme.get(variant, logo_candidates_by_theme["SIINDBAD"])
    for rel_path in candidates:
        path = os.path.join(base_dir, rel_path)
        if os.path.isfile(path):
            return path
    return None


def _refresh_input_mode_theme_widgets(self):
    theme = getattr(self, "_theme", {}) or {}
    panel_bg = theme.get("panel", "#161b24")
    variant = str(getattr(self, "_app_theme_variant", "SIINDBAD")).upper()
    notice_fg_by_theme = {
        "KAMUE": "#cdb6f7",
        "GLITCH": "#b6ebc4",
        "SIINDBAD": "#9dc2e2",
    }
    notice_fg = notice_fg_by_theme.get(variant, notice_fg_by_theme["SIINDBAD"])
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


_DISPATCH.update(
    {
        "_find_logo_path": _find_logo_path,
        "_refresh_input_mode_theme_widgets": _refresh_input_mode_theme_widgets,
        "_update_logo_for_theme": _update_logo_for_theme,
    }
)
