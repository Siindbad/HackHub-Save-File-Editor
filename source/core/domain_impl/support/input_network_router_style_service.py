"""Network ROUTER INPUT style helpers.

Provides Concept-2 style ROUTER row discovery/rendering for INPUT mode with
framed sections and editable port/state fields.
"""

import tkinter as tk
import importlib
import os
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


_FIELD_ORDER = (
    "external",
    "internal",
    "service",
    "version",
    "active",
    "locked",
    "accessable",
)

# Secure-access logo tuning knobs (single-source for quick visual iteration).
_SECURE_ACCESS_MAX_WIDTH = 118
_SECURE_ACCESS_MAX_HEIGHT = 42
_SECURE_ACCESS_CELL_MARGIN_X = 1
_SECURE_ACCESS_CELL_MARGIN_Y = 1
_SECURE_ACCESS_CROP_PAD_X = 2
_SECURE_ACCESS_CROP_PAD_TOP = 1
_SECURE_ACCESS_CROP_PAD_BOTTOM = 5
_SECURE_ACCESS_LABEL_PAD_X = 0
_SECURE_ACCESS_LABEL_PAD_Y = 0


def _format_input_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _is_false_like(value: Any) -> bool:
    if value is False:
        return True
    return str(value).strip().lower() == "false"


def is_network_router_group_payload(owner: Any, path: Any, value: Any) -> Any:
    if not isinstance(path, list) or len(path) != 1:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, dict) and str(item.get("type", "")).upper() == "ROUTER" for item in value)


def collect_router_input_rows(owner: Any, normalized_path: Any, routers: Any, max_rows: Any = 60) -> Any:
    # Build editable row definitions with rel_paths mapped to original Network list indices.
    full_network = owner._get_value(normalized_path)
    if not isinstance(full_network, list):
        return []
    index_by_id = {id(item): idx for idx, item in enumerate(full_network) if isinstance(item, dict)}

    rows = []
    for router in routers:
        if len(rows) >= max_rows:
            break
        if not isinstance(router, dict):
            continue
        root_index = index_by_id.get(id(router))
        if root_index is None:
            continue

        wifi_raw = router.get("wifiNetwork")
        wifi = wifi_raw if isinstance(wifi_raw, dict) else {}
        users = router.get("users") if isinstance(router.get("users"), list) else []
        first_user_raw = users[0] if users else {}
        first_user = first_user_raw if isinstance(first_user_raw, dict) else {}
        ports = router.get("ports") if isinstance(router.get("ports"), list) else []
        if not ports:
            ports = [{}]

        for port_index, port in enumerate(ports):
            if len(rows) >= max_rows:
                break
            if not isinstance(port, dict):
                port = {}
            rows.append(
                {
                    "ip": str(router.get("ip", "") or ""),
                    "lan_ip": str(router.get("lanIp", "") or ""),
                    "model": str(router.get("model", "") or ""),
                    "wifi_name": str(wifi.get("name", "") or ""),
                    "wifi_password": str(wifi.get("password", "") or ""),
                    "signal": str(wifi.get("level", "") or ""),
                    "user_name": str(first_user.get("username", "") or ""),
                    "user_password": str(first_user.get("password", "") or ""),
                    "external": {
                        "value": port.get("external"),
                        "rel_path": [root_index, "ports", port_index, "external"],
                        "type": type(port.get("external")),
                    },
                    "internal": {
                        "value": port.get("internal"),
                        "rel_path": [root_index, "ports", port_index, "internal"],
                        "type": type(port.get("internal")),
                    },
                    "service": {
                        "value": port.get("service"),
                        "rel_path": [root_index, "ports", port_index, "service"],
                        "type": type(port.get("service")),
                    },
                    "version": {
                        "value": port.get("version"),
                        "rel_path": [root_index, "ports", port_index, "version"],
                        "type": type(port.get("version")),
                    },
                    "active": {
                        "value": port.get("active"),
                        "rel_path": [root_index, "ports", port_index, "active"],
                        "type": type(port.get("active")),
                    },
                    "locked": {
                        "value": port.get("locked"),
                        "rel_path": [root_index, "ports", port_index, "locked"],
                        "type": type(port.get("locked")),
                    },
                    "accessable": {
                        "value": router.get("accessable"),
                        "rel_path": [root_index, "accessable"],
                        "type": type(router.get("accessable")),
                    },
                }
            )
    return rows


def reset_router_row_pool(owner: Any) -> None:
    pool = list(getattr(owner, "_input_mode_router_row_pool", []) or [])
    for row_slot in pool:
        row_frame = row_slot.get("row_frame")
        if row_frame is None:
            continue
        try:
            row_frame.destroy()
        except (tk.TclError, RuntimeError, AttributeError):
            continue
    owner._input_mode_router_row_pool = []
    owner._input_mode_router_pool_host = None
    owner._input_mode_router_rendered_count = 0


def _router_style(owner: Any) -> dict[str, Any]:
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    # Use explicit router panel fills per theme to prevent cross-theme bleed.
    panel_bg = "#130a1f" if variant == "KAMUE" else "#08111d"
    return {
        "panel_bg": panel_bg,
        "frame_edge": "#5f3d86" if variant == "KAMUE" else "#295478",
        "left_bg": "#140c22" if variant == "KAMUE" else "#0b1523",
        "right_bg": "#120a1f" if variant == "KAMUE" else "#091521",
        "cell_bg": "#160f27" if variant == "KAMUE" else "#091521",
        "name_fg": "#C8A8FF" if variant == "KAMUE" else "#f2ad5e",
        "meta_fg": "#bbaed0" if variant == "KAMUE" else "#9ab0c2",
        "label_fg": "#d8c0f3" if variant == "KAMUE" else "#b7d5ef",
        "na_fg": "#d08c8c",
        "input_edge": "#8a5bc4" if variant == "KAMUE" else "#2e8fd4",
        "input_bg": "#1b1230" if variant == "KAMUE" else "#071322",
        "input_fg": "#70e58a" if variant == "KAMUE" else "#62d67a",
        "bool_false_fg": "#f3a1ad" if variant == "KAMUE" else "#ff9ea1",
        "label_family": owner._resolve_font_family(
            ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
            owner._credit_name_font()[0],
        ),
        "input_family": owner._resolve_font_family(
            ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
            owner._credit_name_font()[0],
        ),
        "ip_size": owner._input_mode_font_size(11, min_size=9, max_size=20),
        "meta_size": owner._input_mode_font_size(9, min_size=8, max_size=17),
        "label_size": owner._input_mode_font_size(9, min_size=8, max_size=17),
        "input_size": owner._input_mode_font_size(9, min_size=8, max_size=17),
    }


def _ensure_router_pool(owner: Any, host: Any) -> list[dict[str, Any]]:
    if getattr(owner, "_input_mode_router_pool_host", None) is not host:
        for child in host.winfo_children():
            child.destroy()
        owner._input_mode_router_row_pool = []
        owner._input_mode_router_pool_host = host
        owner._input_mode_router_rendered_count = 0
    pool = getattr(owner, "_input_mode_router_row_pool", None)
    if not isinstance(pool, list):
        pool = []
        owner._input_mode_router_row_pool = pool
    return pool


def prepare_router_render_host(owner: Any, host: Any, *, reset_pool: bool = False) -> None:
    if bool(reset_pool):
        reset_router_row_pool(owner)
    pool = _ensure_router_pool(owner, host)
    for row_slot in pool:
        row_frame = row_slot.get("row_frame")
        if row_frame is None:
            continue
        if row_frame.winfo_manager() == "pack":
            row_frame.pack_forget()
    owner._input_mode_router_rendered_count = 0


def suspend_router_render_host(owner: Any, host: Any) -> set[Any]:
    # Preserve pooled router rows across category switches; hide them instead of destroying.
    if getattr(owner, "_input_mode_router_pool_host", None) is not host:
        return set()
    keep_children: set[Any] = set()
    pool = list(getattr(owner, "_input_mode_router_row_pool", []) or [])
    for row_slot in pool:
        row_frame = row_slot.get("row_frame")
        if row_frame is None:
            continue
        try:
            if row_frame.winfo_manager() == "pack":
                row_frame.pack_forget()
            keep_children.add(row_frame)
        except (tk.TclError, RuntimeError, AttributeError):
            continue
    owner._input_mode_router_rendered_count = 0
    return keep_children


def _set_label_visible(label: Any, visible: bool, *, pady: tuple[int, int] | None = None) -> None:
    if visible:
        if label.winfo_manager() != "pack":
            kwargs = {"anchor": "w", "padx": 7}
            if pady is not None:
                kwargs["pady"] = pady
            label.pack(**kwargs)
        return
    if label.winfo_manager() == "pack":
        label.pack_forget()


def _set_widget_text(widget: Any, value: str) -> None:
    var = getattr(widget, "_hh_text_var", None)
    if isinstance(var, tk.StringVar):
        var.set(str(value))
        return
    try:
        widget.configure(text=str(value))
    except (tk.TclError, RuntimeError, AttributeError):
        return


def _router_asset_path(owner: Any, filename: str) -> str:
    return os.path.join(owner._resource_base_dir(), "assets", "network", str(filename))


def _load_router_art_photo(
    owner: Any,
    path: str,
    *,
    max_width: int,
    max_height: int,
    stretch: bool = False,
    allow_upscale: bool = False,
    fit_mode: str = "contain",
) -> Any:
    cache = getattr(owner, "_input_mode_router_art_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._input_mode_router_art_cache = cache
    mode = str(fit_mode or "contain").strip().lower()
    key = (str(path), int(max_width), int(max_height), bool(stretch), bool(allow_upscale), mode)
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
        # Trim transparent padding so logos can truly fill target frames.
        bbox = image.getbbox()
        if bbox is not None:
            image = image.crop(bbox)
        # secure_access.png ships on a large matte canvas; crop to logo foreground first.
        if os.path.basename(str(path)).strip().lower() == "secure_access.png":
            image_chops_module = importlib.import_module("PIL.ImageChops")
            red_chan, green_chan, blue_chan, _alpha_chan = image.split()
            green_over_red = image_chops_module.subtract(green_chan, red_chan).point(lambda v: 255 if v >= 16 else 0)
            green_over_blue = image_chops_module.subtract(green_chan, blue_chan).point(lambda v: 255 if v >= 10 else 0)
            green_floor = green_chan.point(lambda v: 255 if v >= 60 else 0)
            logo_mask = image_chops_module.multiply(image_chops_module.multiply(green_over_red, green_over_blue), green_floor)
            logo_bbox = logo_mask.getbbox()
            if logo_bbox is not None:
                x1, y1, x2, y2 = [int(v) for v in logo_bbox]
                # Keep a thin matte around the logo while still filling the frame.
                pad_x = _SECURE_ACCESS_CROP_PAD_X
                # Bias extra bottom matte so the rendered badge sits visually centered.
                pad_top = _SECURE_ACCESS_CROP_PAD_TOP
                pad_bottom = _SECURE_ACCESS_CROP_PAD_BOTTOM
                image = image.crop(
                    (
                        max(0, x1 - pad_x),
                        max(0, y1 - pad_top),
                        min(image.width, x2 + pad_x),
                        min(image.height, y2 + pad_bottom),
                    )
                )
        width, height = image.size
        if width > 0 and height > 0:
            if bool(stretch):
                target_w = max(1, int(max_width))
                target_h = max(1, int(max_height))
                if target_w != width or target_h != height:
                    image = image.resize((target_w, target_h), image_module.LANCZOS)
            elif mode == "cover":
                target_w = max(1, int(max_width))
                target_h = max(1, int(max_height))
                image_ops_module = importlib.import_module("PIL.ImageOps")
                image = image_ops_module.fit(
                    image,
                    (target_w, target_h),
                    method=image_module.LANCZOS,
                    centering=(0.5, 0.5),
                )
            else:
                ratio = min(float(max_width) / float(width), float(max_height) / float(height))
                if not bool(allow_upscale):
                    ratio = min(ratio, 1.0)
                new_w = max(1, int(width * ratio))
                new_h = max(1, int(height * ratio))
                if new_w != width or new_h != height:
                    image = image.resize((new_w, new_h), image_module.LANCZOS)
        if os.path.basename(str(path)).strip().lower() == "secure_access.png":
            # Nudge the badge content upward for visual centering inside the version frame.
            shifted = image_module.new("RGBA", image.size, (0, 0, 0, 0))
            shifted.paste(image, (0, -2))
            image = shifted
        photo = image_tk_module.PhotoImage(image)
    except EXPECTED_ERRORS as exc:
        _LOG.debug("expected_error", exc_info=exc)
        try:
            raw = tk.PhotoImage(file=path)
            width = raw.width()
            height = raw.height()
            if width > 0 and height > 0:
                scale = max(
                    1,
                    int(round(max(float(width) / float(max_width), float(height) / float(max_height), 1.0))),
                )
                if scale > 1:
                    raw = raw.subsample(scale)
            photo = raw
        except EXPECTED_ERRORS as exc:
            _LOG.debug("expected_error", exc_info=exc)
            photo = None

    cache[key] = photo
    return photo


def _set_art_label_image(label: Any, photo: Any, *, show: bool, padx: int = 7, pady: tuple[int, int] = (4, 4)) -> None:
    if show and photo is not None:
        try:
            label.configure(image=photo)
            setattr(label, "image", photo)
        except (tk.TclError, RuntimeError, AttributeError):
            return
        if label.winfo_manager() != "pack":
            label.pack(anchor="center", padx=padx, pady=pady)
        return
    if label.winfo_manager() == "pack":
        label.pack_forget()


def _render_secure_access_logo(owner: Any, row_slot: dict[str, Any]) -> None:
    cell = row_slot["version_logo_cell"]
    label = row_slot["version_logo_label"]
    cell_width = int(cell.winfo_width())
    cell_height = int(cell.winfo_height())
    if cell_width <= 8 or cell_height <= 8:
        # Geometry is not settled yet; paint a safe default, then retry after layout.
        secure_photo = _load_router_art_photo(
            owner,
            _router_asset_path(owner, "secure_access.png"),
            max_width=_SECURE_ACCESS_MAX_WIDTH - _SECURE_ACCESS_CELL_MARGIN_X,
            max_height=_SECURE_ACCESS_MAX_HEIGHT - _SECURE_ACCESS_CELL_MARGIN_Y,
            allow_upscale=True,
            fit_mode="contain",
            stretch=True,
        )
        _set_art_label_image(label, secure_photo, show=True, padx=0, pady=(0, 0))
        if not bool(getattr(label, "_hh_logo_refresh_pending", False)):
            setattr(label, "_hh_logo_refresh_pending", True)

            def _retry() -> None:
                setattr(label, "_hh_logo_refresh_pending", False)
                _render_secure_access_logo(owner, row_slot)

            cell.after(20, _retry)
        return

    # Keep the frame size stable: grow logo within the cell but cap height to avoid row expansion.
    target_width = max(20, min(cell_width - _SECURE_ACCESS_CELL_MARGIN_X, _SECURE_ACCESS_MAX_WIDTH))
    target_height = max(16, min(cell_height - _SECURE_ACCESS_CELL_MARGIN_Y, _SECURE_ACCESS_MAX_HEIGHT))
    secure_photo = _load_router_art_photo(
        owner,
        _router_asset_path(owner, "secure_access.png"),
        max_width=target_width,
        max_height=target_height,
        allow_upscale=True,
        fit_mode="contain",
        stretch=True,
    )
    _set_art_label_image(label, secure_photo, show=True, padx=0, pady=(0, 0))


def _schedule_secure_access_logo_refresh(owner: Any, row_slot: dict[str, Any]) -> None:
    cell = row_slot["version_logo_cell"]
    pending = bool(row_slot.get("_logo_resize_pending", False))
    if pending:
        return
    row_slot["_logo_resize_pending"] = True

    def _refresh() -> None:
        row_slot["_logo_resize_pending"] = False
        _render_secure_access_logo(owner, row_slot)

    cell.after_idle(_refresh)


def _has_lan_value(lan_ip: Any) -> bool:
    text = str(lan_ip or "").strip().lower()
    return bool(text) and text not in {"n/a", "na", "none", "null"}


def _build_router_row_slot(owner: Any, host: Any, style: dict[str, Any]) -> dict[str, Any]:
    row_frame = tk.Frame(
        host,
        bg=style["panel_bg"],
        bd=0,
        highlightthickness=1,
        highlightbackground=style["frame_edge"],
    )
    row_frame.grid_rowconfigure(0, weight=1)
    row_frame.grid_columnconfigure(0, minsize=206, weight=0)
    row_frame.grid_columnconfigure(1, weight=1)

    left = tk.Frame(row_frame, bg=style["left_bg"], bd=0, highlightthickness=1, highlightbackground=style["frame_edge"])
    left.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=6)

    def _identity_field(fg: str, size: int) -> tk.Entry:
        var = tk.StringVar(value="")
        entry = tk.Entry(
            left,
            textvariable=var,
            relief="flat",
            bd=0,
            highlightthickness=0,
            readonlybackground=style["left_bg"],
            fg=fg,
            justify="left",
            font=(style["input_family"], size, "bold"),
            state="readonly",
        )
        setattr(entry, "_hh_text_var", var)
        bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
        if callable(bind_input_widget):
            bind_input_widget(entry, allow_paste=False)
        return entry

    left_labels = {
        "ip": _identity_field(style["name_fg"], style["ip_size"]),
        "lan": _identity_field(style["meta_fg"], style["meta_size"]),
        "model": _identity_field(style["meta_fg"], style["meta_size"]),
        "wifi": _identity_field(style["meta_fg"], style["meta_size"]),
        "signal": _identity_field(style["meta_fg"], style["meta_size"]),
        "wifi_pass": _identity_field(style["meta_fg"], style["meta_size"]),
        "user": _identity_field(style["meta_fg"], style["meta_size"]),
        "user_pass": _identity_field(style["meta_fg"], style["meta_size"]),
    }
    left_labels["ip"].pack(anchor="w", padx=7, pady=(4, 1))
    left_labels["lan"].pack(anchor="w", padx=7)
    left_router_art = tk.Label(left, bg=style["left_bg"], bd=0, highlightthickness=0)

    right = tk.Frame(row_frame, bg=style["panel_bg"], bd=0, highlightthickness=0)
    right.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=6)
    right.grid_rowconfigure(0, weight=1)
    right.grid_columnconfigure(0, weight=1)

    edit_frame = tk.Frame(right, bg=style["right_bg"], bd=0, highlightthickness=1, highlightbackground=style["frame_edge"])
    edit_frame.grid(row=0, column=0, sticky="nsew")
    edit_frame.grid_rowconfigure(0, weight=1, minsize=46)
    edit_frame.grid_rowconfigure(1, weight=1, minsize=46)
    for idx in range(4):
        minsize = 122 if idx == 3 else 78
        weight = 2 if idx == 3 else 1
        edit_frame.grid_columnconfigure(idx, weight=weight, minsize=minsize)

    field_slots: dict[str, dict[str, Any]] = {}
    fields = (
        ("external", "External", 0, 0),
        ("internal", "Internal", 0, 1),
        ("service", "Service", 0, 2),
        ("version", "Version", 0, 3),
        ("active", "Active", 1, 0),
        ("locked", "Locked", 1, 1),
        ("accessable", "Accessable", 1, 2),
    )
    for key, title, grid_row, grid_col in fields:
        cell = tk.Frame(edit_frame, bg=style["cell_bg"], bd=0, highlightthickness=1, highlightbackground=style["frame_edge"])
        cell.grid(row=grid_row, column=grid_col, sticky="nsew", padx=2, pady=2)
        header_label = tk.Label(
            cell,
            text=title,
            bg=style["cell_bg"],
            fg=style["label_fg"],
            anchor="center",
            justify="center",
            # Use value-family typography for ROUTER field labels to match INPUT value styling.
            font=(style["input_family"], style["label_size"], "bold"),
        )
        header_label.pack(fill="x", padx=3, pady=(3, 2))
        var = tk.StringVar(value="")
        is_version = key == "version"
        entry = tk.Entry(
            cell,
            textvariable=var,
            width=13 if is_version else 8,
            justify="left" if is_version else "center",
            bg=style["input_bg"],
            fg=style["input_fg"],
            insertbackground=style["input_fg"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=style["input_edge"],
            highlightcolor=style["input_edge"],
            font=(style["input_family"], style["input_size"], "bold"),
        )
        entry.pack(fill="x", padx=5, pady=(1, 5), ipady=2)
        bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
        if callable(bind_input_widget):
            bind_input_widget(entry, allow_paste=True)
        field_slots[key] = {"entry": entry, "var": var, "is_version": is_version, "cell": cell, "label": header_label}

    version_logo_cell = tk.Frame(edit_frame, bg=style["cell_bg"], bd=0, highlightthickness=1, highlightbackground=style["frame_edge"])
    version_logo_cell.grid(row=1, column=3, sticky="nsew", padx=2, pady=2)
    version_logo_label = tk.Label(version_logo_cell, bg=style["cell_bg"], bd=0, highlightthickness=0)
    version_logo_label.pack(
        fill="both",
        expand=True,
        padx=_SECURE_ACCESS_LABEL_PAD_X,
        pady=_SECURE_ACCESS_LABEL_PAD_Y,
    )

    row_slot = {
        "row_frame": row_frame,
        "left": left,
        "right": right,
        "edit_frame": edit_frame,
        "left_labels": left_labels,
        "left_router_art": left_router_art,
        "field_slots": field_slots,
        "version_logo_cell": version_logo_cell,
        "version_logo_label": version_logo_label,
        "field_specs": [],
    }
    version_logo_cell.bind("<Configure>", lambda _event: _schedule_secure_access_logo_refresh(owner, row_slot), add="+")
    return row_slot


def _apply_router_row_style(row_slot: dict[str, Any], style: dict[str, Any]) -> None:
    row_slot["row_frame"].configure(bg=style["panel_bg"], highlightbackground=style["frame_edge"])
    row_slot["left"].configure(bg=style["left_bg"], highlightbackground=style["frame_edge"])
    row_slot["right"].configure(bg=style["panel_bg"])
    row_slot["edit_frame"].configure(bg=style["right_bg"], highlightbackground=style["frame_edge"])
    row_slot["version_logo_cell"].configure(bg=style["cell_bg"], highlightbackground=style["frame_edge"])
    row_slot["version_logo_label"].configure(bg=style["cell_bg"])
    row_slot["left_router_art"].configure(bg=style["left_bg"])

    left_labels = row_slot["left_labels"]
    left_labels["ip"].configure(
        bg=style["left_bg"],
        fg=style["name_fg"],
        readonlybackground=style["left_bg"],
        disabledforeground=style["name_fg"],
        insertbackground=style["name_fg"],
        font=(style["input_family"], style["ip_size"], "bold"),
    )
    for key in ("lan", "model", "wifi", "signal", "wifi_pass", "user", "user_pass"):
        left_labels[key].configure(
            bg=style["left_bg"],
            fg=style["meta_fg"],
            readonlybackground=style["left_bg"],
            disabledforeground=style["meta_fg"],
            insertbackground=style["meta_fg"],
            font=(style["input_family"], style["meta_size"], "bold"),
        )

    for field_slot in row_slot["field_slots"].values():
        cell = field_slot.get("cell")
        if cell is not None:
            cell.configure(bg=style["cell_bg"], highlightbackground=style["frame_edge"])
        header_label = field_slot.get("label")
        if header_label is not None:
            header_label.configure(
                bg=style["cell_bg"],
                fg=style["label_fg"],
                font=(style["input_family"], style["label_size"], "bold"),
            )
        entry = field_slot["entry"]
        entry.configure(
            bg=style["input_bg"],
            highlightbackground=style["input_edge"],
            highlightcolor=style["input_edge"],
            font=(style["input_family"], style["input_size"], "bold"),
        )


def _build_row_field_specs(
    owner: Any,
    row_slot: dict[str, Any],
    normalized_path: list[Any],
    row: dict[str, Any],
    style: dict[str, Any],
) -> list[dict[str, Any]]:
    left_labels = row_slot["left_labels"]
    left_router_art = row_slot["left_router_art"]
    _set_widget_text(left_labels["ip"], row.get("ip", ""))
    lan_text = str(row.get("lan_ip", "") or "").strip()
    _set_widget_text(left_labels["lan"], f"LAN: {lan_text}" if lan_text else "LAN:")

    model_value = str(row.get("model", "") or "").strip()
    _set_widget_text(left_labels["model"], f"Model : {model_value}")
    _set_label_visible(left_labels["model"], bool(model_value))

    wifi_name = str(row.get("wifi_name", "") or "").strip()
    signal_value = str(row.get("signal", "") or "").strip()
    wifi_pass = str(row.get("wifi_password", "") or "").strip()
    user_name = str(row.get("user_name", "") or "").strip()
    user_pass = str(row.get("user_password", "") or "").strip()

    has_wifi = bool(wifi_name)
    signal_display = signal_value if signal_value else "N/A"
    pass_display = wifi_pass if wifi_pass else "N/A"

    _set_widget_text(left_labels["wifi"], f"WiFi: {wifi_name}")
    _set_widget_text(left_labels["signal"], f"Signal : {signal_display}")
    left_labels["signal"].configure(fg=style["meta_fg"] if signal_value else style["na_fg"])
    _set_widget_text(left_labels["wifi_pass"], f"Pass : {pass_display}")
    left_labels["wifi_pass"].configure(fg=style["meta_fg"] if wifi_pass else style["na_fg"])
    _set_label_visible(left_labels["wifi"], has_wifi)
    _set_label_visible(left_labels["signal"], has_wifi)
    _set_label_visible(left_labels["wifi_pass"], has_wifi, pady=(0, 4))

    _set_widget_text(left_labels["user"], f"User : {user_name}")
    left_labels["user"].configure(fg=style["meta_fg"])
    _set_widget_text(left_labels["user_pass"], f"Pass : {user_pass}")
    left_labels["user_pass"].configure(fg=style["meta_fg"])
    _set_label_visible(left_labels["user"], not has_wifi and bool(user_name))
    _set_label_visible(left_labels["user_pass"], not has_wifi and bool(user_pass), pady=(0, 4))

    has_detail_under_lan = bool(model_value or has_wifi or user_name or user_pass)
    show_router_art = not has_detail_under_lan
    router_photo = _load_router_art_photo(
        owner,
        _router_asset_path(owner, "router1.png"),
        max_width=190,
        max_height=84,
    )
    _set_art_label_image(left_router_art, router_photo, show=show_router_art, padx=7, pady=(4, 4))

    _render_secure_access_logo(owner, row_slot)

    specs: list[dict[str, Any]] = []
    for field_key in _FIELD_ORDER:
        spec = row[field_key]
        field_slot = row_slot["field_slots"][field_key]
        entry = field_slot["entry"]
        var = field_slot["var"]
        is_version = bool(field_slot["is_version"])

        value = spec.get("value")
        text_value = _format_input_text(value)
        value_fg = style["bool_false_fg"] if _is_false_like(value) else style["input_fg"]
        var.set(text_value)
        entry.configure(
            fg=value_fg,
            insertbackground=value_fg,
            justify="left" if is_version else "center",
        )

        specs.append(
            {
                "rel_path": list(spec.get("rel_path", [])),
                "abs_path": list(normalized_path) + list(spec.get("rel_path", [])),
                "initial": value,
                "type": spec.get("type", type(value)),
                "var": var,
                "widget": entry,
                "display_placeholder": None,
                "placeholder_as_empty": False,
            }
        )

    row_slot["field_specs"] = specs
    return specs


def _row_fingerprint(row: dict[str, Any]) -> tuple[Any, ...]:
    # Skip no-op router row refreshes when values/paths/types are unchanged.
    values: list[Any] = [
        row.get("ip", ""),
        row.get("lan_ip", ""),
        row.get("model", ""),
        row.get("wifi_name", ""),
        row.get("wifi_password", ""),
        row.get("signal", ""),
        row.get("user_name", ""),
        row.get("user_password", ""),
    ]
    for key in _FIELD_ORDER:
        spec = row.get(key, {}) if isinstance(row.get(key, {}), dict) else {}
        values.append(spec.get("value"))
        values.append(tuple(spec.get("rel_path", []) or []))
        values.append(spec.get("type"))
    return tuple(values)


def _rebuild_owner_specs(owner: Any, pool: list[dict[str, Any]], visible_count: int) -> None:
    field_specs: list[dict[str, Any]] = []
    for idx in range(max(0, visible_count)):
        field_specs.extend(pool[idx].get("field_specs", []))
    owner._input_mode_field_specs = field_specs


def render_router_input_rows(
    owner: Any,
    host: Any,
    normalized_path: Any,
    row_defs: Any,
    *,
    start_index: int = 0,
    finalize: bool = False,
    total_rows: int | None = None,
) -> Any:
    # NOTE: Keep this pooled path. Full destroy/recreate caused visible stalls on ROUTER-heavy saves.
    style = _router_style(owner)
    pool = _ensure_router_pool(owner, host)
    base_path = list(normalized_path or [])
    start = max(0, int(start_index or 0))
    rows = list(row_defs or [])

    for offset, row in enumerate(rows):
        row_index = start + offset
        while len(pool) <= row_index:
            pool.append(_build_router_row_slot(owner, host, style))
        row_slot = pool[row_index]
        row_fp = _row_fingerprint(row)
        style_key = (
            style["panel_bg"],
            style["frame_edge"],
            style["left_bg"],
            style["right_bg"],
            style["name_fg"],
            style["meta_fg"],
            style["label_fg"],
            style["na_fg"],
            style["input_edge"],
            style["input_bg"],
            style["input_fg"],
            style["bool_false_fg"],
            style["label_family"],
            style["input_family"],
            style["ip_size"],
            style["meta_size"],
            style["label_size"],
            style["input_size"],
        )
        if row_slot.get("style_key") != style_key:
            _apply_router_row_style(row_slot, style)
            row_slot["style_key"] = style_key
        row_frame = row_slot["row_frame"]
        if row_frame.winfo_manager() != "pack":
            row_frame.pack(fill="x", padx=8, pady=(5, 0))
        if row_slot.get("fingerprint") != row_fp:
            _build_row_field_specs(owner, row_slot, base_path, row, style)
            row_slot["fingerprint"] = row_fp

    rendered_count = max(int(getattr(owner, "_input_mode_router_rendered_count", 0) or 0), start + len(rows))
    owner._input_mode_router_rendered_count = rendered_count

    if finalize:
        visible_count = rendered_count if total_rows is None else max(0, int(total_rows))
        for idx in range(visible_count, len(pool)):
            row_frame = pool[idx].get("row_frame")
            if row_frame is None:
                continue
            if row_frame.winfo_manager() == "pack":
                row_frame.pack_forget()
        owner._input_mode_router_rendered_count = visible_count
        _rebuild_owner_specs(owner, pool, visible_count)
        return

    _rebuild_owner_specs(owner, pool, rendered_count)
