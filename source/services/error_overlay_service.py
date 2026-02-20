import tkinter as tk
import tkinter.font as tkfont


def _overlay_scale_metrics(owner, title):
    """Return warning-overlay sizing metrics that follow active editor font size."""
    is_warning_overlay = str(title or "").strip().lower() == "warning"
    scale_down = 1 if is_warning_overlay else 0
    base_font = max(6, int(getattr(owner, "_font_size", 10) or 10))
    text_font_size = max(8, base_font - scale_down)
    button_font_size = max(8, base_font - 1 - scale_down)
    pad_x = max(4, 10 - scale_down)
    pad_y = max(2, 8 - scale_down)
    button_pad_x = max(4, 8 - scale_down)
    return {
        "is_warning": is_warning_overlay,
        "text_font_size": text_font_size,
        "button_font_size": button_font_size,
        "pad_x": pad_x,
        "pad_y": pad_y,
        "button_pad_x": button_pad_x,
    }


def place_error_pin(owner, index):
    # Place a narrow marker at the current fix/insertion index.
    try:
        palette = owner._current_error_palette()
        if owner.error_pin is None:
            owner.error_pin = tk.Frame(owner.text, bg=palette["fix_bg"], bd=0, highlightthickness=0)
        else:
            owner.error_pin.configure(bg=palette["fix_bg"])
        line = int(str(index).split(".")[0])
        dline = owner.text.dlineinfo(f"{line}.0")
        if not dline:
            return False
        x0, y0, _w0, h0, _b0 = dline
        line_text = owner._line_text(line)
        try:
            col = int(str(index).split(".")[1])
        except Exception:
            col = len(line_text)
        col = max(0, min(col, len(line_text)))
        font = tkfont.Font(font=owner.text.cget("font"))
        x = x0 + font.measure(line_text[:col])
        y = y0
        h = h0

        pin_w = 6
        pin_h = max(8, int(h) - 2)
        pin_y = max(int(y) - 1, 0)
        owner.error_pin.place(x=x, y=pin_y, width=pin_w, height=pin_h)
        owner.error_pin.lift()
        return True
    except Exception:
        return False


def clear_error_pin(owner):
    if owner.error_pin is not None:
        try:
            owner.error_pin.place_forget()
        except Exception:
            pass


def show_error_overlay(owner, title, message):
    # Build the floating error card and apply error tint to editor content.
    pending_actions = getattr(owner, "_error_overlay_actions", None)
    owner._destroy_error_overlay()
    owner._last_error_overlay_message = str(message or "")
    owner._apply_error_tint()
    palette = owner._current_error_palette()
    overlay_bg = palette.get("overlay_bg", "#11161f")
    overlay_fg = palette.get("overlay_fg", "#ffffff")
    metrics = _overlay_scale_metrics(owner, title)
    owner._last_error_overlay_title = str(title or "")
    overlay = tk.Frame(
        owner.text,
        bg=overlay_bg,
        bd=0,
        highlightthickness=2,
        highlightbackground=palette["border"],
        highlightcolor=palette["border"],
    )
    overlay.place(x=12, y=12)

    msg_label = tk.Label(
        overlay,
        text=message,
        bg=overlay_bg,
        fg=overlay_fg,
        font=(owner._preferred_mono_family(), metrics["text_font_size"]),
        anchor="w",
        justify="left",
    )
    msg_label._hh_overlay_role = "message_label"
    msg_label.pack(fill="both", padx=metrics["pad_x"], pady=(metrics["pad_y"], metrics["pad_y"]))

    actions = pending_actions
    if actions:
        button_row = tk.Frame(overlay, bg=overlay_bg, bd=0, highlightthickness=0)
        button_row._hh_overlay_role = "button_row"
        button_row.pack(fill="x", padx=metrics["pad_x"], pady=(0, metrics["pad_y"]))
        button_host = tk.Frame(button_row, bg=overlay_bg, bd=0, highlightthickness=0)
        button_host._hh_overlay_role = "button_host"
        button_host.pack(side="right")
        button_font = (owner._preferred_mono_family(), metrics["button_font_size"], "bold")
        button_border = "#e6edf7"
        button_fill = overlay_bg
        button_text = overlay_fg
        button_active = palette.get("line_bg", overlay_bg)
        for action in tuple(actions):
            if not isinstance(action, (tuple, list)) or len(action) < 2:
                continue
            action_label = str(action[0] or "").strip()
            action_callback = action[1]
            if not action_label or not callable(action_callback):
                continue
            btn_border_wrap = tk.Frame(
                button_host,
                bg=button_border,
                bd=0,
                highlightthickness=0,
            )
            btn_border_wrap._hh_overlay_role = "button_wrap"
            btn_border_wrap.pack(side="left", padx=(0, 6))
            btn = tk.Button(
                btn_border_wrap,
                text=action_label,
                command=action_callback,
                bd=0,
                padx=metrics["button_pad_x"],
                pady=0,
                relief="flat",
                activebackground=button_active,
                activeforeground=button_text,
                highlightthickness=0,
                borderwidth=0,
                highlightbackground=button_border,
                highlightcolor=button_border,
                bg=button_fill,
                fg=button_text,
                font=button_font,
                cursor="hand2",
            )
            btn._hh_overlay_role = "action_button"
            btn.pack(side="left", padx=1, pady=1)
    else:
        overlay.bind("<Button-1>", lambda _evt: owner._destroy_error_overlay())
        msg_label.bind("<Button-1>", lambda _evt: owner._destroy_error_overlay())

    owner.error_overlay = overlay


def destroy_error_overlay(owner):
    # Fully clear overlay + tint + pin state.
    if owner.error_overlay is not None:
        try:
            owner.error_overlay.destroy()
        except Exception:
            pass
        owner.error_overlay = None
    owner._last_error_overlay_message = ""
    owner._last_error_overlay_title = ""
    owner._error_overlay_actions = None
    owner._clear_error_tint()
    owner._clear_error_pin()


def apply_error_tint(owner):
    try:
        palette = owner._current_error_palette()
        owner.text.tag_remove("error_tint", "1.0", "end")
        owner.text.tag_add("error_tint", "1.0", "end")
        owner.text.tag_config("error_tint", background=palette["tint_bg"], foreground=palette["tint_fg"])
        owner.text.tag_lower("error_tint")
        owner._apply_text_selection_style(use_error_palette=True)
    except Exception:
        return


def clear_error_tint(owner):
    try:
        owner.text.tag_remove("error_tint", "1.0", "end")
        owner._apply_text_selection_style(use_error_palette=False)
    except Exception:
        return


def refresh_active_error_theme(owner):
    # Recolor active error visuals when app theme changes.
    try:
        palette = owner._current_error_palette()
    except Exception:
        return
    try:
        has_overlay = bool(owner.error_overlay is not None and owner.error_overlay.winfo_exists())
    except Exception:
        has_overlay = False
    has_tint = owner._tag_has_ranges("error_tint")
    has_line = owner._tag_has_ranges("json_error_line")
    has_error = owner._tag_has_ranges("json_error")
    has_active = has_overlay or has_tint or has_line or has_error

    owner._apply_text_selection_style(use_error_palette=has_active)

    if has_tint:
        try:
            owner.text.tag_config("error_tint", background=palette["tint_bg"], foreground=palette["tint_fg"])
            owner.text.tag_lower("error_tint")
        except Exception:
            pass
    if has_line:
        try:
            owner.text.tag_config("json_error_line", background=palette["line_bg"], foreground="#ffffff")
        except Exception:
            pass
    if has_error:
        try:
            marker_bg, marker_fg = owner._error_marker_colors(
                getattr(owner, "_last_error_highlight_note", ""),
                palette,
                insertion_only=bool(getattr(owner, "_last_error_insertion_only", False)),
            )
            owner.text.tag_config("json_error", background=marker_bg, foreground=marker_fg)
        except Exception:
            pass
    try:
        if owner.error_pin is not None and owner.error_pin.winfo_exists():
            marker_bg, _marker_fg = owner._error_marker_colors(
                getattr(owner, "_last_error_highlight_note", ""),
                palette,
                insertion_only=bool(getattr(owner, "_last_error_insertion_only", False)),
            )
            owner.error_pin.configure(bg=marker_bg)
    except Exception:
        pass

    try:
        if has_line:
            owner.text.tag_raise("json_error_line")
        if has_error:
            owner.text.tag_raise("json_error")
        owner.text.tag_raise("sel")
    except Exception:
        pass

    if has_overlay:
        try:
            overlay_bg = palette.get("overlay_bg", "#11161f")
            overlay_fg = palette.get("overlay_fg", "#ffffff")
            metrics = _overlay_scale_metrics(owner, getattr(owner, "_last_error_overlay_title", ""))
            def _refresh_widget(widget):
                role = str(getattr(widget, "_hh_overlay_role", "") or "")
                try:
                    if role == "message_label" and isinstance(widget, tk.Label):
                        widget.configure(
                            bg=overlay_bg,
                            fg=overlay_fg,
                            font=(owner._preferred_mono_family(), metrics["text_font_size"]),
                        )
                    elif role == "action_button" and isinstance(widget, tk.Button):
                        widget.configure(
                            bg=overlay_bg,
                            fg=overlay_fg,
                            activebackground=palette.get("line_bg", overlay_bg),
                            activeforeground=overlay_fg,
                            relief="flat",
                            bd=0,
                            borderwidth=0,
                            highlightthickness=0,
                            highlightbackground="#e6edf7",
                            highlightcolor="#e6edf7",
                            font=(owner._preferred_mono_family(), metrics["button_font_size"], "bold"),
                            padx=metrics["button_pad_x"],
                        )
                    elif role == "button_wrap":
                        widget.configure(bg="#e6edf7")
                    elif role in ("button_row", "button_host"):
                        widget.configure(bg=overlay_bg)
                    else:
                        widget.configure(bg=overlay_bg)
                except Exception:
                    pass
                try:
                    for child in widget.winfo_children():
                        _refresh_widget(child)
                except Exception:
                    return
            owner.error_overlay.configure(
                bg=overlay_bg,
                highlightbackground=palette["border"],
                highlightcolor=palette["border"],
            )
            for child in owner.error_overlay.winfo_children():
                _refresh_widget(child)
            for child in owner.error_overlay.winfo_children():
                role = str(getattr(child, "_hh_overlay_role", "") or "")
                if role == "message_label":
                    child.pack_configure(padx=metrics["pad_x"], pady=(metrics["pad_y"], metrics["pad_y"]))
                elif role == "button_row":
                    child.pack_configure(padx=metrics["pad_x"], pady=(0, metrics["pad_y"]))
        except Exception:
            pass
        try:
            line = owner._line_number_from_index(getattr(owner, "_error_focus_index", None))
            if line:
                owner._position_error_overlay(line)
        except Exception:
            pass


def position_error_overlay(owner, line):
    # Keep overlay near the active error line without leaving text viewport bounds.
    if owner.error_overlay is None:
        return
    try:
        def _first_content_x(line_no, fallback_x):
            try:
                dline = owner.text.dlineinfo(f"{line_no}.0")
                if not dline:
                    return int(fallback_x)
                x0 = int(dline[0])
                line_text = owner._line_text(line_no)
                if not line_text:
                    return x0
                first_col = 0
                for idx, ch in enumerate(line_text):
                    if not ch.isspace():
                        first_col = idx
                        break
                font = tkfont.Font(font=owner.text.cget("font"))
                return x0 + int(font.measure(line_text[:first_col]))
            except Exception:
                return int(fallback_x)

        def _nearest_non_empty_line(line_no):
            try:
                max_line = int(owner.text.index("end-1c").split(".")[0])
            except Exception:
                max_line = max(int(line_no or 1), 1)
            line_no = max(1, min(int(line_no or 1), max_line))
            try:
                if owner._line_text(line_no).strip():
                    return line_no
            except Exception:
                pass
            for delta in range(1, 6):
                up = line_no - delta
                if up >= 1:
                    try:
                        if owner._line_text(up).strip():
                            return up
                    except Exception:
                        pass
                down = line_no + delta
                if down <= max_line:
                    try:
                        if owner._line_text(down).strip():
                            return down
                    except Exception:
                        pass
            return line_no

        anchor_index = getattr(owner, "_error_focus_index", None) or f"{line}.0"
        try:
            anchor_line = int(str(anchor_index).split(".")[0])
        except Exception:
            anchor_line = int(line)
        note_text = str(getattr(owner, "_last_error_highlight_note", "") or "")
        preserve_blank_anchor = False
        try:
            if note_text.endswith("_eof") and not owner._line_text(anchor_line).strip():
                preserve_blank_anchor = True
        except Exception:
            preserve_blank_anchor = False
        if not preserve_blank_anchor:
            anchor_line = _nearest_non_empty_line(anchor_line)
        token_bbox = owner.text.bbox(anchor_index) or owner.text.bbox(f"{anchor_line}.0")
        line_bbox = owner.text.dlineinfo(f"{anchor_line}.0")
        if preserve_blank_anchor and not token_bbox and not line_bbox:
            prev_line = owner._closest_non_empty_line_before(anchor_line)
            if prev_line:
                anchor_line = prev_line
                anchor_index = owner.text.index(f"{anchor_line}.0 lineend")
                token_bbox = owner.text.bbox(anchor_index) or owner.text.bbox(f"{anchor_line}.0")
                line_bbox = owner.text.dlineinfo(f"{anchor_line}.0")
        if not line_bbox and not token_bbox:
            return
        if token_bbox:
            x = token_bbox[0]
        elif line_bbox:
            x = line_bbox[0]
        else:
            x = 0
        if line_bbox:
            y = line_bbox[1]
            h = line_bbox[3]
        elif token_bbox:
            y = token_bbox[1]
            h = token_bbox[3]
        else:
            return
        text_w = owner.text.winfo_width()
        text_h = owner.text.winfo_height()
        overlay = owner.error_overlay
        overlay.update_idletasks()
        ow = overlay.winfo_width()
        oh = overlay.winfo_height()

        is_warning_overlay = str(getattr(owner, "_last_error_overlay_title", "") or "").strip().lower() == "warning"
        gap = 2 if is_warning_overlay else 6
        try:
            anchor_font = tkfont.Font(font=owner.text.cget("font"))
            tab_shift_x = int(anchor_font.measure("    "))
            line_px = int(anchor_font.metrics("linespace"))
        except Exception:
            tab_shift_x = 28
            line_px = 16
        if is_warning_overlay:
            # Keep warning cards close to the edited highlighted key/token.
            tab_shift_x = max(4, min(16, int(anchor_font.measure(" ")))) if 'anchor_font' in locals() else 6
            nudge_y = max(0, min(6, int(round(max(10, line_px) * 0.15))))
            nx = int(x)
        else:
            tab_shift_x = max(18, min(72, tab_shift_x))
            nudge_y = max(6, min(20, int(round(max(10, line_px) * 0.45))))
            nx = _first_content_x(anchor_line, x)
        below_y = y + h + gap
        above_y = y - oh - gap
        can_place_below = (below_y + oh) <= (text_h - gap)
        can_place_above = above_y >= gap
        if can_place_below:
            ny = below_y + nudge_y
            placed_side = "below"
        elif can_place_above:
            ny = above_y - nudge_y
            placed_side = "above"
        else:
            space_below = max(0, text_h - (y + h))
            space_above = max(0, y)
            prefer_below = space_below >= space_above
            placed_side = "below" if prefer_below else "above"
            ny = (below_y + nudge_y) if prefer_below else (above_y - nudge_y)
            max_y = max(gap, text_h - oh - gap)
            ny = max(gap, min(max_y, ny))
        nx = nx + tab_shift_x
        if nx + ow > text_w:
            nx = max(text_w - ow - gap, 0)
        if nx < gap:
            nx = gap
        if placed_side == "above" and ny < gap:
            ny = gap
        elif placed_side == "below":
            max_y = max(gap, text_h - oh - gap)
            if ny > max_y:
                ny = max_y

        overlay.place_configure(x=nx, y=ny)
    except Exception:
        return
