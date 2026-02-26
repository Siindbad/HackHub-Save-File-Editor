"""Database INPUT style helpers for BCC email-table rendering.

Provides a read-only BCC table UI that fits the INPUT editor width constraints
while matching SIINDBAD/KAMUE theme palettes.
"""

from typing import Any
import re
import tkinter as tk


def collect_database_bcc_payload(value: Any, max_rows: Any = 200) -> Any:
    source = _resolve_bcc_source(value)
    if source is None:
        return None
    host = str(source.get("host", "") or "")
    user = str(source.get("user", "") or "")
    password = str(source.get("password", "") or "")
    users = source.get("users", [])
    rows = []
    for idx, row in enumerate(users):
        if len(rows) >= int(max_rows):
            break
        if not isinstance(row, dict):
            continue
        id_cell = row.get("id")
        email_cell = row.get("email")
        if not isinstance(email_cell, dict) or "value" not in email_cell:
            continue
        row_id = id_cell.get("value") if isinstance(id_cell, dict) else None
        email_value = str(email_cell.get("value", "") or "").strip()
        if not email_value:
            continue
        rows.append(
            {
                "row_index": idx,
                "id": row_id,
                "email": email_value,
                "name": _display_name_from_email(email_value),
            }
        )
    if not rows:
        return None
    return {
        "host": host,
        "user": user,
        "password": password,
        "rows": rows,
    }


def collect_database_interpol_payload(value: Any, max_rows: Any = 200) -> Any:
    source = _resolve_interpol_source(value)
    if source is None:
        return None
    host = str(source.get("host", "") or "")
    user = str(source.get("user", "") or "")
    password = str(source.get("password", "") or "")
    customers = source.get("customers", [])
    rows = []
    for idx, row in enumerate(customers):
        if len(rows) >= int(max_rows):
            break
        if not isinstance(row, dict):
            continue
        name_cell = row.get("name")
        email_cell = row.get("email")
        job_cell = row.get("job")
        name_value = name_cell.get("value") if isinstance(name_cell, dict) else None
        email_value = email_cell.get("value") if isinstance(email_cell, dict) else None
        job_value = job_cell.get("value") if isinstance(job_cell, dict) else None
        if not str(name_value or "").strip():
            continue
        rows.append(
            {
                "row_index": idx,
                "name": str(name_value or ""),
                "email": str(email_value or ""),
                "position": str(job_value or ""),
            }
        )
    if not rows:
        return None
    return {
        "host": host,
        "user": user,
        "password": password,
        "rows": rows,
    }


def _resolve_bcc_source(value: Any) -> Any:
    # Supports both Database entry payload and direct tables->users list path.
    if isinstance(value, dict):
        tables = value.get("tables")
        if isinstance(tables, dict):
            users = tables.get("users")
            if _looks_like_users_rows(users):
                return {
                    "host": value.get("host"),
                    "user": value.get("user"),
                    "password": value.get("password"),
                    "users": users,
                }
        return None
    if isinstance(value, list):
        if _looks_like_users_rows(value):
            return {"host": "", "user": "", "password": "", "users": value}
    return None


def _resolve_interpol_source(value: Any) -> Any:
    # Supports both Database entry payload and direct tables->customers list path.
    if isinstance(value, dict):
        tables = value.get("tables")
        if isinstance(tables, dict):
            customers = tables.get("customers")
            if _looks_like_customers_rows(customers):
                return {
                    "host": value.get("host"),
                    "user": value.get("user"),
                    "password": value.get("password"),
                    "customers": customers,
                }
        return None
    if isinstance(value, list):
        if _looks_like_customers_rows(value):
            return {"host": "", "user": "", "password": "", "customers": value}
    return None


def _looks_like_users_rows(rows: Any) -> bool:
    if not isinstance(rows, list) or not rows:
        return False
    first = rows[0]
    if not isinstance(first, dict):
        return False
    email_cell = first.get("email")
    return isinstance(email_cell, dict) and "value" in email_cell


def _looks_like_customers_rows(rows: Any) -> bool:
    if not isinstance(rows, list) or not rows:
        return False
    first = rows[0]
    if not isinstance(first, dict):
        return False
    name_cell = first.get("name")
    email_cell = first.get("email")
    job_cell = first.get("job")
    return (
        isinstance(name_cell, dict)
        and "value" in name_cell
        and isinstance(email_cell, dict)
        and "value" in email_cell
        and isinstance(job_cell, dict)
        and "value" in job_cell
    )


_SURNAME_SUFFIX_HINTS = (
    "yamaguchi",
    "hashimoto",
    "guerrero",
    "kozlova",
    "egorova",
    "paswan",
    "ahmed",
)


def _display_name_from_email(email_value: Any) -> str:
    local_part = str(email_value or "").split("@", 1)[0].strip().lower()
    if not local_part:
        return ""
    raw_tokens = [tok for tok in re.split(r"[._+\-]+", local_part) if tok]
    tokens = [re.sub(r"\d+$", "", token).strip() for token in raw_tokens]
    tokens = [token for token in tokens if token]
    if not tokens:
        return ""
    if len(tokens) == 1:
        compact = tokens[0]
        split_pair = _split_compact_token(compact)
        if split_pair is not None:
            tokens = split_pair
    return " ".join(_title_word(token) for token in tokens if token)


def _split_compact_token(token: str) -> list[str] | None:
    lowered = str(token or "").strip().lower()
    if len(lowered) < 6:
        return None
    for suffix in _SURNAME_SUFFIX_HINTS:
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 1:
            prefix = lowered[: len(lowered) - len(suffix)]
            if len(prefix) >= 3:
                return [prefix, suffix]
    return None


def _title_word(word: str) -> str:
    if not word:
        return ""
    return word[:1].upper() + word[1:].lower()


def _draw_rounded(canvas: Any, x1: Any, y1: Any, x2: Any, y2: Any, radius: Any, color: Any, splinesteps: Any = 36) -> None:
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
        splinesteps=int(splinesteps),
        fill=color,
        outline=color,
        width=1,
    )


def _render_card_label(
    parent: Any,
    *,
    text: Any,
    width: Any,
    height: Any,
    edge: Any,
    fill: Any,
    fg: Any,
    font_spec: Any,
    anchor: Any = "w",
    left_pad: Any = 10,
) -> Any:
    canvas = tk.Canvas(
        parent,
        width=int(width),
        height=int(height),
        bg=parent.cget("bg"),
        highlightthickness=0,
        bd=0,
        relief="flat",
    )
    canvas.pack(fill="x", expand=True)
    _draw_rounded(canvas, 0, 0, int(width) - 1, int(height) - 1, radius=8, color=edge, splinesteps=40)
    _draw_rounded(canvas, 1, 1, int(width) - 2, int(height) - 2, radius=7, color=fill, splinesteps=40)
    x = int(left_pad) if str(anchor) == "w" else int(width) // 2
    canvas.create_text(
        x,
        int(height) // 2,
        text=str(text or ""),
        fill=fg,
        font=font_spec,
        anchor=anchor,
    )
    return canvas


def _render_selectable_card_entry(
    owner: Any,
    parent: Any,
    *,
    text: Any,
    width: Any,
    height: Any,
    edge: Any,
    fill: Any,
    fg: Any,
    font_spec: Any,
    left_pad: Any = 10,
) -> Any:
    canvas = tk.Canvas(
        parent,
        width=int(width),
        height=int(height),
        bg=parent.cget("bg"),
        highlightthickness=0,
        bd=0,
        relief="flat",
    )
    canvas.pack(fill="x", expand=True)
    value_var = tk.StringVar(value=str(text or ""))
    entry = tk.Entry(
        canvas,
        textvariable=value_var,
        bg=fill,
        fg=fg,
        insertbackground=fg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=font_spec,
        justify="left",
    )
    bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
    if callable(bind_input_widget):
        bind_input_widget(entry, allow_paste=True)

    def _redraw(event: Any = None) -> None:
        _ = event
        try:
            w = max(int(width), int(canvas.winfo_width()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            w = int(width)
        h = int(height)
        canvas.delete("all")
        _draw_rounded(canvas, 0, 0, w - 1, h - 1, radius=8, color=edge, splinesteps=40)
        _draw_rounded(canvas, 1, 1, w - 2, h - 2, radius=7, color=fill, splinesteps=40)
        canvas.create_window(
            int(left_pad),
            h // 2,
            window=entry,
            width=max(36, w - (int(left_pad) + 8)),
            height=max(16, h - 10),
            anchor="w",
        )

    canvas.bind("<Configure>", _redraw)
    _redraw()
    return canvas


def render_database_bcc_table(owner: Any, host: Any, normalized_path: Any, payload: Any) -> Any:
    _ = normalized_path
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    if variant == "KAMUE":
        shell_edge = "#6a4697"
        shell_bg = "#1b1230"
        card_edge = "#8f6ad1"
        card_bg = "#1b1230"
        key_fg = "#c8a8ff"
        value_fg = "#e2cbff"
        header_fg = "#d9c2fb"
        row_edge = "#714aa1"
        row_bg = "#1b1230"
        id_fg = "#c7a9ee"
        # Keep BCC email color aligned with INTERPOL neutral value tone.
        email_fg = "#b9aacd"
    else:
        shell_edge = "#2f5f85"
        shell_bg = "#071322"
        card_edge = "#3b7daf"
        card_bg = "#071322"
        key_fg = "#f2ad5e"
        value_fg = "#9fd1ff"
        header_fg = "#a8c9e6"
        row_edge = "#3a78a8"
        row_bg = "#071322"
        id_fg = "#9cb7d4"
        # Keep BCC email color aligned with INTERPOL neutral value tone.
        email_fg = "#93a0ad"

    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    value_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    key_size = owner._input_mode_font_size(8, min_size=7, max_size=16)
    value_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    row_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    email_size = min(20, row_size + 1)
    header_size = owner._input_mode_font_size(8, min_size=7, max_size=16)

    shell = tk.Frame(
        host,
        bg=shell_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=shell_edge,
    )
    shell.pack(fill="x", padx=8, pady=(6, 0))

    identity = tk.Frame(shell, bg=shell_bg, bd=0)
    identity.pack(fill="x", padx=8, pady=(8, 8))
    for col in range(3):
        identity.grid_columnconfigure(col, weight=1, uniform="bcc-id-cards")

    identity_items = (
        ("host", payload.get("host", "")),
        ("user", payload.get("user", "")),
        ("password", payload.get("password", "")),
    )
    for idx, (key_text, val_text) in enumerate(identity_items):
        card = tk.Frame(identity, bg=shell_bg, bd=0)
        card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 4, 0 if idx == 2 else 4))
        tk.Label(
            card,
            text=str(key_text).upper(),
            bg=shell_bg,
            fg=key_fg,
            anchor="w",
            justify="left",
            font=(label_family, key_size, "bold"),
        ).pack(anchor="w", padx=(2, 0), pady=(0, 2))
        _render_selectable_card_entry(
            owner,
            card,
            text=val_text,
            width=220,
            height=30,
            edge=card_edge,
            fill=card_bg,
            fg=value_fg,
            font_spec=(value_family, value_size, "bold"),
            left_pad=10,
        )

    table = tk.Frame(shell, bg=shell_bg, bd=0, highlightthickness=1, highlightbackground=shell_edge)
    table.pack(fill="x", padx=8, pady=(0, 8))
    table.grid_columnconfigure(0, minsize=54, weight=0)
    table.grid_columnconfigure(1, minsize=170, weight=1)
    table.grid_columnconfigure(2, minsize=190, weight=1)

    hdr_id = tk.Label(
        table,
        text="ID",
        bg=shell_bg,
        fg=header_fg,
        anchor="w",
        justify="left",
        font=(label_family, header_size, "bold"),
        padx=6,
        pady=5,
    )
    hdr_id.grid(row=0, column=0, sticky="ew", padx=(3, 2), pady=(4, 2))
    hdr_name = tk.Label(
        table,
        text="Name",
        bg=shell_bg,
        fg=header_fg,
        anchor="w",
        justify="left",
        font=(label_family, header_size, "bold"),
        padx=6,
        pady=5,
    )
    hdr_name.grid(row=0, column=1, sticky="ew", padx=(0, 2), pady=(4, 2))
    hdr_email = tk.Label(
        table,
        text="Email",
        bg=shell_bg,
        fg=header_fg,
        anchor="w",
        justify="left",
        font=(label_family, header_size, "bold"),
        padx=6,
        pady=5,
    )
    hdr_email.grid(row=0, column=2, sticky="ew", padx=(0, 3), pady=(4, 2))

    rows = list(payload.get("rows", []) or [])
    for row_idx, row in enumerate(rows, start=1):
        id_cell = tk.Canvas(
            table,
            width=54,
            height=28,
            bg=shell_bg,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        id_cell.grid(row=row_idx, column=0, sticky="ew", padx=(3, 2), pady=(1, 1))
        id_var = tk.StringVar(value=str("" if row.get("id") is None else row.get("id")))
        id_entry = tk.Entry(
            id_cell,
            textvariable=id_var,
            bg=row_bg,
            fg=id_fg,
            insertbackground=id_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(value_family, row_size, "bold"),
            justify="left",
        )
        bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
        if callable(bind_input_widget):
            bind_input_widget(id_entry, allow_paste=True)

        def _redraw_id(event: Any, canvas: Any = id_cell, widget: Any = id_entry) -> None:
            _ = event
            h = 28
            canvas.delete("all")
            _draw_rounded(canvas, 0, 0, 53, 27, radius=7, color=row_edge, splinesteps=36)
            _draw_rounded(canvas, 1, 1, 52, 26, radius=6, color=row_bg, splinesteps=36)
            canvas.create_window(
                8,
                h // 2,
                window=widget,
                width=42,
                height=16,
                anchor="w",
            )

        id_cell.bind("<Configure>", _redraw_id)
        _redraw_id(None)

        name_cell = tk.Canvas(table, height=28, bg=shell_bg, highlightthickness=0, bd=0, relief="flat")
        name_cell.grid(row=row_idx, column=1, sticky="ew", padx=(0, 2), pady=(1, 1))
        name_var = tk.StringVar(value=str(row.get("name", "") or ""))
        name_entry = tk.Entry(
            name_cell,
            textvariable=name_var,
            bg=row_bg,
            fg=value_fg,
            insertbackground=value_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(value_family, row_size, "bold"),
            justify="left",
        )
        if callable(bind_input_widget):
            bind_input_widget(name_entry, allow_paste=True)

        def _redraw_name(event: Any, canvas: Any = name_cell, widget: Any = name_entry) -> None:
            try:
                w = max(120, int(canvas.winfo_width()))
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                w = 120
            h = 28
            canvas.delete("all")
            _draw_rounded(canvas, 0, 0, w - 1, h - 1, radius=7, color=row_edge, splinesteps=36)
            _draw_rounded(canvas, 1, 1, w - 2, h - 2, radius=6, color=row_bg, splinesteps=36)
            canvas.create_window(
                8,
                h // 2,
                window=widget,
                width=max(36, w - 16),
                height=16,
                anchor="w",
            )

        name_cell.bind("<Configure>", _redraw_name)
        _redraw_name(None)

        email_cell = tk.Canvas(table, height=28, bg=shell_bg, highlightthickness=0, bd=0, relief="flat")
        email_cell.grid(row=row_idx, column=2, sticky="ew", padx=(0, 3), pady=(1, 1))
        email_var = tk.StringVar(value=str(row.get("email", "") or ""))
        email_entry = tk.Entry(
            email_cell,
            textvariable=email_var,
            bg=row_bg,
            fg=email_fg,
            insertbackground=email_fg,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(value_family, email_size, "bold"),
            justify="left",
        )
        if callable(bind_input_widget):
            bind_input_widget(email_entry, allow_paste=True)

        def _redraw_email(event: Any, canvas: Any = email_cell, widget: Any = email_entry) -> None:
            try:
                w = max(100, int(canvas.winfo_width()))
            except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                w = 100
            h = 28
            canvas.delete("all")
            _draw_rounded(canvas, 0, 0, w - 1, h - 1, radius=7, color=row_edge, splinesteps=36)
            _draw_rounded(canvas, 1, 1, w - 2, h - 2, radius=6, color=row_bg, splinesteps=36)
            canvas.create_window(
                8,
                h // 2,
                window=widget,
                width=max(36, w - 16),
                height=16,
                anchor="w",
            )

        email_cell.bind("<Configure>", _redraw_email)
        _redraw_email(None)


def _render_selectable_row_entry_cell(
    owner: Any,
    parent: Any,
    *,
    text: Any,
    fg: Any,
    bg: Any,
    edge: Any,
    font_spec: Any,
    min_width: Any,
    pad_left: Any = 8,
    pad_right: Any = 8,
    right_inset: Any = 0,
) -> Any:
    cell = tk.Canvas(parent, height=28, bg=parent.cget("bg"), highlightthickness=0, bd=0, relief="flat")
    value_var = tk.StringVar(value=str(text or ""))
    entry = tk.Entry(
        cell,
        textvariable=value_var,
        bg=bg,
        fg=fg,
        insertbackground=fg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=font_spec,
        justify="left",
    )
    bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
    if callable(bind_input_widget):
        bind_input_widget(entry, allow_paste=True)

    def _redraw(event: Any) -> None:
        _ = event
        try:
            w = max(int(min_width), int(cell.winfo_width()))
        except (tk.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            w = int(min_width)
        h = 28
        inset_right = max(0, int(right_inset))
        x2_outer = max(6, (w - 1) - inset_right)
        x2_inner = max(5, x2_outer - 1)
        cell.delete("all")
        _draw_rounded(cell, 0, 0, x2_outer, h - 1, radius=7, color=edge, splinesteps=36)
        _draw_rounded(cell, 1, 1, x2_inner, h - 2, radius=6, color=bg, splinesteps=36)
        entry_width = max(28, x2_outer - (int(pad_left) + int(pad_right)))
        cell.create_window(
            int(pad_left),
            h // 2,
            window=entry,
            width=entry_width,
            height=16,
            anchor="w",
        )

    cell.bind("<Configure>", _redraw)
    _redraw(None)
    return cell


def render_database_interpol_table(owner: Any, host: Any, normalized_path: Any, payload: Any) -> Any:
    _ = normalized_path
    theme = getattr(owner, "_theme", {})
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    panel_bg = theme.get("panel", "#161b24")
    if variant == "KAMUE":
        shell_edge = "#6a4697"
        shell_bg = "#1b1230"
        card_edge = "#8f6ad1"
        card_bg = "#1b1230"
        key_fg = "#c8a8ff"
        value_fg = "#e2cbff"
        header_fg = "#d9c2fb"
        row_edge = "#714aa1"
        row_bg = "#1b1230"
        name_fg = "#d7c2ff"
        # INTERPOL emails should match Position tone.
        email_fg = "#b9aacd"
        position_fg = "#b9aacd"
    else:
        shell_edge = "#2f5f85"
        shell_bg = "#071322"
        card_edge = "#3b7daf"
        card_bg = "#071322"
        key_fg = "#f2ad5e"
        value_fg = "#9fd1ff"
        header_fg = "#a8c9e6"
        row_edge = "#3a78a8"
        row_bg = "#071322"
        name_fg = "#c6dcf2"
        # INTERPOL emails should match Position tone.
        email_fg = "#93a0ad"
        position_fg = "#93a0ad"

    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    value_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    key_size = owner._input_mode_font_size(8, min_size=7, max_size=16)
    value_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    row_size = owner._input_mode_font_size(9, min_size=8, max_size=18)
    email_size = min(20, row_size + 1)
    header_size = owner._input_mode_font_size(8, min_size=7, max_size=16)

    shell = tk.Frame(
        host,
        bg=shell_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=shell_edge,
    )
    shell.pack(fill="x", padx=8, pady=(6, 0))

    identity = tk.Frame(shell, bg=shell_bg, bd=0)
    identity.pack(fill="x", padx=8, pady=(8, 8))
    for col in range(3):
        identity.grid_columnconfigure(col, weight=1, uniform="interpol-id-cards")

    identity_items = (
        ("host", payload.get("host", "")),
        ("user", payload.get("user", "")),
        ("password", payload.get("password", "")),
    )
    for idx, (key_text, val_text) in enumerate(identity_items):
        card = tk.Frame(identity, bg=shell_bg, bd=0)
        card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 4, 0 if idx == 2 else 4))
        tk.Label(
            card,
            text=str(key_text).upper(),
            bg=shell_bg,
            fg=key_fg,
            anchor="w",
            justify="left",
            font=(label_family, key_size, "bold"),
        ).pack(anchor="w", padx=(2, 0), pady=(0, 2))
        _render_selectable_card_entry(
            owner,
            card,
            text=val_text,
            width=220,
            height=30,
            edge=card_edge,
            fill=card_bg,
            fg=value_fg,
            font_spec=(value_family, value_size, "bold"),
            left_pad=10,
        )

    table = tk.Frame(shell, bg=shell_bg, bd=0, highlightthickness=1, highlightbackground=shell_edge)
    table.pack(fill="x", padx=8, pady=(0, 8))
    table.grid_columnconfigure(0, minsize=126, weight=1)
    table.grid_columnconfigure(1, minsize=270, weight=2)
    table.grid_columnconfigure(2, minsize=168, weight=1)

    header_specs = (
        (0, "Name"),
        (1, "Email"),
        (2, "Position"),
    )
    for col_idx, text in header_specs:
        tk.Label(
            table,
            text=text,
            bg=shell_bg,
            fg=header_fg,
            anchor="w",
            justify="left",
            font=(label_family, header_size, "bold"),
            padx=6,
            pady=5,
        ).grid(
            row=0,
            column=col_idx,
            sticky="ew",
            padx=(3 if col_idx == 0 else 0, 2 if col_idx < 2 else 3),
            pady=(4, 2),
        )

    rows = list(payload.get("rows", []) or [])
    for row_idx, row in enumerate(rows, start=1):
        name_cell = _render_selectable_row_entry_cell(
            owner,
            table,
            text=row.get("name", ""),
            fg=name_fg,
            bg=row_bg,
            edge=row_edge,
            font_spec=(value_family, row_size, "bold"),
            min_width=126,
        )
        name_cell.grid(row=row_idx, column=0, sticky="ew", padx=(3, 2), pady=(1, 1))

        email_cell = _render_selectable_row_entry_cell(
            owner,
            table,
            text=row.get("email", ""),
            fg=email_fg,
            bg=row_bg,
            edge=row_edge,
            font_spec=(value_family, email_size, "bold"),
            min_width=270,
            pad_right=12,
            right_inset=2,
        )
        email_cell.grid(row=row_idx, column=1, sticky="ew", padx=(0, 2), pady=(1, 1))

        position_cell = _render_selectable_row_entry_cell(
            owner,
            table,
            text=row.get("position", ""),
            fg=position_fg,
            bg=row_bg,
            edge=row_edge,
            font_spec=(value_family, row_size, "bold"),
            min_width=168,
        )
        position_cell.grid(row=row_idx, column=2, sticky="ew", padx=(0, 3), pady=(1, 1))
