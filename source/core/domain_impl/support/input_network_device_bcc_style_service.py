"""Network DEVICE BCC DOMAINS INPUT style helpers.

Implements BCC DOMAINS rendering for the locked Network DEVICE row in INPUT mode.
Layout keeps router + primary bcc.com identity cards and renders subdomains in a table.
"""

from __future__ import annotations

import importlib
import os
import tkinter as tk
from typing import Any

from core.exceptions import EXPECTED_ERRORS


def _device_domain_name(device: dict[str, Any]) -> str:
    name = device.get("name")
    if not name:
        domain = device.get("domain")
        if isinstance(domain, dict):
            name = domain.get("name")
    return str(name or "")


def _is_bcc_domain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and (name == "bcc.com" or name.endswith(".bcc.com"))


def _is_bcc_subdomain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and name.endswith(".bcc.com")


def is_network_bcc_domains_payload(owner: Any, path: Any, value: Any) -> bool:
    """Return True only for the BCC DOMAINS row under Network DEVICE."""
    if str(getattr(owner, "_editor_mode", "JSON")).upper() != "INPUT":
        return False
    if not isinstance(path, list) or len(path) != 2:
        return False
    if owner._input_mode_root_key_for_path(path) != "network":
        return False
    if not isinstance(path[1], int):
        return False
    if not isinstance(value, dict):
        return False
    if str(value.get("type", "")).strip().upper() != "DEVICE":
        return False
    ip = str(value.get("ip", "") or "").strip()
    if ip != "193.8.64.214":
        return False
    return _device_domain_name(value).strip().casefold() == "bcc.com"


def collect_bcc_domains_payload(owner: Any, normalized_path: Any, device: Any) -> dict[str, Any] | None:
    """Collect router, primary bcc.com identity, and subdomain rows for display."""
    if not is_network_bcc_domains_payload(owner, normalized_path, device):
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

    router_data = router if isinstance(router, dict) else {}
    primary_identity = {
        "ip": str(device.get("ip", "") or ""),
        "domain": _device_domain_name(device),
    }
    subdomain_rows: list[dict[str, str]] = []
    for item in full_network:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).strip().upper() != "DEVICE":
            continue
        domain_name = _device_domain_name(item)
        if not _is_bcc_domain_name(domain_name):
            continue
        row = {
            "ip": str(item.get("ip", "") or ""),
            "domain": str(domain_name or ""),
        }
        if str(domain_name or "").strip().casefold() == "bcc.com":
            primary_identity = row
            continue
        if _is_bcc_subdomain_name(domain_name):
            subdomain_rows.append(row)
    return {
        "router": {
            "ip": str(router_data.get("ip", "") or ""),
            "lan_ip": str(router_data.get("lanIp", "") or ""),
        },
        "primary_identity": primary_identity,
        "subdomain_rows": subdomain_rows,
    }


def _non_empty(value: Any, fallback: str = "Not Available") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _asset_photo(owner: Any, filename: str, max_width: int, max_height: int) -> Any:
    cache = getattr(owner, "_input_mode_bcc_domains_art_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_mode_bcc_domains_art_cache = cache
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
    cache = getattr(owner, "_input_mode_bcc_domains_card_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_mode_bcc_domains_card_cache = cache
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


def render_bcc_domains_input(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    """Render BCC DOMAINS block layout in INPUT mode."""
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    is_kamue = variant == "KAMUE"

    panel_bg = "#110a1d" if is_kamue else "#070f18"
    frame_edge = "#55357f" if is_kamue else "#1c3d5d"
    card_edge = "#664392" if is_kamue else "#255073"
    card_bg = "#1a112b" if is_kamue else "#0a1826"
    key_fg = "#af97d2" if is_kamue else "#89b1d3"
    value_fg = "#d8c7ee" if is_kamue else "#cfe5ff"
    label_fg = "#d39b55"

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
    image_col_w = 146

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
    _readonly_line(
        router_info,
        "ROUTER IP :",
        payload.get("router", {}).get("ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    _readonly_line(
        router_info,
        "LAN :",
        payload.get("router", {}).get("lan_ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )

    # Primary bcc.com identity remains card-based.
    device_photo = _asset_photo(owner, "device_kam.png" if is_kamue else "device_sin.png", 138, 112)
    primary_identity = payload.get("primary_identity")
    primary = primary_identity if isinstance(primary_identity, dict) else {"ip": "", "domain": ""}

    device_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    device_row.pack(fill="x", padx=6, pady=(2, 4))
    device_row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    device_row.grid_columnconfigure(1, weight=1)

    device_card, device_card_content = _mount_card(
        device_row,
        owner,
        width=image_col_w,
        height=132,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    device_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    device_img = tk.Label(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
    device_img.pack(fill="both", expand=True)
    if device_photo is not None:
        device_img.configure(image=device_photo)
        setattr(device_img, "image", device_photo)

    right = tk.Frame(device_row, bg=panel_bg, bd=0, highlightthickness=0)
    right.grid(row=0, column=1, sticky="nsew")
    right.grid_columnconfigure(0, weight=1)
    right.grid_columnconfigure(1, weight=1)

    device_info_card, device_info = _mount_card(
        right,
        owner,
        width=None,
        height=132,
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
    _readonly_line(
        device_info,
        "IP :",
        primary.get("ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )

    domain_info_card, domain_info = _mount_card(
        right,
        owner,
        width=None,
        height=132,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    domain_info_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
    tk.Label(
        domain_info,
        text="DOMAINS",
        bg=domain_info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    _readonly_line(
        domain_info,
        "DOMAIN :",
        primary.get("domain"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )

    # Remaining .bcc.com identities are rendered in a compact table.
    subdomain_rows_raw = payload.get("subdomain_rows")
    subdomain_rows = [row for row in subdomain_rows_raw if isinstance(row, dict)] if isinstance(subdomain_rows_raw, list) else []
    if not subdomain_rows:
        return

    table = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=card_edge)
    table.pack(fill="x", padx=6, pady=(0, 6))
    table.grid_columnconfigure(0, minsize=180, weight=1)
    table.grid_columnconfigure(1, minsize=260, weight=2)

    header_bg = "#201134" if is_kamue else "#0b1f30"
    body_bg = "#160d25" if is_kamue else "#081522"

    for col, title in enumerate(("IP", "DOMAINS")):
        cell = tk.Frame(table, bg=header_bg, bd=0, highlightthickness=1, highlightbackground=card_edge)
        cell.grid(row=0, column=col, sticky="nsew")
        tk.Label(
            cell,
            text=title,
            bg=header_bg,
            fg=value_fg,
            font=(label_family, max(8, row_size), "bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=5)

    for idx, row in enumerate(subdomain_rows, start=1):
        ip_value = _non_empty(row.get("ip"))
        domain_value = _non_empty(row.get("domain"))
        for col, cell_value in enumerate((ip_value, domain_value)):
            cell = tk.Frame(table, bg=body_bg, bd=0, highlightthickness=1, highlightbackground=card_edge)
            cell.grid(row=idx, column=col, sticky="nsew")
            tk.Label(
                cell,
                text=cell_value,
                bg=body_bg,
                fg=value_fg,
                font=(value_family, max(8, row_size), "bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=4)
