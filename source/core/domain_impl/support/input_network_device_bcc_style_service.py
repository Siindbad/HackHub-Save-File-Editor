"""Network DEVICE domain table INPUT style helpers.

Implements locked Network DEVICE domain-table layouts in INPUT mode.
Layout keeps router + primary-domain identity cards and renders subdomains in a table.
"""

from __future__ import annotations

import importlib
import os
import tkinter as tk
from typing import Any

from core.exceptions import EXPECTED_ERRORS

_BCC_DOMAIN_ROOT = "bcc.com"
_BLUE_TABLE_DOMAIN_ROOT = "thebluetable.com"
_BCC_PRIMARY_IP = "193.8.64.214"
_INTERPOL_ROUTER_IP = "81.96.16.47"


def _device_domain_name(device: dict[str, Any]) -> str:
    name = device.get("name")
    if not name:
        domain = device.get("domain")
        if isinstance(domain, dict):
            name = domain.get("name")
    return str(name or "")


def _is_bcc_domain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and (name == _BCC_DOMAIN_ROOT or name.endswith(f".{_BCC_DOMAIN_ROOT}"))


def _is_bcc_subdomain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and name.endswith(f".{_BCC_DOMAIN_ROOT}")


def _is_blue_table_domain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and (name == _BLUE_TABLE_DOMAIN_ROOT or name.endswith(f".{_BLUE_TABLE_DOMAIN_ROOT}"))


def _is_blue_table_subdomain_name(value: Any) -> bool:
    name = str(value or "").strip().casefold()
    return bool(name) and name.endswith(f".{_BLUE_TABLE_DOMAIN_ROOT}")


def _collect_full_network(owner: Any, normalized_path: Any) -> list[dict[str, Any]] | None:
    if not isinstance(normalized_path, list) or not normalized_path:
        return None
    full_network = owner._get_value([normalized_path[0]])
    if not isinstance(full_network, list):
        return None
    return [item for item in full_network if isinstance(item, dict)]


def _find_blue_table_anchor_index(full_network: list[dict[str, Any]]) -> int | None:
    first_subdomain_index: int | None = None
    for idx, item in enumerate(full_network):
        if str(item.get("type", "")).strip().upper() != "DEVICE":
            continue
        domain_name = _device_domain_name(item).strip().casefold()
        if domain_name == _BLUE_TABLE_DOMAIN_ROOT:
            return idx
        if first_subdomain_index is None and domain_name.endswith(f".{_BLUE_TABLE_DOMAIN_ROOT}"):
            first_subdomain_index = idx
    return first_subdomain_index


def _find_interpol_anchor_index(full_network: list[dict[str, Any]]) -> int | None:
    blue_anchor_index = _find_blue_table_anchor_index(full_network)
    if blue_anchor_index is None:
        return None
    for idx in range(int(blue_anchor_index) + 1, len(full_network)):
        item = full_network[idx]
        if str(item.get("type", "")).strip().upper() == "DEVICE":
            return idx
    return None


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
    if ip != _BCC_PRIMARY_IP:
        return False
    return _device_domain_name(value).strip().casefold() == _BCC_DOMAIN_ROOT


def is_network_blue_table_payload(owner: Any, path: Any, value: Any) -> bool:
    """Return True only for the BLUE TABLE anchor row under Network DEVICE."""
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
    if not _is_blue_table_domain_name(_device_domain_name(value)):
        return False
    full_network = _collect_full_network(owner, path)
    if not isinstance(full_network, list):
        return False
    anchor_index = _find_blue_table_anchor_index(full_network)
    return anchor_index is not None and int(path[1]) == int(anchor_index)


def is_network_interpol_payload(owner: Any, path: Any, value: Any) -> bool:
    """Return True only for the INTERPOL anchor row under Network DEVICE."""
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
    full_network = _collect_full_network(owner, path)
    if not isinstance(full_network, list):
        return False
    anchor_index = _find_interpol_anchor_index(full_network)
    return anchor_index is not None and int(path[1]) == int(anchor_index)


def _collect_domains_payload(
    owner: Any,
    normalized_path: Any,
    device: Any,
    *,
    is_payload_match: Any,
    is_domain_name: Any,
    is_subdomain_name: Any,
    root_domain: str,
    missing_primary_ip: str = "",
) -> dict[str, Any] | None:
    if not callable(is_payload_match) or not bool(is_payload_match(owner, normalized_path, device)):
        return None
    if not isinstance(normalized_path, list) or not normalized_path:
        return None
    if not isinstance(device, dict):
        return None

    full_network = _collect_full_network(owner, normalized_path)
    if not isinstance(full_network, list):
        return None

    parent_router_ip = str(device.get("parent", "") or "").strip()
    router = None
    for item in full_network:
        if str(item.get("type", "")).upper() != "ROUTER":
            continue
        if str(item.get("ip", "") or "").strip() == parent_router_ip:
            router = item
            break

    router_data = router if isinstance(router, dict) else {}
    primary_identity = {
        "ip": "",
        "domain": str(root_domain),
    }
    subdomain_rows: list[dict[str, str]] = []
    for item in full_network:
        if str(item.get("type", "")).strip().upper() != "DEVICE":
            continue
        domain_name = _device_domain_name(item)
        if not bool(is_domain_name(domain_name)):
            continue
        row = {
            "ip": str(item.get("ip", "") or "").strip(),
            "domain": str(domain_name or "").strip(),
        }
        if str(domain_name or "").strip().casefold() == str(root_domain).casefold():
            primary_identity = {
                "ip": row["ip"],
                "domain": str(root_domain),
            }
            continue
        if bool(is_subdomain_name(domain_name)):
            subdomain_rows.append(row)
    if not str(primary_identity.get("ip", "") or "").strip():
        primary_identity["ip"] = str(missing_primary_ip or "").strip()
    return {
        "router": {
            "ip": str(router_data.get("ip", "") or ""),
            "lan_ip": str(router_data.get("lanIp", "") or ""),
        },
        "primary_identity": primary_identity,
        "subdomain_rows": subdomain_rows,
    }


def collect_bcc_domains_payload(owner: Any, normalized_path: Any, device: Any) -> dict[str, Any] | None:
    """Collect router, primary bcc.com identity, and subdomain rows for display."""
    return _collect_domains_payload(
        owner,
        normalized_path,
        device,
        is_payload_match=is_network_bcc_domains_payload,
        is_domain_name=_is_bcc_domain_name,
        is_subdomain_name=_is_bcc_subdomain_name,
        root_domain=_BCC_DOMAIN_ROOT,
    )


def collect_blue_table_payload(owner: Any, normalized_path: Any, device: Any) -> dict[str, Any] | None:
    """Collect router, primary thebluetable.com identity, and subdomain rows for display."""
    return _collect_domains_payload(
        owner,
        normalized_path,
        device,
        is_payload_match=is_network_blue_table_payload,
        is_domain_name=_is_blue_table_domain_name,
        is_subdomain_name=_is_blue_table_subdomain_name,
        root_domain=_BLUE_TABLE_DOMAIN_ROOT,
        missing_primary_ip="Unknown",
    )


def _collect_network_identity_record(entry: Any) -> dict[str, str]:
    if not isinstance(entry, dict):
        return {"ip": "", "lan_ip": "", "id": ""}
    return {
        "ip": str(entry.get("ip", "") or "").strip(),
        "lan_ip": str(entry.get("lanIp", "") or "").strip(),
        "id": str(entry.get("id", "") or "").strip(),
    }


def _first_user_record(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    users_raw = entry.get("users")
    users = users_raw if isinstance(users_raw, list) else []
    first = users[0] if users and isinstance(users[0], dict) else {}
    return first if isinstance(first, dict) else {}


def _extract_email_value(entry: Any, user: Any) -> str:
    candidates: list[Any] = []
    if isinstance(user, dict):
        candidates.append(user.get("email"))
    if isinstance(entry, dict):
        candidates.append(entry.get("email"))
    for value in candidates:
        if isinstance(value, dict):
            for key in ("value", "email", "address"):
                nested = str(value.get(key, "") or "").strip()
                if nested:
                    return nested
            continue
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _is_interpol_server_name(name: Any) -> bool:
    return str(name or "").strip().casefold().startswith("s-")


def _has_interpol_user_info(device: dict[str, Any]) -> bool:
    for key in ("first_name", "last_name", "username", "password"):
        if str(device.get(key, "") or "").strip():
            return True
    return False


def collect_interpol_payload(owner: Any, normalized_path: Any, device: Any) -> dict[str, Any] | None:
    """Collect INTERPOL router/splitter/firewall identity rows for display."""
    if not is_network_interpol_payload(owner, normalized_path, device):
        return None
    full_network = _collect_full_network(owner, normalized_path)
    if not isinstance(full_network, list):
        return None

    router = None
    for item in full_network:
        if str(item.get("type", "")).strip().upper() != "ROUTER":
            continue
        if str(item.get("ip", "") or "").strip() == _INTERPOL_ROUTER_IP:
            router = item
            break
    router_ip = str((router or {}).get("ip", "") or "").strip()
    if not router_ip:
        router_ip = _INTERPOL_ROUTER_IP

    splitter = None
    firewall = None
    for item in full_network:
        item_type = str(item.get("type", "")).strip().upper()
        parent_ip = str(item.get("parent", "") or "").strip()
        if item_type == "SPLITTER" and splitter is None and parent_ip == router_ip:
            splitter = item
            continue
        if item_type == "FIREWALL" and firewall is None and parent_ip == router_ip:
            firewall = item
            continue
        if splitter is not None and firewall is not None:
            break

    parent_ips = {router_ip}
    splitter_ip = str((splitter or {}).get("ip", "") or "").strip()
    firewall_ip = str((firewall or {}).get("ip", "") or "").strip()
    if splitter_ip:
        parent_ips.add(splitter_ip)
    if firewall_ip:
        parent_ips.add(firewall_ip)

    identity_devices: list[dict[str, Any]] = []
    identity_servers: list[dict[str, Any]] = []
    for item in full_network:
        if str(item.get("type", "")).strip().upper() != "DEVICE":
            continue
        parent_ip = str(item.get("parent", "") or "").strip()
        if parent_ip not in parent_ips:
            continue
        name = _device_domain_name(item).strip()
        if _is_bcc_domain_name(name) or _is_blue_table_domain_name(name):
            # Keep domain-table identities owned by BCC/BLUE TABLE views.
            continue
        user = _first_user_record(item)
        row = {
            "ip": str(item.get("ip", "") or "").strip(),
            "lan_ip": str(item.get("lanIp", "") or "").strip(),
            "email": _extract_email_value(item, user),
            "name": name,
            "first_name": str(user.get("firstName", "") or "").strip(),
            "last_name": str(user.get("lastName", "") or "").strip(),
            "username": str(user.get("username", "") or "").strip(),
            "password": str(user.get("password", "") or "").strip(),
            "online": user.get("online"),
        }
        if _is_interpol_server_name(name):
            identity_servers.append(row)
        else:
            identity_devices.append(row)

    return {
        "router": _collect_network_identity_record(router),
        "splitter": _collect_network_identity_record(splitter),
        "firewall": _collect_network_identity_record(firewall),
        "devices": identity_devices,
        "servers": identity_servers,
    }


def _non_empty(value: Any, fallback: str = "Not Available") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _as_str_any_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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


def _render_identity_row(
    owner: Any,
    shell: Any,
    *,
    panel_bg: str,
    card_edge: str,
    card_bg: str,
    image_card_bg: str,
    label_fg: str,
    key_fg: str,
    value_fg: str,
    label_family: str,
    value_family: str,
    title_size: int,
    row_size: int,
    image_filename: str,
    title: str,
    ip_label: str,
    identity: dict[str, Any],
) -> None:
    image_col_w = 146
    row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    row.pack(fill="x", padx=6, pady=(6, 2))
    row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    row.grid_columnconfigure(1, weight=1)

    image_card, image_card_content = _mount_card(
        row,
        owner,
        width=image_col_w,
        height=108,
        border_hex=card_edge,
        fill_hex=image_card_bg,
    )
    image_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    photo = _asset_photo(owner, image_filename, 134, 94)
    image_label = tk.Label(image_card_content, bg=image_card_content.cget("bg"), bd=0, highlightthickness=0)
    image_label.pack(fill="both", expand=True)
    if photo is not None:
        image_label.configure(image=photo)
        setattr(image_label, "image", photo)

    info_card, info = _mount_card(
        row,
        owner,
        width=None,
        height=108,
        border_hex=card_edge,
        fill_hex=card_bg,
    )
    info_card.grid(row=0, column=1, sticky="nsew")
    tk.Label(
        info,
        text=title,
        bg=info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    _readonly_line(
        info,
        ip_label,
        identity.get("ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    _readonly_line(
        info,
        "LAN :",
        identity.get("lan_ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )


def _render_interpol_device_identity_row(
    owner: Any,
    shell: Any,
    *,
    panel_bg: str,
    card_edge: str,
    card_bg: str,
    image_card_bg: str,
    label_fg: str,
    key_fg: str,
    value_fg: str,
    label_family: str,
    value_family: str,
    title_size: int,
    row_size: int,
    device: dict[str, Any],
    is_kamue: bool,
) -> None:
    online_fg = "#70e58a"
    offline_fg = "#ff7b8f"
    image_col_w = 146

    row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    row.pack(fill="x", padx=6, pady=(2, 6))
    row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    row.grid_columnconfigure(1, weight=1)

    device_card, device_card_content = _mount_card(
        row,
        owner,
        width=image_col_w,
        height=152,
        border_hex=card_edge,
        fill_hex=image_card_bg,
    )
    device_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    device_photo = _asset_photo(owner, "device_kam.png" if is_kamue else "device_sin.png", 138, 112)
    device_img = tk.Label(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
    device_img.pack(fill="both", expand=True, pady=(0, 4))
    if device_photo is not None:
        device_img.configure(image=device_photo)
        setattr(device_img, "image", device_photo)

    online = device.get("online")
    if isinstance(online, bool):
        status_row = tk.Frame(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
        status_row.pack(fill="x", pady=(0, 1))
        tk.Label(
            status_row,
            text="STATUS :",
            bg=device_card_content.cget("bg"),
            fg=key_fg,
            font=(value_family, max(8, row_size), "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            status_row,
            text="Online" if online else "Offline",
            bg=device_card_content.cget("bg"),
            fg=online_fg if online else offline_fg,
            font=(value_family, max(8, row_size), "bold"),
            anchor="w",
        ).pack(side="left", padx=(5, 0))

    right = tk.Frame(row, bg=panel_bg, bd=0, highlightthickness=0)
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
    _readonly_line(
        device_info,
        "IP :",
        device.get("ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    _readonly_line(
        device_info,
        "LAN :",
        device.get("lan_ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    email_value = str(device.get("email", "") or "").strip()
    if email_value:
        _readonly_line(
            device_info,
            "EMAIL :",
            email_value,
            key_fg=key_fg,
            value_fg=value_fg,
            font_family=value_family,
            size=row_size,
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
    if not _has_interpol_user_info(device):
        tk.Label(
            user_info,
            text="Not Available",
            bg=user_info.cget("bg"),
            fg=offline_fg,
            font=(value_family, max(8, row_size), "bold"),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
    else:
        _readonly_line(
            user_info,
            "FIRST NAME :",
            device.get("first_name"),
            key_fg=key_fg,
            value_fg=value_fg,
            font_family=value_family,
            size=row_size,
        )
        _readonly_line(
            user_info,
            "LAST NAME :",
            device.get("last_name"),
            key_fg=key_fg,
            value_fg=value_fg,
            font_family=value_family,
            size=row_size,
        )
        _readonly_line(
            user_info,
            "USER NAME :",
            device.get("username"),
            key_fg=key_fg,
            value_fg=value_fg,
            font_family=value_family,
            size=row_size,
        )
        _readonly_line(
            user_info,
            "PASSWORD :",
            device.get("password"),
            key_fg=key_fg,
            value_fg=value_fg,
            font_family=value_family,
            size=row_size,
        )


def _render_interpol_server_identity_row(
    owner: Any,
    shell: Any,
    *,
    panel_bg: str,
    card_edge: str,
    card_bg: str,
    image_card_bg: str,
    label_fg: str,
    key_fg: str,
    value_fg: str,
    label_family: str,
    value_family: str,
    title_size: int,
    row_size: int,
    server: dict[str, Any],
    is_kamue: bool,
) -> None:
    image_col_w = 146

    row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    row.pack(fill="x", padx=6, pady=(2, 4))
    row.grid_columnconfigure(0, minsize=image_col_w, weight=0)
    row.grid_columnconfigure(1, weight=1)

    device_card, device_card_content = _mount_card(
        row,
        owner,
        width=image_col_w,
        height=132,
        border_hex=card_edge,
        fill_hex=image_card_bg,
    )
    device_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    device_photo = _asset_photo(owner, "server_kam.png" if is_kamue else "server_sin.png", 138, 112)
    device_img = tk.Label(device_card_content, bg=device_card_content.cget("bg"), bd=0, highlightthickness=0)
    device_img.pack(fill="both", expand=True)
    if device_photo is not None:
        device_img.configure(image=device_photo)
        setattr(device_img, "image", device_photo)

    right = tk.Frame(row, bg=panel_bg, bd=0, highlightthickness=0)
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
        server.get("ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    _readonly_line(
        device_info,
        "LAN :",
        server.get("lan_ip"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )
    email_value = str(server.get("email", "") or "").strip()
    if email_value:
        _readonly_line(
            device_info,
            "EMAIL :",
            email_value,
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
        text="SERVER",
        bg=domain_info.cget("bg"),
        fg=label_fg,
        font=(label_family, title_size, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 4))
    _readonly_line(
        domain_info,
        "SERVER :",
        server.get("name"),
        key_fg=key_fg,
        value_fg=value_fg,
        font_family=value_family,
        size=row_size,
    )


def render_bcc_domains_input(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    """Render BCC DOMAINS block layout in INPUT mode."""
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    is_kamue = variant == "KAMUE"

    panel_bg = "#0d0816" if is_kamue else "#050b12"
    frame_edge = "#55357f" if is_kamue else "#1c3d5d"
    card_edge = "#664392" if is_kamue else "#255073"
    card_bg = "#150e24" if is_kamue else "#07121e"
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

    # Primary domain identity remains card-based.
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

    # Remaining subdomain identities are rendered in a compact table.
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
    domains_table_value_fg = "#A6BDD2"

    for col, title in enumerate(("IP", "DOMAINS")):
        cell = tk.Frame(table, bg=header_bg, bd=0, highlightthickness=1, highlightbackground=card_edge)
        cell.grid(row=0, column=col, sticky="nsew")
        tk.Label(
            cell,
            text=title,
            bg=header_bg,
            fg=domains_table_value_fg,
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
                fg=domains_table_value_fg,
                font=(value_family, max(8, row_size), "bold"),
                anchor="w",
            ).pack(fill="x", padx=10, pady=4)


def render_blue_table_input(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    """Render BLUE TABLE block layout in INPUT mode."""
    render_bcc_domains_input(owner, host, normalized_path, payload)


def render_interpol_input(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    """Render INTERPOL identity blocks in INPUT mode."""
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    is_kamue = variant == "KAMUE"

    panel_bg = "#110a1d" if is_kamue else "#070f18"
    frame_edge = "#55357f" if is_kamue else "#1c3d5d"
    card_edge = "#664392" if is_kamue else "#255073"
    card_bg = "#1a112b" if is_kamue else "#0a1826"
    # Keep INTERPOL image tiles darker than info cards for clearer icon contrast.
    image_card_bg = "#0d0817" if is_kamue else "#040a12"
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

    router_identity = _as_str_any_dict(payload.get("router"))
    splitter_identity = _as_str_any_dict(payload.get("splitter"))
    firewall_identity = _as_str_any_dict(payload.get("firewall"))
    device_rows_raw = payload.get("devices")
    server_rows_raw = payload.get("servers")
    device_rows = [row for row in device_rows_raw if isinstance(row, dict)] if isinstance(device_rows_raw, list) else []
    server_rows = [row for row in server_rows_raw if isinstance(row, dict)] if isinstance(server_rows_raw, list) else []

    _render_identity_row(
        owner,
        shell,
        panel_bg=panel_bg,
        card_edge=card_edge,
        card_bg=card_bg,
        image_card_bg=image_card_bg,
        label_fg=label_fg,
        key_fg=key_fg,
        value_fg=value_fg,
        label_family=label_family,
        value_family=value_family,
        title_size=title_size,
        row_size=row_size,
        image_filename="router_kam.png" if is_kamue else "router1.png",
        title="ROUTER IDENTITY",
        ip_label="ROUTER IP :",
        identity=router_identity,
    )
    _render_identity_row(
        owner,
        shell,
        panel_bg=panel_bg,
        card_edge=card_edge,
        card_bg=card_bg,
        image_card_bg=image_card_bg,
        label_fg=label_fg,
        key_fg=key_fg,
        value_fg=value_fg,
        label_family=label_family,
        value_family=value_family,
        title_size=title_size,
        row_size=row_size,
        image_filename="splitter_kam.png" if is_kamue else "splitter_sin.png",
        title="SPLITTER IDENTITY",
        ip_label="SPLITTER IP :",
        identity=splitter_identity,
    )
    _render_identity_row(
        owner,
        shell,
        panel_bg=panel_bg,
        card_edge=card_edge,
        card_bg=card_bg,
        image_card_bg=image_card_bg,
        label_fg=label_fg,
        key_fg=key_fg,
        value_fg=value_fg,
        label_family=label_family,
        value_family=value_family,
        title_size=title_size,
        row_size=row_size,
        image_filename="firewall_kam.png" if is_kamue else "firewall_sin.png",
        title="FIREWALL IDENTITY",
        ip_label="FIREWALL IP :",
        identity=firewall_identity,
    )

    for device in device_rows:
        _render_interpol_device_identity_row(
            owner,
            shell,
            panel_bg=panel_bg,
            card_edge=card_edge,
            card_bg=card_bg,
            image_card_bg=image_card_bg,
            label_fg=label_fg,
            key_fg=key_fg,
            value_fg=value_fg,
            label_family=label_family,
            value_family=value_family,
            title_size=title_size,
            row_size=row_size,
            device=device,
            is_kamue=is_kamue,
        )

    for server in server_rows:
        _render_interpol_server_identity_row(
            owner,
            shell,
            panel_bg=panel_bg,
            card_edge=card_edge,
            card_bg=card_bg,
            image_card_bg=image_card_bg,
            label_fg=label_fg,
            key_fg=key_fg,
            value_fg=value_fg,
            label_family=label_family,
            value_family=value_family,
            title_size=title_size,
            row_size=row_size,
            server=server,
            is_kamue=is_kamue,
        )
