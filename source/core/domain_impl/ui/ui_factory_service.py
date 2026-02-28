"""UI factory helpers extracted from JsonEditor widget builders."""

from __future__ import annotations

from typing import Any


def apply_styles(
    owner: Any,
    tree: Any,
    *,
    ttk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
    style: Any = None,
    panel: Any = None,
    tree_fg: Any = None,
    select_bg: Any = None,
    select_fg: Any = None,
) -> None:
    """Apply Treeview style, indicator layout, and level-font tags."""
    if tree is None:
        return
    if style is None:
        try:
            style = ttk_module.Style(owner.root)
        except expected_errors:
            return

    theme = getattr(owner, "_theme", {}) or {}
    panel_bg = panel or theme.get("panel", "#161b24")
    fg = tree_fg if tree_fg is not None else theme.get("tree_fg", theme.get("fg", "#e6e6e6"))
    selected_bg = select_bg or theme.get("select_bg", "#2f3a4d")
    selected_fg = select_fg or theme.get("select_fg", "#ffffff")
    profile = owner._tree_font_profile()
    tree_font_family = owner._tree_font_family(profile["is_variant_b"])
    tree_sub_font_family = owner._tree_sub_font_family()
    tree_font = (
        (tree_font_family, profile["main_size"], profile["main_weight"])
        if profile["main_weight"] != "normal"
        else (tree_font_family, profile["main_size"])
    )
    style.configure(
        "Treeview",
        background=panel_bg,
        fieldbackground=panel_bg,
        foreground=fg,
        font=tree_font,
        rowheight=profile["row_height"],
        padding=(0, int(getattr(owner, "_tree_content_top_gap", 2) or 0), 0, 0),
        bordercolor=panel_bg,
        lightcolor=panel_bg,
        darkcolor=panel_bg,
    )
    _apply_tree_indicator_layout(owner, style, expected_errors=expected_errors)
    style.map(
        "Treeview",
        background=[("selected", selected_bg)],
        foreground=[("selected", selected_fg)],
    )
    _configure_tree_level_fonts(
        owner,
        tree,
        expected_errors=expected_errors,
        tree_font_family=tree_font_family,
        tree_sub_font_family=tree_sub_font_family,
        main_size=profile["main_size"],
        sub_size=profile["sub_size"],
        main_weight=profile["main_weight"],
        sub_weight=profile["sub_weight"],
    )


def _configure_tree_level_fonts(
    owner: Any,
    tree: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
    tree_font_family: Any = None,
    tree_sub_font_family: Any = None,
    main_size: Any = None,
    sub_size: Any = None,
    main_weight: Any = None,
    sub_weight: Any = None,
) -> None:
    if tree is None:
        return
    try:
        if not tree.winfo_exists():
            return
    except expected_errors:
        return
    profile = owner._tree_font_profile()
    family_main = tree_font_family or owner._tree_font_family(profile["is_variant_b"])
    family_sub = tree_sub_font_family or owner._tree_sub_font_family()
    use_main_size = profile["main_size"] if main_size is None else int(main_size)
    use_sub_size = profile["sub_size"] if sub_size is None else int(sub_size)
    use_main_weight = profile["main_weight"] if main_weight is None else str(main_weight)
    use_sub_weight = profile["sub_weight"] if sub_weight is None else str(sub_weight)
    main_font = (
        (family_main, use_main_size, use_main_weight)
        if use_main_weight != "normal"
        else (family_main, use_main_size)
    )
    sub_font = (
        (family_sub, use_sub_size, use_sub_weight)
        if use_sub_weight != "normal"
        else (family_sub, use_sub_size)
    )
    try:
        tree.tag_configure("tree-main-level", font=main_font)
        tree.tag_configure("tree-sub-level", font=sub_font)
    except expected_errors:
        pass


def _apply_tree_indicator_layout(
    owner: Any,
    style: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Hide native indicator in TREE B so composite icon pack provides arrows."""
    try:
        if getattr(owner, "_tree_item_layout_default", None) is None:
            owner._tree_item_layout_default = style.layout("Treeview.Item")
    except expected_errors:
        return

    variant = str(getattr(owner, "_tree_style_variant", "B")).upper()
    if variant == "B":
        if getattr(owner, "_tree_item_layout_no_indicator", None) is None:
            owner._tree_item_layout_no_indicator = [
                (
                    "Treeitem.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            ("Treeitem.image", {"side": "left", "sticky": ""}),
                            (
                                "Treeitem.focus",
                                {
                                    "side": "left",
                                    "sticky": "",
                                    "children": [("Treeitem.text", {"side": "left", "sticky": ""})],
                                },
                            ),
                        ],
                    },
                )
            ]
        try:
            style.layout("Treeview.Item", owner._tree_item_layout_no_indicator)
        except expected_errors:
            pass
        return
    try:
        if owner._tree_item_layout_default:
            style.layout("Treeview.Item", owner._tree_item_layout_default)
    except expected_errors:
        pass


def build_font_control(
    owner: Any,
    parent: Any,
    *,
    tk_module: Any,
    ttk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Render font control row for active theme variant."""
    if parent is None or not parent.winfo_exists():
        return
    for child in parent.winfo_children():
        child.destroy()

    owner._font_stepper_label = None
    owner._font_size_value_label = None
    owner.font_size_combo = None
    owner.font_size_var = None

    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    style = owner._siindbad_effective_style()
    if variant == "SIINDBAD" and style == "B":
        # SIINDBAD Variant-B uses generated font sprite + hitboxes.
        owner._toolbar_button_images = {}
        if not owner._load_siindbad_b_font_sprite_image():
            owner._load_toolbar_button_images_from_assets(
                style="B",
                mapping={"font": (("font2b", "font2", "font"), 146, 34, True)},
            )
        owner._make_font_stepper(parent).pack(side="left")
        return
    if variant == "SIINDBAD":
        owner._make_siindbad_font_stepper(parent).pack(side="left")
        return
    if variant == "KAMUE":
        theme = getattr(owner, "_theme", {})
        bg = theme.get("bg", "#0f131a")
        panel = theme.get("panel", "#161b24")
        fg = theme.get("fg", "#e6e6e6")
        # Keep the previous balanced look, but slightly shaded darker.
        border = theme.get("find_border", "#cfb5ee")
        inner_border = theme.get("logo_border_outer", "#6b37b6")
        label_family = owner._resolve_font_family(
            ["Segoe UI Semibold", "Segoe UI Bold", "Segoe UI"],
            owner._preferred_mono_family(),
        )

        host = tk_module.Frame(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
            width=124,
            height=owner._siindbad_b_button_height("find", default_height=33),
        )
        host.pack(side="left")
        host.pack_propagate(False)
        # Add a subtle dark tint under the border to shade it without over-purple shift.
        shade_layer = tk_module.Frame(host, bg="#0b0615", bd=0, highlightthickness=0)
        shade_layer.place(x=0, y=0, relwidth=1, relheight=1)

        inner = tk_module.Frame(
            host,
            bg=panel,
            bd=0,
            highlightthickness=1,
            highlightbackground=inner_border,
            highlightcolor=inner_border,
        )
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        controls = tk_module.Frame(inner, bg=panel, bd=0, highlightthickness=0)
        controls.place(relx=0.5, rely=0.5, anchor="center")

        label = tk_module.Label(
            controls,
            text="FONT",
            bg=panel,
            fg=fg,
            font=(label_family, 10, "bold"),
            bd=0,
            highlightthickness=0,
        )
        label.pack(side="left", padx=(1, 3))

        values = tuple(str(i) for i in range(6, 33))
        owner.font_size_var = tk_module.StringVar(value=str(int(owner._font_size)))
        combo_style = "Kamue.FontSize.TCombobox"
        number_font = owner._font_dropdown_number_font()
        style_obj = ttk_module.Style(owner.root)
        style_obj.configure(
            combo_style,
            fieldbackground=panel,
            foreground=fg,
            background=panel,
            bordercolor=inner_border,
            arrowcolor=fg,
            lightcolor=panel,
            darkcolor=panel,
            padding=1,
            font=number_font,
        )
        style_obj.map(
            combo_style,
            fieldbackground=[("readonly", panel), ("active", panel)],
            foreground=[("readonly", fg), ("active", fg)],
            selectforeground=[("readonly", fg)],
            selectbackground=[("readonly", theme.get("select_bg", "#2f3a4d"))],
            arrowcolor=[("readonly", fg), ("active", fg)],
            bordercolor=[("readonly", inner_border), ("active", border)],
        )
        combo = ttk_module.Combobox(
            controls,
            textvariable=owner.font_size_var,
            values=values,
            state="readonly",
            width=5,
            style=combo_style,
            font=number_font,
            justify="center",
        )
        combo.pack(side="left", padx=(0, 1), pady=0)
        combo.bind("<<ComboboxSelected>>", owner._on_font_size_selected)
        select_bg = theme.get("select_bg", "#2f3a4d")
        select_fg = theme.get("select_fg", "#ffffff")
        owner._style_combobox_popdown(
            combo,
            bg=panel,
            fg=fg,
            select_bg=select_bg,
            select_fg=select_fg,
            font=number_font,
        )
        combo.bind(
            "<Button-1>",
            lambda _evt, cb=combo, bg_color=panel, fg_color=fg, sb=select_bg, sf=select_fg, nf=number_font:
            owner._style_combobox_popdown(cb, bg=bg_color, fg=fg_color, select_bg=sb, select_fg=sf, font=nf),
            add="+",
        )
        owner.font_size_combo = combo
        return

    owner._make_font_stepper(parent).pack(side="left")


def build_bug_report_chip(
    owner: Any,
    parent: Any,
    *,
    tk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Render footer bug-report chip block."""
    owner._bug_report_host = parent
    theme = getattr(owner, "_theme", {})
    spec = owner._footer_visual_spec()
    chip_colors = owner._bug_chip_palette(getattr(owner, "_app_theme_variant", "SIINDBAD"))
    title = tk_module.Label(
        parent,
        text="REPORT :",
        bg=theme.get("credit_bg", "#0b1118"),
        fg=theme.get("credit_label_fg", "#b5cade"),
        font=spec["label_font"],
        bd=0,
        highlightthickness=0,
    )
    title.pack(side="left", padx=(0, spec["label_gap"]))
    owner._bug_report_label = title
    chip = tk_module.Frame(
        parent,
        bg=chip_colors["bg"],
        bd=0,
        highlightthickness=1,
        highlightbackground=chip_colors["border"],
        highlightcolor=chip_colors["border"],
    )
    icon_label = tk_module.Label(
        chip,
        text="",
        bg=chip_colors["bg"],
        fg=chip_colors["fg"],
        bd=0,
        highlightthickness=0,
        cursor="hand2",
    )
    icon_label.pack(side="left", padx=(spec["chip_icon_left_pad"], spec["chip_icon_gap"]), pady=0)
    text_label = tk_module.Label(
        chip,
        text="SUBMIT A BUG",
        bg=chip_colors["bg"],
        fg=chip_colors["fg"],
        font=spec["chip_font"],
        bd=0,
        highlightthickness=0,
        cursor="hand2",
    )
    text_label.pack(side="left", padx=(0, spec["chip_text_right_pad"]), pady=0)
    for widget in (chip, icon_label, text_label):
        widget.bind("<Button-1>", lambda _event: owner._open_bug_report_dialog())
        try:
            widget.configure(cursor="hand2")
        except expected_errors:
            pass
    chip.pack(side="left")
    owner._bug_report_chip = chip
    owner._bug_report_chip_icon_label = icon_label
    owner._bug_report_chip_text_label = text_label
    owner._sync_bug_report_chip_colors()


def show_bug_submit_splash(
    owner: Any,
    message: Any = "BUG REPORT SUBMITTED",
    duration_ms: Any = 1600,
    *,
    tk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    """Show temporary bug-submit success splash banner."""
    owner._hide_bug_submit_splash()
    root = getattr(owner, "root", None)
    if root is None:
        return
    theme = getattr(owner, "_theme", {}) or {}
    variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    if variant == "KAMUE":
        bg = "#12091d"
        fg = theme.get("title_bar_fg", "#eee8ff")
        border = "#e0b8ff"
    else:
        bg = "#0f1f2d"
        fg = theme.get("title_bar_fg", "#e6f6ff")
        border = "#b5f3ff"
    try:
        root.update_idletasks()
        splash = tk_module.Frame(
            root,
            bg=bg,
            bd=0,
            highlightthickness=2,
            highlightbackground=border,
            highlightcolor=border,
        )
        label = tk_module.Label(
            splash,
            text=str(message or "BUG REPORT SUBMITTED"),
            bg=bg,
            fg=fg,
            font=(owner._preferred_mono_family(), 12, "bold"),
            padx=24,
            pady=12,
        )
        label.pack(fill="both", expand=True)
        splash.update_idletasks()
        splash_w = max(int(splash.winfo_reqwidth()), 300)
        splash_h = max(int(splash.winfo_reqheight()), 56)
        root_w = max(int(root.winfo_width()), 1)
        root_h = max(int(root.winfo_height()), 1)
        pos_x = max(int((root_w - splash_w) / 2), 8)
        pos_y = max(int((root_h - splash_h) / 2), 8)
        splash.place(x=pos_x, y=pos_y, width=splash_w, height=splash_h)
        splash.lift()
        owner._bug_submit_splash = splash
        owner._bug_submit_splash_after_id = root.after(
            max(700, int(duration_ms)),
            owner._hide_bug_submit_splash,
        )
    except expected_errors:
        owner._hide_bug_submit_splash()
