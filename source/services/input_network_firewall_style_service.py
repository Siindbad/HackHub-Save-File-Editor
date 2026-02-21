"""Network FIREWALL INPUT style helpers.

Provides ROUTER Concept-2 aligned FIREWALL row discovery/rendering for INPUT mode
with non-editable identity info and editable per-rule Port/Allowed inputs.
"""

import tkinter as tk


def _format_input_text(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return "" if value is None else str(value)


def _is_false_like(value):
    if value is False:
        return True
    return str(value).strip().lower() == "false"


def is_network_firewall_group_payload(owner, path, value):
    if not isinstance(path, list) or len(path) != 1:
        return False
    if owner._normalize_root_tree_key(path[0]) != "network":
        return False
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, dict) and str(item.get("type", "")).upper() == "FIREWALL" for item in value)


def collect_firewall_input_rows(owner, normalized_path, firewalls, max_rows=40):
    # Map grouped FIREWALL objects back to original Network indices for safe write-back rel_paths.
    full_network = owner._get_value(normalized_path)
    if not isinstance(full_network, list):
        return []
    index_by_id = {id(item): idx for idx, item in enumerate(full_network) if isinstance(item, dict)}

    rows = []
    for firewall in firewalls:
        if len(rows) >= max_rows:
            break
        if not isinstance(firewall, dict):
            continue
        root_index = index_by_id.get(id(firewall))
        if root_index is None:
            continue

        users = firewall.get("users") if isinstance(firewall.get("users"), list) else []
        first_user = users[0] if users and isinstance(users[0], dict) else {}
        user_id = str(first_user.get("id", "") or "")
        username = str(first_user.get("username", "") or "")
        password = str(first_user.get("password", "") or "")
        display_id = user_id or username or str(firewall.get("id", "") or "FIREWALL")

        raw_rules = firewall.get("rules") if isinstance(firewall.get("rules"), list) else []
        rules = []
        for rule_index, rule in enumerate(raw_rules):
            if not isinstance(rule, dict):
                continue
            port_value = rule.get("port")
            allowed_value = rule.get("allowed")
            rules.append(
                {
                    "port": {
                        "value": port_value,
                        "rel_path": [root_index, "rules", rule_index, "port"],
                        "type": type(port_value),
                    },
                    "allowed": {
                        "value": allowed_value,
                        "rel_path": [root_index, "rules", rule_index, "allowed"],
                        "type": type(allowed_value),
                    },
                }
            )

        rows.append(
            {
                "display_id": display_id,
                "ip": str(firewall.get("ip", "") or ""),
                "lan_ip": str(firewall.get("lanIp", "") or ""),
                "user": username,
                "password": password,
                "rules": rules,
            }
        )
    return rows


def render_firewall_input_rows(owner, host, normalized_path, row_defs):
    # Keep FIREWALL visuals aligned with ROUTER Concept-2 palette and framing.
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
    bool_false_fg = "#f3a1ad" if variant == "KAMUE" else "#ff9ea1"
    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    input_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    ip_size = owner._input_mode_font_size(11, min_size=9, max_size=20)
    meta_size = owner._input_mode_font_size(9, min_size=8, max_size=17)
    label_size = owner._input_mode_font_size(9, min_size=8, max_size=17)
    input_size = owner._input_mode_font_size(9, min_size=8, max_size=17)

    for row in row_defs:
        row_frame = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
        row_frame.pack(fill="x", padx=8, pady=(5, 0))
        row_frame.grid_columnconfigure(0, minsize=206, weight=0)
        row_frame.grid_columnconfigure(1, weight=1)

        left = tk.Frame(row_frame, bg=left_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
        left.grid(row=0, column=0, sticky="nsew", padx=(5, 3), pady=6)
        tk.Label(
            left,
            text=row.get("display_id", ""),
            bg=left_bg,
            fg=name_fg,
            anchor="w",
            font=(input_family, ip_size, "bold"),
        ).pack(anchor="w", padx=7, pady=(4, 1))
        tk.Label(
            left,
            text=f"IP : {row.get('ip', '')}",
            bg=left_bg,
            fg=meta_fg,
            anchor="w",
            font=(input_family, meta_size, "bold"),
        ).pack(anchor="w", padx=7)
        tk.Label(
            left,
            text=f"LAN : {row.get('lan_ip', '')}",
            bg=left_bg,
            fg=meta_fg,
            anchor="w",
            font=(input_family, meta_size, "bold"),
        ).pack(anchor="w", padx=7)
        user_value = str(row.get("user", "") or "").strip() or "N/A"
        pass_value = str(row.get("password", "") or "").strip() or "N/A"
        tk.Label(
            left,
            text=f"User : {user_value}",
            bg=left_bg,
            fg=meta_fg if user_value != "N/A" else na_fg,
            anchor="w",
            font=(input_family, meta_size, "bold"),
        ).pack(anchor="w", padx=7)
        tk.Label(
            left,
            text=f"Pass : {pass_value}",
            bg=left_bg,
            fg=meta_fg if pass_value != "N/A" else na_fg,
            anchor="w",
            font=(input_family, meta_size, "bold"),
        ).pack(anchor="w", padx=7, pady=(0, 4))

        right = tk.Frame(row_frame, bg=panel_bg, bd=0, highlightthickness=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 6), pady=6)
        right.grid_columnconfigure(0, weight=1)

        edit_frame = tk.Frame(right, bg=right_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
        edit_frame.grid(row=0, column=0, sticky="ew")
        rules = list(row.get("rules", []) or [])
        if not rules:
            # Keep a visible fallback slot so category never looks empty.
            rules = [
                {
                    "port": {"value": None, "rel_path": None, "type": type(None)},
                    "allowed": {"value": None, "rel_path": None, "type": type(None)},
                }
            ]
        column_count = len(rules)
        for idx in range(column_count):
            edit_frame.grid_columnconfigure(idx, weight=1, minsize=118)

        for col, rule in enumerate(rules):
            cell = tk.Frame(edit_frame, bg=right_bg, bd=0, highlightthickness=1, highlightbackground=frame_edge)
            cell.grid(row=0, column=col, sticky="nsew", padx=2, pady=2)
            tk.Label(
                cell,
                text="PORT",
                bg=right_bg,
                fg=label_fg,
                anchor="center",
                justify="center",
                font=(label_family, label_size, "bold"),
            ).pack(fill="x", padx=3, pady=(3, 2))
            _render_field_input(
                owner,
                container=cell,
                spec=rule["port"],
                normalized_path=normalized_path,
                input_family=input_family,
                input_size=input_size,
                input_bg=input_bg,
                input_fg=input_fg,
                bool_false_fg=bool_false_fg,
                input_edge=input_edge,
                na_fg=na_fg,
            )
            tk.Label(
                cell,
                text="ALLOWED",
                bg=right_bg,
                fg=label_fg,
                anchor="center",
                justify="center",
                font=(label_family, label_size, "bold"),
            ).pack(fill="x", padx=3, pady=(7, 2))
            _render_field_input(
                owner,
                container=cell,
                spec=rule["allowed"],
                normalized_path=normalized_path,
                input_family=input_family,
                input_size=input_size,
                input_bg=input_bg,
                input_fg=input_fg,
                bool_false_fg=bool_false_fg,
                input_edge=input_edge,
                na_fg=na_fg,
            )


def _render_field_input(
    owner,
    container,
    spec,
    normalized_path,
    input_family,
    input_size,
    input_bg,
    input_fg,
    bool_false_fg,
    input_edge,
    na_fg,
):
    value = spec.get("value")
    text_value = _format_input_text(value)
    var = tk.StringVar(value=text_value)
    rel_path = spec.get("rel_path")
    is_editable = isinstance(rel_path, list) and len(rel_path) > 0
    # Booleans keep true/false semantics visible via foreground color in INPUT mode.
    value_fg = bool_false_fg if _is_false_like(value) else input_fg
    entry = tk.Entry(
        container,
        textvariable=var,
        width=12,
        justify="center",
        bg=input_bg,
        fg=value_fg,
        insertbackground=value_fg,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=input_edge,
        highlightcolor=input_edge,
        font=(input_family, input_size, "bold"),
    )
    placeholder_text = None
    if str(text_value).strip() == "":
        # Mirror Version placeholder behavior: visible fallback text, still editable.
        placeholder_text = "Not Available"
        var.set(placeholder_text)
        entry.configure(fg=na_fg)

        def _on_focus_in(_event, _var=var, _entry=entry, _placeholder=placeholder_text):
            if str(_var.get()).strip() == _placeholder:
                _var.set("")
            _entry.configure(fg=input_fg)

        def _on_focus_out(_event, _var=var, _entry=entry, _placeholder=placeholder_text):
            if str(_var.get()).strip() == "":
                _var.set(_placeholder)
                _entry.configure(fg=na_fg)
            else:
                _entry.configure(fg=input_fg)

        entry.bind("<FocusIn>", _on_focus_in, add="+")
        entry.bind("<FocusOut>", _on_focus_out, add="+")

    if not is_editable:
        entry.configure(state="disabled", disabledforeground=na_fg)
    entry.pack(fill="x", padx=5, pady=(1, 5), ipady=2)
    if not is_editable:
        return
    rel_path = list(rel_path)
    owner._input_mode_field_specs.append(
        {
            "rel_path": rel_path,
            "abs_path": list(normalized_path) + rel_path,
            "initial": value,
            "type": spec.get("type", type(value)),
            "var": var,
            "widget": entry,
            "display_placeholder": placeholder_text,
            "placeholder_as_empty": bool(placeholder_text),
        }
    )
