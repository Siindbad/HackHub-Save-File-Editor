"""Suspicion INPUT phone-style renderer.

Renders the Suspicion root value on top of theme-specific phone art with a
single centered editable input field anchored to the image.
"""

import importlib
import os
import tkinter as tk
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def is_suspicion_input_path(owner: Any, path: Any) -> Any:
    normalized = list(path or [])
    return len(normalized) == 1 and owner._input_mode_root_key_for_path(normalized) == "suspicion"


def is_phone_input_path(owner: Any, path: Any) -> Any:
    normalized = list(path or [])
    return len(normalized) == 1 and owner._input_mode_root_key_for_path(normalized) == "phone"


def is_skypersky_input_path(owner: Any, path: Any) -> Any:
    normalized = list(path or [])
    return len(normalized) == 1 and owner._input_mode_root_key_for_path(normalized) == "skypersky"


def render_suspicion_phone_input(owner: Any, host: Any, normalized_path: Any, value: Any) -> Any:
    # Suspicion payload is expected to be a scalar root value.
    if not isinstance(value, (str, int, float, bool)) and value is not None:
        return False

    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    inner_bg = "#060c14" if variant == "KAMUE" else "#040a12"
    frame_edge = "#5f3d86" if variant == "KAMUE" else "#295478"
    input_edge = "#8a5bc4" if variant == "KAMUE" else "#2e8fd4"
    input_bg = "#1b1230" if variant == "KAMUE" else "#071322"
    input_fg = "#8bf2aa" if variant == "KAMUE" else "#62d67a"
    name_font = owner._credit_name_font()[0]
    fallback_size = owner._input_mode_font_size(10, min_size=8, max_size=18)
    input_size = owner._input_mode_font_size(10, min_size=8, max_size=18)

    phone_art_name = "kam_phone_sus.png" if variant == "KAMUE" else "sin_phone_sus.png"
    anchor_parent = _render_phone_preview_shell(
        owner,
        host,
        panel_bg=panel_bg,
        inner_bg=inner_bg,
        frame_edge=frame_edge,
        fallback_fg="#cdb6f7" if variant == "KAMUE" else "#9dc2e2",
        fallback_font=(name_font, fallback_size, "bold"),
        phone_art_name=phone_art_name,
        fallback_text="Suspicion phone preview asset not found.",
    )
    if anchor_parent is None:
        return False

    # Match preview placement: input attached to the phone art below title region.
    overlay = tk.Frame(anchor_parent, bg="", bd=0, highlightthickness=0)
    overlay.place(relx=0.5, rely=0.61, anchor="center")

    text_value = "true" if value is True else "false" if value is False else ("" if value is None else str(value))
    var = tk.StringVar(value=text_value)
    entry = tk.Entry(
        overlay,
        textvariable=var,
        width=6,
        justify="center",
        bg=input_bg,
        fg=input_fg,
        insertbackground=input_fg,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=input_edge,
        highlightcolor=input_edge,
        font=(name_font, input_size, "bold"),
    )
    entry.pack(ipady=1)
    _bind_percent_revert_guard(entry, var, initial_value=value)

    owner._input_mode_field_specs.append(
        {
            "rel_path": [],
            "abs_path": list(normalized_path),
            "initial": value,
            "type": type(value),
            "var": var,
            "widget": entry,
        }
    )
    return True


def render_phone_preview_input(owner: Any, host: Any, normalized_path: Any, value: Any) -> Any:
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    inner_bg = "#060c14" if variant == "KAMUE" else "#040a12"
    frame_edge = "#5f3d86" if variant == "KAMUE" else "#295478"
    name_font = owner._credit_name_font()[0]
    fallback_size = owner._input_mode_font_size(10, min_size=8, max_size=18)
    fallback_fg = "#cdb6f7" if variant == "KAMUE" else "#9dc2e2"

    anchor_parent = _render_phone_preview_shell(
        owner,
        host,
        panel_bg=panel_bg,
        inner_bg=inner_bg,
        frame_edge=frame_edge,
        fallback_fg=fallback_fg,
        fallback_font=(name_font, fallback_size, "bold"),
        phone_art_name="sin_phone.png",
        fallback_text="Phone preview asset not found.",
    )
    if anchor_parent is None:
        return False

    payload = _phone_preview_payload_from_value(value)
    _render_phone_concept_two_overlay(
        owner,
        anchor_parent,
        payload=payload,
        normalized_path=list(normalized_path or []),
        variant=variant,
    )
    return True


def render_skypersky_input(owner: Any, host: Any, normalized_path: Any, value: Any) -> Any:
    payload = _skypersky_payload_from_value(value)
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    stage_bg = "#05070d" if variant == "KAMUE" else "#060b14"
    frame_edge = "#5f3d86" if variant == "KAMUE" else "#295478"
    card_edge = "#6b37b6" if variant == "KAMUE" else "#4e6e86"
    card_fill = "#13102a" if variant == "KAMUE" else "#101a2a"
    label_fg = "#eee8ff" if variant == "KAMUE" else "#e6f6ff"
    family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    label_size = owner._input_mode_font_size(12, min_size=9, max_size=20)
    state_size = owner._input_mode_font_size(9, min_size=8, max_size=16)
    seg_edge = "#6b37b6" if variant == "KAMUE" else "#4e6e86"
    seg_fill = "#120f24" if variant == "KAMUE" else "#0b1524"
    seg_active_fill = "#2d155f" if variant == "KAMUE" else "#2f3a4d"
    seg_active_fg = "#ffffff"
    seg_inactive_fg = "#b0bfcc" if variant == "KAMUE" else "#c5d5e2"

    image_name = "skypersky_kam.png" if variant == "KAMUE" else "skypersky.png"
    stage = _render_skypersky_preview_shell(
        owner,
        host,
        panel_bg=panel_bg,
        stage_bg=stage_bg,
        image_name=image_name,
    )
    if stage is None:
        return False

    # Keep this frame aligned to the PNG inner dialog bounds from the approved concept.
    overlay_bounds = tk.Frame(
        stage,
        bg=stage_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=frame_edge,
        highlightcolor=frame_edge,
    )
    overlay_bounds.place(relx=0.5, rely=0.526, anchor="center", relwidth=0.892, relheight=0.748)

    card = tk.Frame(
        overlay_bounds,
        bg=card_fill,
        bd=0,
        highlightthickness=1,
        highlightbackground=card_edge,
        highlightcolor=card_edge,
    )
    card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.964, relheight=0.932)
    inner = tk.Frame(card, bg=card_fill, bd=0, highlightthickness=0)
    inner.pack(fill="both", expand=True, padx=10, pady=8)
    content = tk.Frame(inner, bg=card_fill, bd=0, highlightthickness=0)
    content.place(relx=0.5, rely=0.5, anchor="center")

    label = tk.Label(
        content,
        text="PROTECTION",
        bg=card_fill,
        fg=label_fg,
        font=(family, label_size, "bold"),
        anchor="center",
        justify="center",
    )
    label.pack(anchor="center", pady=(2, 6))

    protecting_var = tk.StringVar(value="true" if payload.get("protecting") is True else "false")
    toggle = _build_segmented_toggle(
        content,
        value_var=protecting_var,
        edge=seg_edge,
        fill=seg_fill,
        active_fill=seg_active_fill,
        active_fg=seg_active_fg,
        inactive_fg=seg_inactive_fg,
        family=family,
        size=state_size,
        width=150,
        height=30,
        off_text="Off",
        on_text="On",
    )
    toggle.pack(anchor="center", pady=(0, 2))

    owner._input_mode_field_specs.append(
        {
            "rel_path": ["protecting"],
            "abs_path": list(normalized_path) + ["protecting"],
            "initial": bool(payload.get("protecting") is True),
            "type": bool,
            "var": protecting_var,
            "widget": toggle,
        }
    )
    return True


def _skypersky_payload_from_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        protecting_raw = value.get("protecting", False)
    else:
        protecting_raw = value
    return {"protecting": bool(protecting_raw is True)}


def _phone_preview_payload_from_value(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"cellular": False, "hotspot": False, "password": ""}
    hotspot_node = value.get("hotspot")
    hotspot = hotspot_node if isinstance(hotspot_node, dict) else {}
    password = str(hotspot.get("password", "") or "")
    return {
        "cellular": bool(value.get("cellular") is True),
        "hotspot": bool(hotspot.get("activity") is True),
        "password": password,
    }


def _render_phone_concept_two_overlay(
    owner: Any,
    anchor_parent: Any,
    *,
    payload: dict[str, Any],
    normalized_path: list[Any],
    variant: str,
) -> None:
    # PHONE Concept-2 palette: bias toward dark black/green to match sin_phone art.
    screen_edge = "#21483a" if variant == "KAMUE" else "#1b4336"
    screen_fill = "#08090b" if variant == "KAMUE" else "#07080a"
    card_edge = "#285441" if variant == "KAMUE" else "#214b3d"
    card_fill = "#101217" if variant == "KAMUE" else "#0e1014"
    label_fg = "#b8c4cf"
    value_fg = "#72f2a6"
    seg_edge = "#2c5b48" if variant == "KAMUE" else "#255141"
    seg_fill = "#171a20" if variant == "KAMUE" else "#14171c"
    seg_active_fill = "#1f4e39" if variant == "KAMUE" else "#1b4332"
    seg_active_fg = "#9dffc8"
    seg_inactive_fg = "#82a894"
    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    value_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    label_size = owner._input_mode_font_size(10, min_size=7, max_size=16)
    value_size = owner._input_mode_font_size(10, min_size=8, max_size=18)
    state_size = owner._input_mode_font_size(8, min_size=7, max_size=16)

    screen = tk.Canvas(anchor_parent, bg=anchor_parent.cget("bg"), bd=0, highlightthickness=0)
    screen.place(relx=0.5, rely=0.23, anchor="n", relwidth=0.648, relheight=0.50)
    content = tk.Frame(screen, bg=screen_fill, bd=0, highlightthickness=0)
    window_id = screen.create_window(8, 8, window=content, anchor="nw")

    def _redraw_screen(event: Any = None) -> None:
        _ = event
        try:
            w = max(120, int(screen.winfo_width()))
            h = max(120, int(screen.winfo_height()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return
        screen.delete("bg")
        _draw_rounded(screen, 0, 0, w - 1, h - 1, radius=14, color=screen_edge, tag="bg")
        _draw_rounded(screen, 1, 1, w - 2, h - 2, radius=13, color=screen_fill, tag="bg")
        screen.coords(window_id, 8, 8)
        screen.itemconfigure(window_id, width=max(40, w - 16), height=max(40, h - 16))

    screen.bind("<Configure>", _redraw_screen, add="+")

    cellular_var = tk.StringVar(value="true" if bool(payload.get("cellular") is True) else "false")
    hotspot_var = tk.StringVar(value="true" if bool(payload.get("hotspot") is True) else "false")

    _build_phone_info_card(
        content,
        label_text="Cellular",
        value_widget=lambda parent: _build_segmented_toggle(
            parent,
            value_var=cellular_var,
            edge=seg_edge,
            fill=seg_fill,
            active_fill=seg_active_fill,
            active_fg=seg_active_fg,
            inactive_fg=seg_inactive_fg,
            family=label_family,
            size=state_size,
        ),
        edge=card_edge,
        fill=card_fill,
        label_fg=label_fg,
        label_family=label_family,
        label_size=label_size,
    ).pack(fill="x", pady=(0, 6))

    _build_phone_info_card(
        content,
        label_text="Hotspot",
        value_widget=lambda parent: _build_segmented_toggle(
            parent,
            value_var=hotspot_var,
            edge=seg_edge,
            fill=seg_fill,
            active_fill=seg_active_fill,
            active_fg=seg_active_fg,
            inactive_fg=seg_inactive_fg,
            family=label_family,
            size=state_size,
        ),
        edge=card_edge,
        fill=card_fill,
        label_fg=label_fg,
        label_family=label_family,
        label_size=label_size,
    ).pack(fill="x", pady=(0, 6))

    password_text = str(payload.get("password", "") or "")
    _build_phone_info_card(
        content,
        label_text="Password",
        value_widget=lambda parent: tk.Label(
            parent,
            text=password_text,
            bg=card_fill,
            fg=value_fg,
            font=(value_family, value_size, "bold"),
            anchor="w",
            justify="left",
        ),
        edge=card_edge,
        fill=card_fill,
        label_fg=label_fg,
        label_family=label_family,
        label_size=label_size,
    ).pack(fill="x")

    owner._input_mode_field_specs.append(
        {
            "rel_path": ["cellular"],
            "abs_path": list(normalized_path) + ["cellular"],
            "initial": bool(payload.get("cellular") is True),
            "type": bool,
            "var": cellular_var,
            "widget": content,
        }
    )
    owner._input_mode_field_specs.append(
        {
            "rel_path": ["hotspot", "activity"],
            "abs_path": list(normalized_path) + ["hotspot", "activity"],
            "initial": bool(payload.get("hotspot") is True),
            "type": bool,
            "var": hotspot_var,
            "widget": content,
        }
    )

    _redraw_screen()


def _build_phone_info_card(
    parent: Any,
    *,
    label_text: str,
    value_widget: Any,
    edge: str,
    fill: str,
    label_fg: str,
    label_family: str,
    label_size: int,
) -> Any:
    card = tk.Canvas(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, relief="flat", height=70)
    inner = tk.Frame(card, bg=fill, bd=0, highlightthickness=0)
    window_id = card.create_window(8, 7, window=inner, anchor="nw")

    label = tk.Label(
        inner,
        text=str(label_text),
        bg=fill,
        fg=label_fg,
        font=(label_family, label_size, "bold"),
        anchor="w",
        justify="left",
    )
    label.pack(anchor="w")
    widget = value_widget(inner)
    widget.pack(anchor="w", pady=(4, 0))

    def _redraw_card(event: Any = None) -> None:
        _ = event
        try:
            inner.update_idletasks()
            needed_h = max(52, int(inner.winfo_reqheight()) + 14)
            if int(card.cget("height")) < needed_h:
                card.configure(height=needed_h)
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            w = max(80, int(card.winfo_width()))
            h = max(52, int(card.winfo_height()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return
        card.delete("bg")
        _draw_rounded(card, 0, 0, w - 1, h - 1, radius=8, color=edge, tag="bg")
        _draw_rounded(card, 1, 1, w - 2, h - 2, radius=7, color=fill, tag="bg")
        card.coords(window_id, 8, 7)
        card.itemconfigure(window_id, width=max(40, w - 16), height=max(40, h - 14))

    card.bind("<Configure>", _redraw_card, add="+")
    _redraw_card()
    return card


def _build_segmented_toggle(
    parent: Any,
    *,
    value_var: Any,
    edge: str,
    fill: str,
    active_fill: str,
    active_fg: str,
    inactive_fg: str,
    family: str,
    size: int,
    width: int = 126,
    height: int = 28,
    off_text: str = "Off",
    on_text: str = "On",
) -> Any:
    shell = tk.Canvas(
        parent,
        width=max(90, int(width)),
        height=max(24, int(height)),
        bg=parent.cget("bg"),
        highlightthickness=0,
        bd=0,
        relief="flat",
    )
    setattr(shell, "_phone_toggle_var", value_var)

    def _is_on() -> bool:
        raw = str(value_var.get()).strip().casefold()
        return raw in {"true", "1", "yes", "on"}

    def _redraw_toggle(event: Any = None) -> None:
        _ = event
        try:
            w = max(90, int(shell.winfo_width()))
            h = max(24, int(shell.winfo_height()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            return
        left_active = not _is_on()
        right_active = _is_on()
        shell.delete("all")
        _draw_rounded(shell, 0, 0, w - 1, h - 1, radius=8, color=edge)
        _draw_rounded(shell, 1, 1, w - 2, h - 2, radius=7, color=fill)
        mid = w // 2
        shell.create_line(mid, 3, mid, h - 4, fill=edge, width=1)
        if left_active:
            _draw_rounded(shell, 2, 2, mid - 1, h - 3, radius=6, color=active_fill)
        if right_active:
            _draw_rounded(shell, mid + 1, 2, w - 3, h - 3, radius=6, color=active_fill)
        shell.create_text(
            mid // 2,
            h // 2,
            text=str(off_text),
            fill=active_fg if left_active else inactive_fg,
            font=(family, size, "bold"),
        )
        shell.create_text(
            (mid + w) // 2,
            h // 2,
            text=str(on_text),
            fill=active_fg if right_active else inactive_fg,
            font=(family, size, "bold"),
        )

    def _on_click(event: Any) -> None:
        try:
            w = max(90, int(shell.winfo_width()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            w = max(90, int(width))
        value_var.set("false" if int(getattr(event, "x", 0)) < (w // 2) else "true")
        _redraw_toggle()

    shell.bind("<Configure>", _redraw_toggle, add="+")
    shell.bind("<Button-1>", _on_click, add="+")
    _redraw_toggle()
    return shell


def _draw_rounded(
    canvas: Any,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    radius: int,
    color: str,
    tag: str | None = None,
) -> None:
    r = max(1, int(radius))
    if (x2 - x1) < (r * 2):
        r = max(1, int((x2 - x1) / 2))
    if (y2 - y1) < (r * 2):
        r = max(1, int((y2 - y1) / 2))
    points = [
        x1 + r,
        y1,
        x2 - r,
        y1,
        x2,
        y1,
        x2,
        y1 + r,
        x2,
        y2 - r,
        x2,
        y2,
        x2 - r,
        y2,
        x1 + r,
        y2,
        x1,
        y2,
        x1,
        y2 - r,
        x1,
        y1 + r,
        x1,
        y1,
    ]
    kwargs = {
        "smooth": True,
        "splinesteps": 36,
        "fill": color,
        "outline": color,
        "width": 1,
    }
    if tag is not None:
        kwargs["tags"] = (tag,)
    canvas.create_polygon(points, **kwargs)


def _render_phone_preview_shell(
    owner: Any,
    host: Any,
    *,
    panel_bg: Any,
    inner_bg: Any,
    frame_edge: Any,
    fallback_fg: Any,
    fallback_font: Any,
    phone_art_name: Any,
    fallback_text: Any,
) -> Any:
    wrapper = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=0)
    wrapper.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    center = tk.Frame(wrapper, bg=panel_bg, bd=0, highlightthickness=0)
    center.pack(fill="both", expand=True)

    phone_path = os.path.join(
        owner._resource_base_dir(),
        "assets",
        "phone",
        str(phone_art_name),
    )
    image_holder = tk.Frame(
        center,
        bg=inner_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=frame_edge,
    )
    image_holder.pack(fill="both", expand=True, side="top", pady=(0, 0))

    phone_host = tk.Frame(image_holder, bg=inner_bg, bd=0, highlightthickness=0)
    phone_host.pack(expand=True)
    phone_stage = tk.Frame(phone_host, bg=inner_bg, bd=0, highlightthickness=0)
    phone_stage.pack()

    phone_photo = _load_phone_photo(owner, phone_path, max_width=308)
    if phone_photo is not None:
        phone_label = tk.Label(phone_stage, image=phone_photo, bg=inner_bg, bd=0, highlightthickness=0)
        setattr(phone_label, "image", phone_photo)
        phone_label.pack()
        return phone_stage

    # Fallback notice templates are retired; keep a clean stage when art is missing.
    return phone_stage


def _render_skypersky_preview_shell(
    owner: Any,
    host: Any,
    *,
    panel_bg: Any,
    stage_bg: Any,
    image_name: Any,
) -> Any:
    # Keep full Skypersky stage consistently dark so no lighter panel strip shows below the art.
    host.configure(bg=stage_bg)
    parent_canvas = getattr(host, "master", None)
    if isinstance(parent_canvas, tk.Canvas):
        parent_canvas.configure(bg=stage_bg)
    wrapper = tk.Frame(host, bg=stage_bg, bd=0, highlightthickness=0)
    wrapper.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    center = tk.Frame(wrapper, bg=stage_bg, bd=0, highlightthickness=0)
    center.pack(fill="both", expand=True)

    image_holder = tk.Frame(center, bg=stage_bg, bd=0, highlightthickness=0)
    image_holder.pack(fill="both", expand=True)

    stage_host = tk.Frame(image_holder, bg=stage_bg, bd=0, highlightthickness=0)
    stage_host.pack(fill="both", expand=True)
    stage = tk.Frame(stage_host, bg=stage_bg, bd=0, highlightthickness=0)
    stage.pack(expand=True)

    image_path = os.path.join(
        owner._resource_base_dir(),
        "assets",
        "skype",
        str(image_name),
    )
    preview_photo = _load_phone_photo(owner, image_path, max_width=540)
    if preview_photo is not None:
        preview_label = tk.Label(stage, image=preview_photo, bg=stage_bg, bd=0, highlightthickness=0)
        setattr(preview_label, "image", preview_photo)
        preview_label.pack()
    return stage


def _load_phone_photo(owner, path, max_width=440):
    cache = getattr(owner, "_input_suspicion_phone_photo_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_suspicion_phone_photo_cache = cache
    key = (path, int(max_width))
    if key in cache:
        return cache[key]
    if not os.path.isfile(path):
        cache[key] = None
        return None

    photo = None
    try:
        image_module = importlib.import_module("PIL.Image")
        image_tk_module = importlib.import_module("PIL.ImageTk")
        image = image_module.open(path).convert("RGBA")
        width, height = image.size
        if width > max_width:
            ratio = max_width / float(width)
            image = image.resize((max_width, max(1, int(height * ratio))), image_module.LANCZOS)
        photo = image_tk_module.PhotoImage(image)
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        try:
            raw = tk.PhotoImage(file=path)
            width = raw.width()
            if width > max_width:
                factor = max(1, int(round(width / float(max_width))))
                raw = raw.subsample(factor)
            photo = raw
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            photo = None
    cache[key] = photo
    return photo


def _bind_percent_revert_guard(entry, var, initial_value):
    # Enforce 0..100 without popups; invalid edits revert to last accepted value.
    initial_text = str(initial_value) if isinstance(initial_value, int) and 0 <= initial_value <= 100 else "0"
    state = {"last_valid": initial_text}
    if str(var.get()).strip() == "":
        var.set(initial_text)

    def _normalize_or_revert(allow_blank=False):
        raw = str(var.get()).strip()
        if raw == "":
            if allow_blank:
                return
            var.set(state["last_valid"])
            return
        if raw.isdigit():
            value = int(raw)
            if 0 <= value <= 100:
                state["last_valid"] = str(value)
                if raw != state["last_valid"]:
                    var.set(state["last_valid"])
                return
        var.set(state["last_valid"])

    entry.bind("<KeyRelease>", lambda _e: _normalize_or_revert(allow_blank=True), add="+")
    entry.bind("<FocusOut>", lambda _e: _normalize_or_revert(allow_blank=False), add="+")
