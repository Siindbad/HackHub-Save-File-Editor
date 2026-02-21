"""Network ROUTER INPUT style helpers.

Provides Concept-2 style ROUTER row discovery/rendering for INPUT mode with
framed sections and editable port/state fields.
"""

import tkinter as tk


def _format_input_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def is_network_router_group_payload(owner, path, value):
    if not isinstance(path, list) or len(path) != 1:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, dict) and str(item.get("type", "")).upper() == "ROUTER" for item in value)


def collect_router_input_rows(owner, normalized_path, routers, max_rows=60):
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


def render_router_input_rows(owner, host, normalized_path, row_defs):
    # Concept-2 layout with framed left identity block and framed editable sections.
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    frame_edge = "#5f3d86" if variant == "KAMUE" else "#295478"
    left_bg = "#140c22" if variant == "KAMUE" else "#0b1523"
    right_bg = "#120a1f" if variant == "KAMUE" else "#091521"
    name_fg = "#C8A8FF" if variant == "KAMUE" else "#f2ad5e"
    meta_fg = "#bbaed0" if variant == "KAMUE" else "#9ab0c2"
    label_fg = "#d8c0f3" if variant == "KAMUE" else "#b7d5ef"
    na_fg = "#d08c8c"
    input_edge = "#8a5bc4" if variant == "KAMUE" else "#2e8fd4"
    input_bg = "#1b1230" if variant == "KAMUE" else "#071322"
    input_fg = "#70e58a" if variant == "KAMUE" else "#62d67a"
    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    input_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )

    for row in row_defs:
        row_frame = tk.Frame(
            host,
            bg=panel_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=frame_edge,
        )
        row_frame.pack(fill="x", padx=8, pady=(5, 0))
        # Keep the left identity panel compact so right-side inputs have room.
        row_frame.grid_columnconfigure(0, minsize=206, weight=0)
        row_frame.grid_columnconfigure(1, weight=1)

        left = tk.Frame(row_frame, bg=left_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
        left.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=6)
        tk.Label(left, text=row.get("ip", ""), bg=left_bg, fg=name_fg, anchor="w", font=(input_family, 11, "bold")).pack(anchor="w", padx=7, pady=(4, 1))
        tk.Label(left, text=f"LAN: {row.get('lan_ip', '')}", bg=left_bg, fg=meta_fg, anchor="w", font=(input_family, 9, "bold")).pack(anchor="w", padx=7)
        model_value = str(row.get("model", "") or "").strip()
        if model_value:
            tk.Label(
                left,
                text=f"Model : {model_value}",
                bg=left_bg,
                fg=meta_fg,
                anchor="w",
                font=(input_family, 9, "bold"),
            ).pack(anchor="w", padx=7)
        wifi_name = str(row.get("wifi_name", "") or "").strip()
        signal_value = str(row.get("signal", "") or "").strip()
        wifi_pass = str(row.get("wifi_password", "") or "").strip()
        user_name = str(row.get("user_name", "") or "").strip()
        user_pass = str(row.get("user_password", "") or "").strip()
        has_wifi = bool(wifi_name)
        if has_wifi:
            # WiFi routers keep WiFi + Signal context from wifiNetwork payload.
            signal_display = signal_value if signal_value else "N/A"
            pass_display = wifi_pass if wifi_pass else "N/A"
            tk.Label(
                left,
                text=f"WiFi: {wifi_name}",
                bg=left_bg,
                fg=meta_fg,
                anchor="w",
                font=(input_family, 9, "bold"),
            ).pack(anchor="w", padx=7)
            tk.Label(
                left,
                text=f"Signal : {signal_display}",
                bg=left_bg,
                fg=meta_fg if signal_value else na_fg,
                anchor="w",
                font=(input_family, 9, "bold"),
            ).pack(anchor="w", padx=7)
            tk.Label(
                left,
                text=f"Pass : {pass_display}",
                bg=left_bg,
                fg=meta_fg if wifi_pass else na_fg,
                anchor="w",
                font=(input_family, 9, "bold"),
            ).pack(anchor="w", padx=7, pady=(0, 4))
        else:
            # Non-WiFi routers skip WiFi/Signal and show account credentials when available.
            if user_name:
                tk.Label(
                    left,
                    text=f"User : {user_name}",
                    bg=left_bg,
                    fg=meta_fg,
                    anchor="w",
                    font=(input_family, 9, "bold"),
                ).pack(anchor="w", padx=7)
            if user_pass:
                tk.Label(
                    left,
                    text=f"Pass : {user_pass}",
                    bg=left_bg,
                    fg=meta_fg,
                    anchor="w",
                    font=(input_family, 9, "bold"),
                ).pack(anchor="w", padx=7, pady=(0, 4))

        right = tk.Frame(row_frame, bg=panel_bg, bd=0, highlightthickness=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=6)
        right.grid_columnconfigure(0, weight=1)

        edit_frame = tk.Frame(right, bg=right_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
        edit_frame.grid(row=0, column=0, sticky="ew")
        edit_frame.grid_rowconfigure(0, weight=1, minsize=46)
        edit_frame.grid_rowconfigure(1, weight=1, minsize=46)
        for idx in range(4):
            # Two-row layout: top (External/Internal/Service/Version), bottom (Active/Locked/Accessable).
            minsize = 122 if idx == 3 else 78
            weight = 2 if idx == 3 else 1
            edit_frame.grid_columnconfigure(idx, weight=weight, minsize=minsize)

        fields = (
            ("External", row["external"], 0, 0),
            ("Internal", row["internal"], 0, 1),
            ("Service", row["service"], 0, 2),
            ("Version", row["version"], 0, 3),
            ("Active", row["active"], 1, 0),
            ("Locked", row["locked"], 1, 1),
            ("Accessable", row["accessable"], 1, 2),
        )

        for title, spec, grid_row, grid_col in fields:
            cell = tk.Frame(edit_frame, bg=right_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
            cell.grid(row=grid_row, column=grid_col, sticky="nsew", padx=2, pady=2)
            tk.Label(
                cell,
                text=title,
                bg=right_bg,
                fg=label_fg,
                anchor="center",
                justify="center",
                font=(label_family, 9, "bold"),
            ).pack(fill="x", padx=3, pady=(3, 2))
            value = spec.get("value")
            text_value = _format_input_text(value)
            var = tk.StringVar(value=text_value)
            is_version = title == "Version"
            entry = tk.Entry(
                cell,
                textvariable=var,
                width=13 if is_version else 8,
                justify="left" if is_version else "center",
                bg=input_bg,
                fg=input_fg,
                insertbackground=input_fg,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=input_edge,
                highlightcolor=input_edge,
                font=(input_family, 9, "bold"),
            )
            placeholder_text = None
            if is_version and str(text_value).strip() == "":
                # Visual placeholder: keep field editable and treat placeholder as empty on apply.
                placeholder_text = "Not Available"
                var.set(placeholder_text)
                entry.configure(fg=na_fg, justify="center")

                def _on_focus_in(_event, _var=var, _entry=entry, _placeholder=placeholder_text):
                    if str(_var.get()).strip() == _placeholder:
                        _var.set("")
                    _entry.configure(fg=input_fg, justify="left")

                def _on_focus_out(_event, _var=var, _entry=entry, _placeholder=placeholder_text):
                    if str(_var.get()).strip() == "":
                        _var.set(_placeholder)
                        _entry.configure(fg=na_fg, justify="center")
                    else:
                        _entry.configure(fg=input_fg, justify="left")

                entry.bind("<FocusIn>", _on_focus_in, add="+")
                entry.bind("<FocusOut>", _on_focus_out, add="+")
            entry.pack(fill="x", padx=5, pady=(1, 5), ipady=2)
            owner._input_mode_field_specs.append(
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
