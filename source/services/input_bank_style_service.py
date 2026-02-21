"""Bank INPUT style helpers.

Keeps Bank-specific INPUT row collection and rendering in the service layer so
layout/style iterations do not bloat the main editor module.
"""

import tkinter as tk


def collect_bank_input_rows(value, max_rows=40):
    # Bank style-4 view: discover account/provider/balance/IBAN rows and map editable balance rel_paths.
    rows = []

    def _add_row(payload, rel_prefix):
        if not isinstance(payload, dict):
            return
        if "balance" not in payload:
            return
        account_name = payload.get("accountName", "")
        provider = payload.get("provider", "N/A")
        iban_value = payload.get("IBAN", "")
        rows.append(
            {
                "account_name": account_name,
                "provider": provider,
                "iban": iban_value,
                "initial": payload.get("balance"),
                "rel_path": list(rel_prefix) + ["balance"],
            }
        )

    def _walk(node, rel_prefix):
        if len(rows) >= max_rows:
            return
        if isinstance(node, list):
            for idx, item in enumerate(node):
                if len(rows) >= max_rows:
                    break
                if isinstance(item, dict):
                    _add_row(item, list(rel_prefix) + [idx])
                    if "balance" not in item:
                        _walk(item, list(rel_prefix) + [idx])
        elif isinstance(node, dict):
            _add_row(node, rel_prefix)
            for key, child in node.items():
                if len(rows) >= max_rows:
                    break
                if isinstance(child, (list, dict)):
                    _walk(child, list(rel_prefix) + [key])

    _walk(value, [])
    return rows


def _draw_rounded(canvas, x1, y1, x2, y2, radius, color, splinesteps=24):
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
    canvas.create_polygon(
        points,
        smooth=True,
        splinesteps=splinesteps,
        fill=color,
        outline=color,
        width=1,
    )


def render_bank_input_style_rows(owner, host, normalized_path, row_defs):
    # Render style-4 inspired Bank INPUT rows with provider pill + balance editor.
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    name_fg = "#C8A8FF" if variant == "KAMUE" else "#f2ad5e"
    iban_fg = "#9ab0c2" if variant != "KAMUE" else "#bbaed0"
    iban_label_fg = "#4fd5ff"
    row_edge = "#4f356f" if variant == "KAMUE" else "#254b6b"
    row_bg = "#160f22" if variant == "KAMUE" else "#0b1421"
    provider_edge = "#8f6ad1" if variant == "KAMUE" else "#3c7eaf"
    provider_bg = "#241734" if variant == "KAMUE" else "#0a1f30"
    provider_fg = "#eadcff" if variant == "KAMUE" else "#d0dfec"
    input_edge = "#8a5bc4" if variant == "KAMUE" else "#2e8fd4"
    input_bg = "#1b1230" if variant == "KAMUE" else "#081725"
    input_fg = "#70e58a" if variant == "KAMUE" else "#62d67a"
    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur Med", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    account_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Bahnschrift SemiBold", "Segoe UI Semibold", "Segoe UI"],
        label_family,
    )
    provider_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Bahnschrift SemiBold", "Segoe UI Semibold", "Segoe UI"],
        account_family,
    )
    mono_family = owner._resolve_font_family(
        ["Consolas", "Cascadia Mono", "Courier New", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    input_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    account_size = owner._input_mode_font_size(12, min_size=9, max_size=20)
    meta_size = owner._input_mode_font_size(9, min_size=8, max_size=16)
    provider_size = owner._input_mode_font_size(9, min_size=8, max_size=16)
    input_size = owner._input_mode_font_size(9, min_size=8, max_size=16)

    for row in row_defs:
        row_frame = tk.Frame(
            host,
            bg=row_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=row_edge,
        )
        row_frame.pack(fill="x", padx=8, pady=(5, 0))
        # Stable alignment model:
        # account | flexible middle (provider sits at right edge) | input
        # This keeps input pinned right while provider can sit clearly to its left.
        row_frame.grid_columnconfigure(0, weight=0, minsize=250)
        row_frame.grid_columnconfigure(1, weight=1, minsize=0)
        row_frame.grid_columnconfigure(2, weight=0, minsize=126)

        account_host = tk.Frame(row_frame, bg=row_bg, bd=0, highlightthickness=0)
        account_host.grid(row=0, column=0, sticky="w", padx=(8, 10), pady=6)
        account_name_raw = str(row.get("account_name", "") or "").strip()
        has_account_name = bool(account_name_raw)
        account_display = account_name_raw if has_account_name else "Not Available"
        account_fg = name_fg if has_account_name else "#cc5a5a"
        tk.Label(
            account_host,
            text=account_display,
            bg=row_bg,
            fg=account_fg,
            anchor="w",
            justify="left",
            font=(account_family, account_size, "bold"),
        ).pack(anchor="w")
        iban_line = tk.Frame(account_host, bg=row_bg, bd=0, highlightthickness=0)
        iban_line.pack(anchor="w", pady=(1, 0))
        tk.Label(
            iban_line,
            text="IBAN :",
            bg=row_bg,
            fg=iban_label_fg,
            anchor="w",
            justify="left",
            font=(mono_family, meta_size, "bold"),
        ).pack(side="left")
        tk.Label(
            iban_line,
            text=f"{row.get('iban', '')}",
            bg=row_bg,
            fg=iban_fg,
            anchor="w",
            justify="left",
            font=(mono_family, meta_size, "bold"),
        ).pack(side="left")

        provider_canvas = tk.Canvas(
            row_frame,
            width=118,
            height=28,
            bg=row_bg,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        provider_canvas.grid(row=0, column=1, sticky="e", padx=(0, 104))
        provider_canvas.grid_propagate(False)
        w = 118
        h = 28
        # Rounded pill with smoother edges.
        _draw_rounded(provider_canvas, 0, 0, w - 1, h - 1, radius=12, color=provider_edge, splinesteps=36)
        _draw_rounded(provider_canvas, 1, 1, w - 2, h - 2, radius=11, color=provider_bg, splinesteps=36)
        provider_canvas.create_text(
            w // 2,
            h // 2,
            text=f"Provider : {row.get('provider', 'N/A')}",
            fill=provider_fg,
            font=(provider_family, provider_size, "bold"),
            anchor="c",
        )

        entry_canvas = tk.Canvas(
            row_frame,
            width=118,
            height=28,
            bg=row_bg,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        entry_canvas.grid(row=0, column=2, sticky="e", padx=(2, 8))
        ew = 118
        eh = 28
        # Rounded-square shell with smoother corners.
        _draw_rounded(entry_canvas, 0, 0, ew - 1, eh - 1, radius=7, color=input_edge, splinesteps=28)
        _draw_rounded(entry_canvas, 1, 1, ew - 2, eh - 2, radius=6, color=input_bg, splinesteps=28)
        initial = row.get("initial")
        text_value = "" if initial is None else f"{initial}"
        var = tk.StringVar(value=text_value)
        entry = tk.Entry(
            entry_canvas,
            textvariable=var,
            bg=input_bg,
            fg=input_fg,
            insertbackground=input_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(input_family, input_size, "bold"),
        )
        entry_canvas.create_window(
            ew // 2,
            eh // 2,
            window=entry,
            width=104,
            height=18,
            anchor="c",
        )
        owner._input_mode_field_specs.append(
            {
                "rel_path": list(row.get("rel_path", [])),
                "abs_path": list(normalized_path) + list(row.get("rel_path", [])),
                "initial": initial,
                "type": type(initial),
                "var": var,
                "widget": entry,
            }
        )
