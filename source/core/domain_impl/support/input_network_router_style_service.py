"""Network ROUTER INPUT style helpers.

Provides Concept-2 style ROUTER row discovery/rendering for INPUT mode with
framed sections and editable port/state fields.
"""

import tkinter as tk
from typing import Any


_FIELD_ORDER = (
    "external",
    "internal",
    "service",
    "version",
    "active",
    "locked",
    "accessable",
)


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

        wifi = router.get("wifiNetwork") if isinstance(router.get("wifiNetwork"), dict) else {}
        users = router.get("users") if isinstance(router.get("users"), list) else []
        first_user = users[0] if users and isinstance(users[0], dict) else {}
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
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    return {
        "panel_bg": theme.get("panel", "#161b24"),
        "frame_edge": "#5f3d86" if variant == "KAMUE" else "#295478",
        "left_bg": "#140c22" if variant == "KAMUE" else "#0b1523",
        "right_bg": "#120a1f" if variant == "KAMUE" else "#091521",
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


def _bind_version_placeholder(entry: tk.Entry, var: tk.StringVar) -> None:
    if bool(getattr(entry, "_hh_placeholder_bound", False)):
        return

    def _on_focus_in(_event: Any) -> None:
        placeholder = getattr(entry, "_hh_placeholder_text", None)
        if placeholder and str(var.get()).strip() == str(placeholder):
            var.set("")
        entry.configure(fg=getattr(entry, "_hh_input_fg", "#62d67a"), justify="left")

    def _on_focus_out(_event: Any) -> None:
        placeholder = getattr(entry, "_hh_placeholder_text", None)
        if placeholder and str(var.get()).strip() == "":
            var.set(str(placeholder))
            entry.configure(fg=getattr(entry, "_hh_na_fg", "#d08c8c"), justify="center")
            return
        entry.configure(fg=getattr(entry, "_hh_input_fg", "#62d67a"), justify="left")

    entry.bind("<FocusIn>", _on_focus_in, add="+")
    entry.bind("<FocusOut>", _on_focus_out, add="+")
    entry._hh_placeholder_bound = True


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
        entry._hh_text_var = var
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
        cell = tk.Frame(edit_frame, bg=style["right_bg"], bd=0, highlightthickness=1, highlightbackground=style["frame_edge"])
        cell.grid(row=grid_row, column=grid_col, sticky="nsew", padx=2, pady=2)
        tk.Label(
            cell,
            text=title,
            bg=style["right_bg"],
            fg=style["label_fg"],
            anchor="center",
            justify="center",
            font=(style["label_family"], style["label_size"], "bold"),
        ).pack(fill="x", padx=3, pady=(3, 2))
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
        if is_version:
            _bind_version_placeholder(entry, var)
        entry.pack(fill="x", padx=5, pady=(1, 5), ipady=2)
        bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
        if callable(bind_input_widget):
            bind_input_widget(entry, allow_paste=True)
        field_slots[key] = {"entry": entry, "var": var, "is_version": is_version}

    return {
        "row_frame": row_frame,
        "left": left,
        "right": right,
        "edit_frame": edit_frame,
        "left_labels": left_labels,
        "field_slots": field_slots,
        "field_specs": [],
    }


def _apply_router_row_style(row_slot: dict[str, Any], style: dict[str, Any]) -> None:
    row_slot["row_frame"].configure(bg=style["panel_bg"], highlightbackground=style["frame_edge"])
    row_slot["left"].configure(bg=style["left_bg"], highlightbackground=style["frame_edge"])
    row_slot["right"].configure(bg=style["panel_bg"])
    row_slot["edit_frame"].configure(bg=style["right_bg"], highlightbackground=style["frame_edge"])

    left_labels = row_slot["left_labels"]
    left_labels["ip"].configure(bg=style["left_bg"], fg=style["name_fg"], font=(style["input_family"], style["ip_size"], "bold"))
    for key in ("lan", "model", "wifi", "signal", "wifi_pass", "user", "user_pass"):
        left_labels[key].configure(bg=style["left_bg"], fg=style["meta_fg"], font=(style["input_family"], style["meta_size"], "bold"))

    for field_slot in row_slot["field_slots"].values():
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
    _set_widget_text(left_labels["ip"], row.get("ip", ""))
    _set_widget_text(left_labels["lan"], f"LAN: {row.get('lan_ip', '')}")

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
        placeholder_text = None

        entry._hh_input_fg = style["input_fg"]
        entry._hh_na_fg = style["na_fg"]

        if is_version and str(text_value).strip() == "":
            placeholder_text = "Not Available"
            var.set(placeholder_text)
            entry._hh_placeholder_text = placeholder_text
            entry.configure(fg=style["na_fg"], insertbackground=style["na_fg"], justify="center")
        else:
            var.set(text_value)
            entry._hh_placeholder_text = None
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
                "display_placeholder": placeholder_text,
                "placeholder_as_empty": bool(placeholder_text),
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
