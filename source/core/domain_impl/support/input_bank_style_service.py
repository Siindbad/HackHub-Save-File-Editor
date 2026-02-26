"""Bank INPUT style helpers.

Keeps Bank-specific INPUT row collection and rendering in the service layer so
layout/style iterations do not bloat the main editor module.
"""

import tkinter as tk
from typing import Any


def _collect_my_account_payload(value: Any, max_rows: int = 80) -> dict[str, Any] | None:
    # Bank concept-2 mirror view: focus only My Account identity + linked transactions.
    if not isinstance(value, dict):
        return None
    accounts = value.get("accounts")
    transactions = value.get("transactions")
    if not isinstance(accounts, list) or not isinstance(transactions, list):
        return None

    my_account: dict[str, Any] | None = None
    my_index: int = -1
    for idx, item in enumerate(accounts):
        if not isinstance(item, dict):
            continue
        account_name = str(item.get("accountName", "")).strip().lower()
        if account_name == "my account":
            my_account = item
            my_index = idx
            break
    if my_account is None:
        for idx, item in enumerate(accounts):
            if isinstance(item, dict) and bool(item.get("isMine")):
                my_account = item
                my_index = idx
                break
    if my_account is None:
        return None

    my_id = my_account.get("id")
    my_iban = str(my_account.get("IBAN", "") or "").strip()
    rows: list[dict[str, Any]] = []
    for tx in transactions:
        if not isinstance(tx, dict):
            continue
        if tx.get("accountId") != my_id:
            continue
        direction = _transaction_direction(tx, my_iban)
        is_positive = direction == "in"
        name = _transaction_name(tx, direction)
        iban = _transaction_iban(tx, direction)
        description = str(tx.get("description", "") or "").strip() or "Not Available"
        amount_value = _safe_float(tx.get("amount"))
        amount_text = _format_signed_amount(abs(amount_value), is_positive=is_positive)
        rows.append(
            {
                "name": name,
                "iban": iban,
                "description": description,
                "amount_text": amount_text,
                "is_positive": is_positive,
            }
        )
        if len(rows) >= max_rows:
            break
    return {
        "view": "my_account_mirror",
        "identity": {
            "full_name": str(my_account.get("fullName", "") or "").strip() or "Not Available",
            "iban": my_iban or "Not Available",
            "provider": str(my_account.get("provider", "") or "").strip() or "N/A",
            "balance": my_account.get("balance"),
            "balance_rel_path": ["accounts", my_index, "balance"],
            "balance_type": type(my_account.get("balance")),
        },
        "transactions": rows,
    }


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_signed_amount(amount: float, is_positive: bool) -> str:
    sign = "+" if is_positive else "-"
    return f"{sign}${amount:,.2f}"


def _transaction_direction(tx: dict[str, Any], my_iban: str) -> str:
    to_iban = str(tx.get("to", "") or "").strip()
    from_iban = ""
    from_value = tx.get("from")
    if isinstance(from_value, dict):
        from_iban = str(from_value.get("IBAN", "") or "").strip()
    if my_iban and to_iban == my_iban:
        return "in"
    if my_iban and from_iban == my_iban:
        return "out"
    return "out" if _safe_float(tx.get("amount")) < 0 else "in"


def _transaction_name(tx: dict[str, Any], direction: str) -> str:
    direct_name = str(tx.get("name", "") or "").strip()
    if direct_name:
        return direct_name
    from_value = tx.get("from")
    from_name = ""
    if isinstance(from_value, dict):
        from_name = str(from_value.get("name", "") or "").strip()
    if direction == "in":
        return from_name or "Unknown"
    description = str(tx.get("description", "") or "").strip()
    if ":" in description:
        parsed = description.split(":", 1)[1].strip()
        if parsed:
            return parsed
    return "Recipient"


def _transaction_iban(tx: dict[str, Any], direction: str) -> str:
    direct_iban = str(tx.get("IBAN", "") or tx.get("iban", "") or "").strip()
    if direct_iban:
        return direct_iban
    if direction == "in":
        from_value = tx.get("from")
        if isinstance(from_value, dict):
            from_iban = str(from_value.get("IBAN", "") or "").strip()
            if from_iban:
                return from_iban
    to_iban = str(tx.get("to", "") or "").strip()
    return to_iban or "Not Available"


def collect_bank_input_rows(value: Any, max_rows: Any = 40) -> Any:
    # Bank INPUT now supports My Account mirror payload only.
    payload = _collect_my_account_payload(value, max_rows=int(max_rows))
    if payload:
        return payload
    return None


def _draw_rounded(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
    color: str,
    splinesteps: int = 24,
) -> None:
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


def render_bank_input_style_rows(owner: Any, host: Any, normalized_path: Any, row_defs: Any) -> None:
    # Render My Account mirror payload only.
    if isinstance(row_defs, dict) and row_defs.get("view") == "my_account_mirror":
        _render_my_account_mirror(owner, host, normalized_path, row_defs)
    return


def _render_my_account_mirror(owner: Any, host: Any, normalized_path: Any, payload: dict[str, Any]) -> None:
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    is_kamue = variant == "KAMUE"
    panel_edge = "#553a7f" if is_kamue else "#2b4f71"
    panel_bg = "#140f22" if is_kamue else "#0b1523"
    identity_edge = "#63438f" if is_kamue else "#35526c"
    identity_bg = "#1a1430" if is_kamue else "#0c1420"
    header_bg = "#2a1f44" if is_kamue else "#11263a"
    divider = "#7a58b6" if is_kamue else "#3a6a91"
    text_fg = "#c8e2fb"
    desc_fg = "#a7c3df"
    iban_fg = "#9fc0df"
    amount_pos = "#70e58a"
    amount_neg = "#ff7b8f"
    label_fg = "#f2ad5e"
    value_fg = "#99c9f7"
    input_edge = "#8a5bc4" if is_kamue else "#2e83c1"
    input_bg = "#1b1230" if is_kamue else "#081626"
    input_fg = amount_pos
    row_alt_1 = "#15182d" if is_kamue else "#0e1926"
    row_alt_2 = "#111626" if is_kamue else "#0a1420"
    if is_kamue:
        header_col_bgs = ("#231835", "#281c3d", "#221834", "#1e152d")
        row_col_even = ("#141a2a", "#121726", "#101421", "#0e121c")
        row_col_odd = ("#111725", "#0f1421", "#0d111c", "#0b0f17")
    else:
        header_col_bgs = ("#16324b", "#153149", "#142f46", "#11283e")
        row_col_even = ("#0d1b2c", "#0c1928", "#0b1624", "#09121e")
        row_col_odd = ("#0b1828", "#0a1523", "#09131f", "#08111b")

    label_family = owner._resolve_font_family(
        ["Tektur SemiBold", "Tektur", "Segoe UI Semibold", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    value_family = owner._resolve_font_family(
        ["Segoe UI", "Bahnschrift SemiBold", "Segoe UI Semibold"],
        owner._credit_name_font()[0],
    )
    mono_family = owner._resolve_font_family(
        ["Consolas", "Cascadia Mono", "Courier New", "Segoe UI"],
        owner._credit_name_font()[0],
    )
    label_size = owner._input_mode_font_size(10, min_size=8, max_size=16)
    value_size = owner._input_mode_font_size(10, min_size=8, max_size=16)
    head_size = owner._input_mode_font_size(10, min_size=8, max_size=16)
    row_size = owner._input_mode_font_size(10, min_size=8, max_size=16)

    identity = payload.get("identity", {}) if isinstance(payload.get("identity"), dict) else {}
    card_host = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=panel_edge)
    card_host.pack(fill="x", padx=8, pady=(5, 0))
    # Concept-style identity proportions: 4 cards with IBAN slightly wider and
    # Provider slightly narrower while keeping the row fitting editor width.
    top_weights = (24, 34, 14, 28)  # My Account, IBAN, Provider, Available Balance
    top_mins = (76, 130, 66, 86)
    for col, (weight, min_size) in enumerate(zip(top_weights, top_mins)):
        card_host.grid_columnconfigure(col, weight=weight, minsize=min_size)

    def _paint_identity_card(canvas: tk.Canvas, title: str, primary_text: str, secondary_text: str = "") -> None:
        canvas.delete("face")
        width = max(1, int(canvas.winfo_width()) - 1)
        height = max(54, int(canvas.winfo_height()) - 1)
        _draw_rounded(canvas, 0, 0, width, height, radius=9, color=identity_edge, splinesteps=40)
        _draw_rounded(canvas, 1, 1, width - 1, height - 1, radius=8, color=identity_bg, splinesteps=40)
        canvas.create_text(
            10,
            12,
            text=title,
            fill=label_fg,
            font=(label_family, label_size, "bold"),
            anchor="w",
            tags=("face",),
        )
        canvas.create_text(
            10,
            30,
            text=primary_text,
            fill=value_fg,
            font=(value_family, value_size, "bold"),
            anchor="w",
            tags=("face",),
        )
        if secondary_text:
            canvas.create_text(
                10,
                45,
                text=secondary_text,
                fill=text_fg,
                font=(value_family, max(8, value_size - 1), "bold"),
                anchor="w",
                tags=("face",),
            )

    def _make_identity_canvas(
        col: int,
        title: str,
        primary_text: str,
        secondary_text: str = "",
        colspan: int = 1,
        req_width: int = 120,
    ) -> tk.Canvas:
        canvas = tk.Canvas(
            card_host,
            width=req_width,
            height=58,
            bg=panel_bg,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        canvas.grid(row=0, column=col, columnspan=colspan, sticky="ew", padx=4, pady=6)
        canvas.bind(
            "<Configure>",
            lambda _event, c=canvas, t=title, p=primary_text, s=secondary_text: _paint_identity_card(c, t, p, s),
        )
        canvas.after_idle(lambda c=canvas, t=title, p=primary_text, s=secondary_text: _paint_identity_card(c, t, p, s))
        return canvas

    _make_identity_canvas(0, "My Account", str(identity.get("full_name", "Not Available")), req_width=136)
    _make_identity_canvas(1, "IBAN", str(identity.get("iban", "Not Available")), req_width=208)
    _make_identity_canvas(2, "Provider", str(identity.get("provider", "N/A")), req_width=92)

    balance_shell = tk.Canvas(
        card_host,
        width=164,
        height=58,
        bg=panel_bg,
        bd=0,
        highlightthickness=0,
        relief="flat",
    )
    balance_shell.grid(row=0, column=3, sticky="ew", padx=4, pady=6)
    initial_balance = identity.get("balance")
    balance_value = "" if initial_balance is None else f"${_safe_float(initial_balance):,.2f}"
    balance_var = tk.StringVar(value=balance_value)
    balance_entry = tk.Entry(
        balance_shell,
        textvariable=balance_var,
        bg=input_bg,
        fg=input_fg,
        insertbackground=input_fg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        font=(value_family, row_size, "bold"),
        justify="left",
    )
    balance_entry_window = balance_shell.create_window(0, 0, window=balance_entry, width=120, height=19, anchor="center")

    def _paint_balance_card() -> None:
        balance_shell.delete("face")
        width = max(1, int(balance_shell.winfo_width()) - 1)
        height = max(54, int(balance_shell.winfo_height()) - 1)
        _draw_rounded(balance_shell, 0, 0, width, height, radius=9, color=identity_edge, splinesteps=40)
        _draw_rounded(balance_shell, 1, 1, width - 1, height - 1, radius=8, color=identity_bg, splinesteps=40)
        balance_shell.create_text(
            10,
            12,
            text="Available Balance",
            fill=label_fg,
            font=(label_family, label_size, "bold"),
            anchor="w",
            tags=("face",),
        )
        inner_left = 10
        inner_right = max(inner_left + 40, width - 10)
        _draw_rounded(balance_shell, inner_left, 24, inner_right, 50, radius=6, color=input_edge, splinesteps=32)
        _draw_rounded(balance_shell, inner_left + 1, 25, inner_right - 1, 49, radius=5, color=input_bg, splinesteps=32)
        entry_w = max(72, (inner_right - inner_left) - 10)
        balance_shell.coords(balance_entry_window, (inner_left + inner_right) // 2, 37)
        balance_shell.itemconfigure(balance_entry_window, width=entry_w, height=19)
        balance_shell.lift(balance_entry_window)

    balance_shell.bind("<Configure>", lambda _event: _paint_balance_card())
    balance_shell.after_idle(_paint_balance_card)
    bind_input_widget = getattr(owner, "_bind_input_context_widget", None)
    if callable(bind_input_widget):
        bind_input_widget(balance_entry, allow_paste=True)
    owner._input_mode_field_specs.append(
        {
            "rel_path": list(identity.get("balance_rel_path", [])),
            "abs_path": list(normalized_path) + list(identity.get("balance_rel_path", [])),
            "initial": initial_balance,
            "type": identity.get("balance_type", type(initial_balance)),
            "var": balance_var,
            "widget": balance_entry,
        }
    )

    table_wrap = tk.Frame(host, bg=panel_bg, bd=0, highlightthickness=1, highlightbackground=panel_edge)
    table_wrap.pack(fill="both", expand=True, padx=8, pady=(6, 0))
    grid_host = tk.Frame(table_wrap, bg=panel_bg, bd=0, highlightthickness=0)
    grid_host.pack(fill="both", expand=True, padx=4, pady=4)

    # Shared grid host ensures header/body divider alignment stays exact.
    width_map = {0: 22, 2: 50, 4: 23, 6: 5}
    for col, weight in width_map.items():
        grid_host.grid_columnconfigure(col, weight=weight, minsize=40)
    for divider_col in (1, 3, 5):
        grid_host.grid_columnconfigure(divider_col, weight=0, minsize=1)

    headers = ("Name", "IBAN", "Description", "Amount")
    for idx, title in enumerate(headers):
        col = idx * 2
        justify = "right" if title == "Amount" else "left"
        anchor = "e" if title == "Amount" else "w"
        header_cell_bg = header_col_bgs[idx]
        header_cell = tk.Frame(
            grid_host,
            bg=header_cell_bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=divider,
        )
        header_cell.grid(row=0, column=col, sticky="nsew", padx=0, pady=(0, 2))
        tk.Label(
            header_cell,
            text=title,
            bg=header_cell_bg,
            fg=text_fg,
            font=(label_family, head_size, "bold"),
            anchor=anchor,
            justify=justify,
        ).pack(fill="x", padx=8, pady=5)
        if col < 6:
            tk.Frame(grid_host, bg=divider, width=1).grid(row=0, column=col + 1, sticky="ns", pady=(0, 2))

    tx_rows = payload.get("transactions", [])
    if not isinstance(tx_rows, list):
        tx_rows = []
    if not tx_rows:
        tk.Label(
            grid_host,
            text="No transactions tied to My Account",
            bg=panel_bg,
            fg=desc_fg,
            font=(value_family, row_size, "bold"),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, columnspan=7, sticky="ew", padx=8, pady=8)
        return

    for row_index, item in enumerate(tx_rows):
        if not isinstance(item, dict):
            continue
        grid_row = (row_index * 2) + 1
        line_row = grid_row + 1
        row_bg = row_alt_1 if (row_index % 2 == 0) else row_alt_2
        values = (
            str(item.get("name", "Unknown")),
            str(item.get("iban", "Not Available")),
            str(item.get("description", "Not Available")),
            str(item.get("amount_text", "")),
        )
        fgs = (
            text_fg,
            iban_fg,
            desc_fg,
            amount_pos if bool(item.get("is_positive")) else amount_neg,
        )
        for idx, (text_value, fg_value) in enumerate(zip(values, fgs)):
            col = idx * 2
            justify = "right" if idx == 3 else "left"
            col_bg = row_col_even[idx] if (row_index % 2 == 0) else row_col_odd[idx]
            entry = tk.Entry(
                grid_host,
                textvariable=tk.StringVar(value=text_value),
                relief="flat",
                bd=0,
                highlightthickness=0,
                readonlybackground=col_bg,
                bg=col_bg,
                fg=fg_value,
                justify=justify,
                font=((mono_family if idx in (1, 3) else value_family), row_size, "bold"),
                state="readonly",
                width=1,
            )
            entry.grid(row=grid_row, column=col, sticky="nsew", padx=3, pady=0, ipady=3)
            if callable(bind_input_widget):
                bind_input_widget(entry, allow_paste=False)
            if col < 6:
                tk.Frame(grid_host, bg=divider, width=1).grid(row=grid_row, column=col + 1, sticky="ns")
        # Horizontal row separator across all segments for cleaner table rhythm.
        tk.Frame(grid_host, bg=divider, height=1).grid(
            row=line_row,
            column=0,
            columnspan=7,
            sticky="ew",
            padx=(0, 0),
            pady=(0, 0),
        )

