"""UI factory helpers extracted from JsonEditor widget builders."""

from __future__ import annotations

from typing import Any

from core.domain_impl.ui import color_utility_service
from core.domain_impl.ui import theme_service


def preferred_mono_family(
    owner: Any,
    *,
    tkfont_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> str:
    """Resolve and cache the preferred monospace family."""
    current = getattr(owner, "_mono_family", None)
    if current:
        return str(current)
    preferred = [
        "JetBrains Mono",
        "Cascadia Code",
        "Cascadia Mono",
        "Consolas",
        "Courier New",
    ]
    try:
        families = {name.lower(): name for name in tkfont_module.families(owner.root)}
        for name in preferred:
            hit = families.get(name.lower())
            if hit:
                owner._mono_family = hit
                return str(owner._mono_family)
    except expected_errors:
        pass
    owner._mono_family = "Consolas"
    return str(owner._mono_family)


def resolve_font_family(
    owner: Any,
    preferred_families: Any,
    fallback: Any,
    *,
    tkfont_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> str:
    """Resolve preferred family names against available OS font families."""
    families = getattr(owner, "_font_family_lookup_cache", None)
    if families is None:
        families = {}
        try:
            families = {name.lower(): name for name in tkfont_module.families(owner.root)}
        except expected_errors:
            families = {}
        owner._font_family_lookup_cache = families
    try:
        for family in preferred_families:
            hit = families.get(str(family).lower())
            if hit:
                return str(hit)
    except expected_errors:
        pass
    return str(fallback)


def hex_to_colorref(hex_color: Any) -> int | None:
    """Convert #RRGGBB into Windows COLORREF integer."""
    return color_utility_service.hex_to_colorref(hex_color)


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
    if variant == "GLITCH":
        # GLITCH must always render a deterministic native stepper so startup
        # and theme-switch flows keep black fill + green frame styling.
        owner._make_siindbad_font_stepper(parent).pack(side="left")
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


def editor_mode_tab_photo(
    owner: Any,
    *,
    active: Any = False,
    importlib_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> Any:
    theme_variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    tab_w = 70
    tab_h = 26
    signature = (theme_variant, bool(active), "e1_clean_v4", tab_w, tab_h)
    cache = getattr(owner, "_editor_mode_tab_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._editor_mode_tab_cache = cache
    cached = cache.get(signature)
    if cached is not None:
        return cached
    try:
        image_module = importlib_module.import_module("PIL.Image")
        draw_module = importlib_module.import_module("PIL.ImageDraw")
        scale = 4
        w = tab_w * scale
        h = tab_h * scale
        radius = 8 * scale
        canvas = image_module.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = draw_module.Draw(canvas)
        palette = theme_service.editor_mode_tab_palette(theme_variant, active=bool(active))
        fill = palette["fill"]
        edge = palette["edge"]
        draw.rounded_rectangle(
            (0, 0, w - 1, h - 1),
            radius=radius,
            fill=fill,
            outline=edge,
            width=max(1, scale - 2),
        )
        draw.rectangle((0, 0, w - 1, max(1, radius // 3)), fill=fill)
        small = canvas.resize((tab_w, tab_h), image_module.LANCZOS)
        photo = owner._pil_to_photo(small)
    except expected_errors:
        photo = None
    owner._bounded_cache_put(cache, signature, photo, max_items=16)
    return photo


def update_editor_mode_controls(
    owner: Any,
    *,
    tk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    host = getattr(owner, "_editor_mode_host", None)
    parent = getattr(owner, "_editor_mode_parent", None)
    if host is None or parent is None:
        return
    try:
        if not (host.winfo_exists() and parent.winfo_exists()):
            return
    except expected_errors:
        return
    theme = getattr(owner, "_theme", {})
    try:
        host.configure(bg=theme.get("panel", "#161b24"))
    except expected_errors:
        pass
    try:
        host.place(relx=1.0, y=0, x=-16, anchor="ne")
    except expected_errors:
        pass
    active_mode = str(getattr(owner, "_editor_mode", "JSON")).upper()
    text_palette = theme_service.editor_mode_text_palette(
        str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    )
    for mode, label in dict(getattr(owner, "_editor_mode_labels", {}) or {}).items():
        try:
            if not label.winfo_exists():
                continue
            is_active = mode == active_mode
            tab_photo = owner._editor_mode_tab_photo(active=is_active)
            fg = text_palette["active_fg"] if is_active else text_palette["inactive_fg"]
            label.configure(
                image=tab_photo if tab_photo is not None else "",
                fg=fg,
                bg=theme.get("panel", "#161b24"),
                font=(owner._credit_name_font()[0], 8, "bold"),
                text=mode,
            )
        except (expected_errors + (TypeError, ValueError)):
            continue


def update_header_variant_controls(
    owner: Any,
    *,
    tk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    theme = getattr(owner, "_theme", {})
    host = getattr(owner, "_header_variant_host", None)
    host_in_footer = bool(getattr(owner, "_header_variant_is_footer", False))
    host_bg = theme.get("credit_bg", "#0b1118") if host_in_footer else theme.get("bg", "#0f131a")
    if host and host.winfo_exists():
        try:
            host.configure(bg=host_bg)
        except expected_errors:
            pass
    active_variant = str(getattr(owner, "_header_variant", "A")).upper()
    theme_variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    label_fg = theme.get("credit_label_fg", "#b5cade")
    for child in (host.winfo_children() if host and host.winfo_exists() else ()):
        if child in getattr(owner, "_header_variant_labels", {}).values():
            continue
        if isinstance(child, tk_module.Label):
            try:
                child.configure(bg=host_bg, fg=label_fg)
            except expected_errors:
                pass
    for variant, chip in dict(getattr(owner, "_header_variant_labels", {}) or {}).items():
        colors = theme_service.header_variant_chip_palette(theme_variant, active=variant == active_variant)
        try:
            chip.configure(
                bg=colors["bg"],
                fg=colors["fg"],
                highlightbackground=colors["border"],
                highlightcolor=colors["border"],
            )
        except expected_errors:
            continue


def update_app_theme_controls(
    owner: Any,
    *,
    tk_module: Any,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    active = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    spec = owner._footer_visual_spec()
    use_soft_active = owner._footer_style_variant() == "B"
    for variant, label in dict(getattr(owner, "_app_theme_labels", {}) or {}).items():
        colors = owner._theme_chip_palette(variant)
        is_active = variant == active
        active_bg = colors["bg"]
        active_fg = colors["fg"] if (use_soft_active or not is_active) else "#ffffff"
        label.configure(
            bg=active_bg,
            fg=active_fg,
            highlightbackground=colors["border"],
            highlightcolor=colors["border"],
            font=spec["chip_font"],
            padx=spec["theme_chip_padx"],
            pady=spec["theme_chip_pady"],
        )
    host = getattr(owner, "_theme_selector_host", None)
    if host is None or not host.winfo_exists():
        return
    for child in host.winfo_children():
        if not isinstance(child, tk_module.Label):
            continue
        if child in getattr(owner, "_app_theme_labels", {}).values():
            continue
        if child in getattr(owner, "_toolbar_style_labels", {}).values():
            continue
        if child in getattr(owner, "_tree_style_labels", {}).values():
            continue
        if child == getattr(owner, "_toolbar_style_title_label", None):
            continue
        if child == getattr(owner, "_tree_style_title_label", None):
            continue
        try:
            child.configure(
                bg=getattr(owner, "_theme", {}).get("credit_bg", "#0b1118"),
                fg=getattr(owner, "_theme", {}).get("credit_label_fg", "#b5cade"),
                font=spec["label_font"],
            )
        except expected_errors:
            continue


def update_toolbar_style_controls(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...],
) -> None:
    if not bool(getattr(owner, "_show_toolbar_variant_controls", False)):
        return
    if not getattr(owner, "_toolbar_style_labels", None):
        return
    active_theme = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    focus = owner._siindbad_effective_style()
    palette = theme_service.toolbar_style_variant_palette(active_theme)
    title = getattr(owner, "_toolbar_style_title_label", None)
    if title is not None and title.winfo_exists():
        try:
            title.configure(
                bg=getattr(owner, "_theme", {}).get("credit_bg", "#0b1118"),
                fg=getattr(owner, "_theme", {}).get("credit_label_fg", "#b5cade"),
            )
        except expected_errors:
            pass
    for variant, label in dict(getattr(owner, "_toolbar_style_labels", {}) or {}).items():
        is_active = variant == focus
        label.configure(
            bg=palette["active_bg"] if is_active else palette["inactive_bg"],
            fg=palette["active_fg"] if is_active else palette["inactive_fg"],
            highlightbackground=palette["active_border"] if is_active else palette["inactive_border"],
            highlightcolor=palette["active_border"] if is_active else palette["inactive_border"],
            cursor="hand2",
        )
