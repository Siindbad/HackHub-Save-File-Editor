"""Network DEVICE GEO IP INPUT style helpers.

Implements Concept-1 style GEO IP rendering for the first DEVICE row under
Network in INPUT mode. Layout is read-only and uses router/device identity
blocks with smooth rounded cards.
"""

from __future__ import annotations

import importlib
import os
import tkinter as tk
from typing import Any

from core.exceptions import EXPECTED_ERRORS


def is_network_geoip_payload(owner: Any, path: Any, value: Any) -> bool:
    """Return True only for the first DEVICE row under Network."""
    if not isinstance(path, list) or len(path) != 2:
        return False
    if owner._input_mode_root_key_for_path(path) != "network":
        return False
    if not isinstance(path[1], int):
        return False
    if not (isinstance(value, dict) and str(value.get("type", "")).upper() == "DEVICE"):
        return False
    full_network = owner._get_value([path[0]])
    if not isinstance(full_network, list):
        return False
    first_device_index: int | None = None
    for idx, item in enumerate(full_network):
        if isinstance(item, dict) and str(item.get("type", "")).upper() == "DEVICE":
            first_device_index = idx
            break
    return first_device_index is not None and int(path[1]) == int(first_device_index)


def collect_geoip_payload(owner: Any, normalized_path: Any, device: Any) -> dict[str, Any] | None:
    """Collect router/device/user/location fields for Concept-1 GEO IP display."""
    if not is_network_geoip_payload(owner, normalized_path, device):
        return None
    if not isinstance(normalized_path, list) or not normalized_path:
        return None
    if not isinstance(device, dict):
        return None

    full_network = owner._get_value([normalized_path[0]])
    if not isinstance(full_network, list):
        return None

    parent_router_ip = str(device.get("parent", "") or "").strip()
    router = None
    for item in full_network:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).upper() != "ROUTER":
            continue
        if str(item.get("ip", "") or "").strip() == parent_router_ip:
            router = item
            break

    location_raw = device.get("location")
    location: dict[str, Any] = location_raw if isinstance(location_raw, dict) else {}
    users_raw = device.get("users")
    users: list[Any] = users_raw if isinstance(users_raw, list) else []
    first_user_raw = users[0] if users and isinstance(users[0], dict) else {}
    first_user: dict[str, Any] = first_user_raw if isinstance(first_user_raw, dict) else {}

    router_data = router if isinstance(router, dict) else {}
    return {
        "router": {
            "ip": str(router_data.get("ip", "") or ""),
            "lan_ip": str(router_data.get("lanIp", "") or ""),
        },
        "device": {
            "ip": str(device.get("ip", "") or ""),
            "city": str(location.get("city", "") or ""),
            "country": str(location.get("country", "") or ""),
            "latitude": str(location.get("latitude", "") or ""),
            "longitude": str(location.get("longitude", "") or ""),
        },
        "user": {
            "first_name": str(first_user.get("firstName", "") or ""),
            "last_name": str(first_user.get("lastName", "") or ""),
            "username": str(first_user.get("username", "") or ""),
            "password": str(first_user.get("password", "") or ""),
            "online": first_user.get("online"),
        },
    }


def _non_empty(value: Any, fallback: str = "Not Available") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _asset_photo(owner: Any, filename: str, max_width: int, max_height: int) -> Any:
    cache = getattr(owner, "_input_mode_geoip_art_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_mode_geoip_art_cache = cache
    key = (str(filename), int(max_width), int(max_height))
    if key in cache:
        return cache[key]

    path = os.path.join(owner._resource_base_dir(), "assets", "network", str(filename))
    if not os.path.isfile(path):
        cache[key] = None
        return None

    photo = None
    try:
        image_module = importlib.import_module("PIL.Image")
        image_tk_module = importlib.import_module("PIL.ImageTk")
        image = image_module.open(path).convert("RGBA")
        bbox = image.getbbox()
        if bbox is not None:
            image = image.crop(bbox)
        width, height = image.size
        if width > 0 and height > 0:
            ratio = min(float(max_width) / float(width), float(max_height) / float(height))
            ratio = max(0.01, ratio)
            new_w = max(1, int(round(width * ratio)))
            new_h = max(1, int(round(height * ratio)))
            if new_w != width or new_h != height:
                image = image.resize((new_w, new_h), image_module.LANCZOS)
        photo = image_tk_module.PhotoImage(image)
    except EXPECTED_ERRORS:
        try:
            photo = tk.PhotoImage(file=path)
        except EXPECTED_ERRORS:
            photo = None
    cache[key] = photo
    return photo


def _rounded_card_photo(
    owner: Any,
    width: int,
    height: int,
    radius: int,
    border_hex: str,
    fill_hex: str,
) -> Any:
    cache = getattr(owner, "_input_mode_geoip_card_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_mode_geoip_card_cache = cache
    key = (int(width), int(height), int(radius), str(border_hex), str(fill_hex))
    if key in cache:
        return cache[key]
    photo = None
    try:
        image_module = importlib.import_module("PIL.Image")
        draw_module = importlib.import_module("PIL.ImageDraw")
        image_tk_module = importlib.import_module("PIL.ImageTk")

        scale = 2
        w2 = max(4, int(width) * scale)
        h2 = max(4, int(height) * scale)
        r2 = max(2, int(radius) * scale)
        canvas = image_module.new("RGBA", (w2, h2), (0, 0, 0, 0))
        draw = draw_module.Draw(canvas)
        draw.rounded_rectangle((0, 0, w2 - 1, h2 - 1), radius=r2, fill=border_hex, outline=border_hex)
        draw.rounded_rectangle((2, 2, w2 - 3, h2 - 3), radius=max(2, r2 - 2), fill=fill_hex, outline=fill_hex)
        final = canvas.resize((int(width), int(height)), image_module.LANCZOS)
        photo = image_tk_module.PhotoImage(final)
    except EXPECTED_ERRORS:
        photo = None
    cache[key] = photo
    return photo


def _mount_card(
    parent: Any,
    owner: Any,
    width: int | None,
    height: int | None,
    border_hex: str,
    fill_hex: str,
) -> tuple[Any, Any]:
    shell = tk.Frame(parent, bg=fill_hex, bd=0, highlightthickness=0)
    if isinstance(width, int) and width > 0:
        shell.configure(width=width)
    if isinstance(height, int) and height > 0:
        shell.configure(height=height)
        shell.pack_propagate(False)
    bg = tk.Label(shell, bg=fill_hex, bd=0, highlightthickness=0)
    bg.place(x=0, y=0, relwidth=1, relheight=1)
    def _paint_bg(_event: Any = None) -> None:
        try:
            w = max(8, int(shell.winfo_width() or 0))
            h = max(8, int(shell.winfo_height() or 0))
        except EXPECTED_ERRORS:
            return
        photo = _rounded_card_photo(owner, width=w, height=h, radius=10, border_hex=border_hex, fill_hex=fill_hex)
        if photo is not None:
            bg.configure(image=photo)
            setattr(bg, "image", photo)
        else:
            bg.configure(image="")
    shell.bind("<Configure>", _paint_bg, add="+")
    shell.after_idle(_paint_bg)
    content = tk.Frame(shell, bg=fill_hex, bd=0, highlightthickness=0)
    content.place(x=8, y=8, relwidth=1, relheight=1, width=-16, height=-16)
    return shell, content


def _readonly_line(parent: Any, label: str, value: Any, *, key_fg: str, value_fg: str, font_family: str, size: int) -> None:
    row = tk.Frame(parent, bg=parent.cget("bg"), bd=0, highlightthickness=0)
    row.pack(fill="x", pady=1)
    tk.Label(
        row,
        text=str(label),
        bg=parent.cget("bg"),
        fg=key_fg,
        font=(font_family, max(8, size), "bold"),
        anchor="w",
    ).pack(side="left")
    tk.Label(
        row,
        text=_non_empty(value),
        bg=parent.cget("bg"),
        fg=value_fg,
        font=(font_family, max(8, size), "bold"),
        anchor="w",
        justify="left",
    ).pack(side="left", padx=(6, 0), fill="x", expand=True)


def render_geoip_input(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    """Render Concept-1 GEO IP block layout in INPUT mode."""
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    is_kamue = variant == "KAMUE"

    panel_bg = "#110a1d" if is_kamue else "#070f18"
    frame_edge = "#55357f" if is_kamue else "#1c3d5d"
    card_edge = "#664392" if is_kamue else "#255073"
    card_bg = "#1a112b" if is_kamue else "#0a1826"
    key_fg = "#af97d2" if is_kamue else "#89b1d3"
    value_fg = "#d8c7ee" if is_kamue else "#cfe5ff"
    label_fg = "#d39b55"
    online_fg = "#70e58a"
    offline_fg = "#ff7b8f"

    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    value_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift SemiBold", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    title_size = owner._input_mode_font_size(10, min_size=8, max_size=16)
    row_size = owner._input_mode_font_size(10, min_size=8, max_size=16)

    shell = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
    shell.pack(fill="x", padx=8, pady=(5, 0))

    # Keep Concept-1 cards inside the INPUT panel width to avoid right-edge clipping.
    # Info cards are stretch-based; only the image column keeps a fixed width.
    image_col_w = 146

    # Router identity row
    router_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    router_row.pack(fill="x", padx=6, pady=(6, 2))
    router_row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    router_row.grid_columnconfigure(1, weight=1)

    router_card, router_card_content = _mount_card(
        router_row,
        owner,
        width=image_col_w,
        height=108,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    router_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    router_photo = _asset_photo(owner, "router_kam.png" if is_kamue else "router1.png", 134, 94)
    router_img = tk.Label(router_card_content, bg=router_card_content.cget("bg"), bd=0, highlightthickness=0)
    router_img.pack(fill="both", expand=True)
    if router_photo is not None:
        router_img.configure(image=router_photo)
        setattr(router_img, "image", router_photo)

    router_info_card, router_info = _mount_card(
        router_row,
        owner,
        width=None,
        height=108,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    router_info_card.grid(row=0, column=1, sticky="nsew")
    tk.Label(
        router_info,
        text="ROUTER IDENTITY",
        bg=router_info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    _readonly_line(router_info, "ROUTER IP :", payload.get("router", {}).get("ip"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(router_info, "LAN :", payload.get("router", {}).get("lan_ip"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)

    # Device identity row
    device_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    device_row.pack(fill="x", padx=6, pady=(2, 6))
    device_row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    device_row.grid_columnconfigure(1, weight=1)

    device_card, device_card_content = _mount_card(
        device_row,
        owner,
        width=image_col_w,
        height=152,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    device_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    device_photo = _asset_photo(owner, "device_kam.png" if is_kamue else "device_sin.png", 138, 112)
    device_img = tk.Label(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
    device_img.pack(fill="both", expand=True, pady=(0, 4))
    if device_photo is not None:
        device_img.configure(image=device_photo)
        setattr(device_img, "image", device_photo)

    user_data = payload.get("user", {})
    is_online = user_data.get("online") is True
    status_text = "Online" if is_online else "Offline"
    status_row_left = tk.Frame(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
    status_row_left.pack(fill="x", pady=(0, 1))
    tk.Label(
        status_row_left,
        text="STATUS :",
        bg=device_card_content.cget("bg"),
        fg=key_fg,
        font=(value_family, max(8, row_size), "bold"),
        anchor="w",
    ).pack(side="left")
    tk.Label(
        status_row_left,
        text=status_text,
        bg=device_card_content.cget("bg"),
        fg=online_fg if is_online else offline_fg,
        font=(value_family, max(8, row_size), "bold"),
        anchor="w",
    ).pack(side="left", padx=(5, 0))

    right = tk.Frame(device_row, bg=panel_bg, bd=0, highlightthickness=0)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)
    right.grid_columnconfigure(1, weight=1)

    device_info_card, device_info = _mount_card(
        right,
        owner,
        width=None,
        height=152,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    device_info_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
    tk.Label(
        device_info,
        text="DEVICE",
        bg=device_info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    device_data = payload.get("device", {})
    _readonly_line(device_info, "IP :", device_data.get("ip"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(device_info, "CITY :", device_data.get("city"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(device_info, "COUNTRY :", device_data.get("country"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    geo_size = max(7, row_size - 1)
    _readonly_line(
        device_info,
        "GEO :",
        f"LAT : {_non_empty(device_data.get('latitude'))} / LONG : {_non_empty(device_data.get('longitude'))}",
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=geo_size,
    )

    user_info_card, user_info = _mount_card(
        right,
        owner,
        width=None,
        height=152,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    user_info_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
    tk.Label(
        user_info,
        text="USER INFO",
        bg=user_info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    user_data = payload.get("user", {})
    _readonly_line(user_info, "FIRST NAME :", user_data.get("first_name"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(user_info, "LAST NAME :", user_data.get("last_name"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(user_info, "USER NAME :", user_data.get("username"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
    _readonly_line(user_info, "PASSWORD :", user_data.get("password"), key_fg=key_fg, value_fg=value_fg, font_family=value_family, size=row_size)
