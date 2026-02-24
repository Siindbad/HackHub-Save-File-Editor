"""Text context menu build/style/show helpers."""

from typing import Any


def build_text_context_menu(owner: Any, *, tk: Any, expected_errors: Any) -> None:
    owner._destroy_text_context_menu()
    try:
        scale = owner._text_context_menu_scale()

        def _s(value: float, min_value: int = 1) -> int:
            return max(min_value, int(round(float(value) * scale)))

        popup = tk.Toplevel(owner.root)
        popup.withdraw()
        popup.overrideredirect(True)
        try:
            popup.attributes("-topmost", True)
        except expected_errors:
            pass

        anchor = tk.Frame(popup, bd=0, highlightthickness=1)
        anchor.pack(fill="both", expand=True)
        frame = tk.Frame(anchor, bd=0, highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        panel = tk.Frame(frame, bd=0, highlightthickness=1)
        panel.pack(fill="both", expand=True, padx=_s(3), pady=(_s(3), _s(2)))
        body = tk.Frame(panel, bd=0, highlightthickness=0)
        body.pack(fill="both", expand=True, padx=_s(2), pady=(_s(2), _s(1)))

        items = {}
        widget_actions = {}
        menu_layout = (
            ("undo", "Undo", "Ctrl+Z"),
            ("redo", "Redo", "Ctrl+Y"),
            ("copy", "Copy", "Ctrl+C"),
            ("paste", "Paste", "Ctrl+V"),
            ("autofix", "Auto-Fix", ""),
        )
        total_items = len(menu_layout)
        for item_idx, (action, label, shortcut) in enumerate(menu_layout):
            separator = None
            if action == "copy":
                separator = tk.Frame(body, bd=0, height=1)
                separator.pack(fill="x", padx=_s(7), pady=_s(5))
                owner._text_context_menu_separator = separator
            elif action == "autofix":
                separator = tk.Frame(body, bd=0, height=1)
                separator.pack(fill="x", padx=_s(7), pady=_s(5))
            row = tk.Frame(body, bd=0, highlightthickness=1, cursor="hand2")
            row_bottom = _s(0 if item_idx == (total_items - 1) else 1)
            row.pack(fill="x", padx=_s(2), pady=(_s(1), row_bottom))
            title = tk.Label(row, text=str(label).upper(), anchor="w")
            shortcut_label = tk.Label(row, text=shortcut, anchor="e")
            if action == "autofix":
                title.configure(anchor="center", justify="center")
                title.grid(
                    row=0,
                    column=0,
                    columnspan=2,
                    padx=_s(6),
                    pady=_s(4),
                    sticky="nsew",
                )
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=1)
            else:
                title.grid(row=0, column=0, padx=(_s(11), _s(10)), pady=_s(4), sticky="w")
                shortcut_label.grid(row=0, column=1, padx=(0, _s(7)), pady=_s(4), sticky="e")
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)
            for widget in (row, title, shortcut_label):
                widget_actions[widget] = action
                widget.bind("<Motion>", owner._on_text_context_menu_motion, add="+")
            for widget in (title, shortcut_label):
                widget.bind(
                    "<Button-1>",
                    lambda _evt, key=action: owner._on_text_context_menu_click(key),
                    add="+",
                )
            row.bind(
                "<Button-1>",
                lambda _evt, key=action: owner._on_text_context_menu_click(key),
                add="+",
            )
            items[action] = {
                "row": row,
                "title": title,
                "shortcut": shortcut_label,
            }
            if separator is not None and action in ("copy", "autofix"):
                try:
                    owner._text_context_menu_separators.append(separator)
                except expected_errors:
                    pass

        popup.bind("<Escape>", owner._on_text_context_menu_escape, add="+")
        popup.bind("<Button-1>", lambda _evt: "break", add="+")
        popup.bind("<Motion>", owner._on_text_context_menu_motion, add="+")

        owner._text_context_menu = popup
        owner._text_context_menu_anchor = anchor
        owner._text_context_menu_frame = frame
        owner._text_context_menu_panel = panel
        owner._text_context_menu_body = body
        owner._text_context_menu_items = items
        owner._text_context_menu_widget_actions = widget_actions
        owner._text_context_menu_item_states = {key: True for key in items}
        owner._text_context_menu_hover_action = None
        owner._style_text_context_menu()
    except expected_errors:
        owner._destroy_text_context_menu()


def style_text_context_menu(owner: Any, *, expected_errors: Any) -> None:
    popup = getattr(owner, "_text_context_menu", None)
    if popup is None:
        return
    try:
        if not popup.winfo_exists():
            return
    except expected_errors:
        return

    palette = owner._text_context_menu_palette()
    scale = owner._text_context_menu_scale()
    title_size = max(8, int(round(11 * scale)))
    small_size = max(7, int(round(9 * scale)))
    font_family = owner._resolve_font_family(
        ["Tektur", "Oxanium", "Orbitron", "Rajdhani", "Share Tech Mono", "Segoe UI Semibold", "Segoe UI"],
        owner._preferred_mono_family(),
    )
    try:
        popup.configure(bg=palette["frame_bg"])
    except expected_errors:
        pass

    anchor = getattr(owner, "_text_context_menu_anchor", None)
    frame = getattr(owner, "_text_context_menu_frame", None)
    panel = getattr(owner, "_text_context_menu_panel", None)
    body = getattr(owner, "_text_context_menu_body", None)
    separator = getattr(owner, "_text_context_menu_separator", None)
    separators = list(getattr(owner, "_text_context_menu_separators", []) or [])

    if anchor is not None:
        try:
            anchor.configure(
                bg=palette["bg"],
                highlightbackground=palette["border"],
                highlightcolor=palette["border"],
            )
        except expected_errors:
            pass
    if frame is not None:
        try:
            frame.configure(
                bg=palette["bg"],
                highlightbackground=palette["inset_border"],
                highlightcolor=palette["inset_border"],
            )
        except expected_errors:
            pass
    if panel is not None:
        try:
            panel.configure(
                bg=palette["panel_bg"],
                highlightbackground=palette["panel_border"],
                highlightcolor=palette["panel_border"],
            )
        except expected_errors:
            pass
    if body is not None:
        try:
            body.configure(bg=palette["bg"])
        except expected_errors:
            pass
    if separator is not None:
        try:
            separator.configure(bg=palette["separator"])
        except expected_errors:
            pass
    for sep in separators:
        try:
            if sep is not None and sep.winfo_exists():
                sep.configure(bg=palette["separator"])
        except expected_errors:
            pass

    owner._style_text_context_menu_rows(
        palette=palette,
        font_family=font_family,
        shortcut_font_family=owner._preferred_mono_family(),
        title_size=title_size,
        small_size=small_size,
        apply_fonts=True,
    )
    owner._text_context_menu_row_style = {
        "palette": palette,
        "font_family": font_family,
        "shortcut_font_family": owner._preferred_mono_family(),
        "title_size": title_size,
        "small_size": small_size,
    }


def style_text_context_menu_row(
    owner: Any,
    action: Any,
    *,
    palette: Any = None,
    font_family: Any = None,
    shortcut_font_family: Any = None,
    title_size: Any = None,
    small_size: Any = None,
    apply_fonts: bool = False,
    expected_errors: Any,
) -> None:
    parts = getattr(owner, "_text_context_menu_items", {}).get(action)
    if not parts:
        return
    cached = getattr(owner, "_text_context_menu_row_style", None)
    if palette is None and isinstance(cached, dict):
        palette = cached.get("palette")
    if font_family is None and isinstance(cached, dict):
        font_family = cached.get("font_family")
    if shortcut_font_family is None and isinstance(cached, dict):
        shortcut_font_family = cached.get("shortcut_font_family")
    if title_size is None and isinstance(cached, dict):
        title_size = cached.get("title_size")
    if small_size is None and isinstance(cached, dict):
        small_size = cached.get("small_size")
    if palette is None:
        palette = owner._text_context_menu_palette()
    if font_family is None:
        font_family = owner._preferred_mono_family()
    if shortcut_font_family is None:
        shortcut_font_family = owner._preferred_mono_family()
    scale = owner._text_context_menu_scale()
    if title_size is None:
        title_size = max(8, int(round(11 * scale)))
    if small_size is None:
        small_size = max(7, int(round(9 * scale)))

    row = parts["row"]
    title = parts["title"]
    shortcut = parts["shortcut"]
    enabled = bool(getattr(owner, "_text_context_menu_item_states", {}).get(action, True))
    hovered = bool(action == getattr(owner, "_text_context_menu_hover_action", None) and enabled)
    if hovered:
        row_bg = palette["active_bg"]
        row_fg = palette["active_fg"]
        row_border = palette["active_border"]
        shortcut_fg = palette["active_fg"]
    else:
        row_bg = palette["bg"]
        row_fg = palette["fg"] if enabled else palette["disabled_fg"]
        row_border = palette["inset_border"]
        shortcut_fg = palette["shortcut_fg"] if enabled else palette["disabled_fg"]
    cursor = "hand2" if enabled else "arrow"
    try:
        row.configure(
            bg=row_bg,
            highlightbackground=row_border,
            highlightcolor=row_border,
            cursor=cursor,
        )
    except expected_errors:
        pass
    for widget in (title, shortcut):
        try:
            widget.configure(bg=row_bg)
        except expected_errors:
            pass
    try:
        if action == "autofix":
            title_kwargs = {
                "fg": row_fg,
                "cursor": cursor,
                "anchor": "center",
                "justify": "center",
            }
        else:
            title_kwargs = {
                "fg": row_fg,
                "cursor": cursor,
            }
        if apply_fonts:
            title_kwargs["font"] = (font_family, title_size, "bold")
        title.configure(**title_kwargs)
    except expected_errors:
        pass
    try:
        shortcut_kwargs = {
            "fg": shortcut_fg,
            "cursor": cursor,
        }
        if apply_fonts:
            shortcut_kwargs["font"] = (shortcut_font_family, small_size)
        shortcut.configure(**shortcut_kwargs)
    except expected_errors:
        pass


def show_text_context_menu(owner: Any, event: Any, *, expected_errors: Any) -> str:
    owner._input_context_target_widget = None
    owner._input_context_target_allow_paste = False
    popup = getattr(owner, "_text_context_menu", None)
    if popup is None:
        owner._build_text_context_menu()
        popup = getattr(owner, "_text_context_menu", None)
    if popup is None:
        return "break"
    try:
        owner.text.focus_set()
    except expected_errors:
        pass

    anchor_index = "insert"
    if event is not None and hasattr(event, "x") and hasattr(event, "y"):
        try:
            idx = owner.text.index(f"@{event.x},{event.y}")
            anchor_index = idx
            if not owner._has_text_selection():
                owner.text.mark_set("insert", idx)
        except expected_errors:
            pass

    owner._set_text_context_menu_item_state("undo", owner._text_can_undo())
    owner._set_text_context_menu_item_state("redo", owner._text_can_redo())
    owner._set_text_context_menu_item_state("copy", owner._has_text_selection())
    owner._set_text_context_menu_item_state("paste", owner._clipboard_has_text())
    owner._set_text_context_menu_item_state("autofix", owner._can_context_autofix())
    owner._text_context_menu_hover_action = None

    menu_req_h = 0
    vroot_top = 2
    vroot_bottom = 0
    text_bottom = None
    root_bottom = None
    try:
        popup.update_idletasks()
        menu_req_h = max(1, int(popup.winfo_reqheight()))
        vroot_y = int(owner.root.winfo_vrooty())
        vroot_h = max(menu_req_h + 2, int(owner.root.winfo_vrootheight()))
        vroot_top = vroot_y + 2
        vroot_bottom = vroot_y + vroot_h
        try:
            text_bottom = int(owner.text.winfo_rooty()) + int(owner.text.winfo_height())
        except expected_errors:
            text_bottom = None
        try:
            root_bottom = int(owner.root.winfo_rooty()) + int(owner.root.winfo_height())
        except expected_errors:
            root_bottom = None
    except expected_errors:
        menu_req_h = 0
        vroot_top = 2
        vroot_bottom = 0
        text_bottom = None
        root_bottom = None

    def _resolve_menu_y(preferred_y: Any, anchor_top: Any = None) -> Any:
        try:
            y = int(preferred_y)
        except expected_errors:
            return preferred_y
        if menu_req_h <= 0:
            return y
        container_bottom = int(vroot_bottom)
        if container_bottom <= 0:
            try:
                container_bottom = max(menu_req_h + 2, int(owner.root.winfo_screenheight()))
            except expected_errors:
                container_bottom = menu_req_h + 2
        try:
            if text_bottom is not None and int(text_bottom) > 0:
                container_bottom = min(container_bottom, int(text_bottom))
        except expected_errors:
            pass
        try:
            if root_bottom is not None and int(root_bottom) > 0:
                container_bottom = min(container_bottom, int(root_bottom))
        except expected_errors:
            pass
        bottom_limit = container_bottom - menu_req_h - 2
        if y > bottom_limit and anchor_top is not None:
            try:
                above_y = int(anchor_top) - menu_req_h - 2
                if above_y >= int(vroot_top):
                    return above_y
            except expected_errors:
                pass
        if y > bottom_limit:
            y = max(int(vroot_top), bottom_limit)
        if y < int(vroot_top):
            y = int(vroot_top)
        return y

    popup_x = None
    popup_y = None
    if event is not None and hasattr(event, "x_root"):
        try:
            popup_x = int(event.x_root)
        except expected_errors:
            popup_x = None
    try:
        box = owner.text.bbox(anchor_index)
        if box:
            anchor_top = owner.text.winfo_rooty() + int(box[1])
            popup_y = _resolve_menu_y(anchor_top + int(box[3]) + 2, anchor_top=anchor_top)
            if popup_x is None:
                popup_x = owner.text.winfo_rootx() + int(box[0]) + 6
    except expected_errors:
        popup_y = None
    if popup_x is None or popup_y is None:
        try:
            box = owner.text.bbox("insert")
            if box:
                popup_x = owner.text.winfo_rootx() + int(box[0]) + 6
                anchor_top = owner.text.winfo_rooty() + int(box[1])
                popup_y = _resolve_menu_y(anchor_top + int(box[3]) + 2, anchor_top=anchor_top)
        except expected_errors:
            popup_x = None
            popup_y = None
    if (popup_x is None or popup_y is None) and event is not None and hasattr(event, "x_root") and hasattr(event, "y_root"):
        try:
            popup_x = int(event.x_root)
            popup_y = _resolve_menu_y(int(event.y_root), anchor_top=int(event.y_root))
        except expected_errors:
            popup_x = None
            popup_y = None
    if popup_x is None or popup_y is None:
        try:
            popup_x = owner.root.winfo_rootx() + 40
            popup_y = owner.root.winfo_rooty() + 40
        except expected_errors:
            return "break"

    owner._hide_text_context_menu()
    owner._text_context_menu_hover_action = None
    owner._show_text_context_menu_popup(popup_x, popup_y)
    return "break"
