"""Suspicion INPUT phone-style renderer.

Renders the Suspicion root value on top of theme-specific phone art with a
single centered editable input field anchored to the image.
"""

import importlib
import os
import tkinter as tk


def is_suspicion_input_path(owner, path):
    normalized = list(path or [])
    return len(normalized) == 1 and owner._input_mode_root_key_for_path(normalized) == "suspicion"


def render_suspicion_phone_input(owner, host, normalized_path, value):
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

    wrapper = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=0)
    wrapper.pack(fill="both", expand=True, padx=0, pady=(0, 0))

    center = tk.Frame(wrapper, bg=panel_bg, bd=0, highlightthickness=0)
    center.pack(fill="both", expand=True)

    phone_path = os.path.join(
        owner._resource_base_dir(),
        "assets",
        "phone",
        "kam_phone_sus.png" if variant == "KAMUE" else "sin_phone_sus.png",
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

    phone_photo = _load_phone_photo(owner, phone_path, max_width=308)
    if phone_photo is not None:
        phone_label = tk.Label(phone_host, image=phone_photo, bg=inner_bg, bd=0, highlightthickness=0)
        phone_label.image = phone_photo
        phone_label.pack()
        anchor_parent = phone_label
    else:
        fallback = tk.Label(
            image_holder,
            text="Suspicion phone preview asset not found.",
            bg=panel_bg,
            fg="#cdb6f7" if variant == "KAMUE" else "#9dc2e2",
            font=(name_font, fallback_size, "bold"),
            padx=18,
            pady=28,
        )
        fallback.pack()
        anchor_parent = image_holder

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
    except Exception:
        try:
            raw = tk.PhotoImage(file=path)
            width = raw.width()
            if width > max_width:
                factor = max(1, int(round(width / float(max_width))))
                raw = raw.subsample(factor, factor)
            photo = raw
        except Exception:
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
