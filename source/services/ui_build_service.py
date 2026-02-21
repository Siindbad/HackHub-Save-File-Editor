"""Main editor UI build service."""


# UI composition extraction: owner handles callbacks/state, this service
# builds and wires the major editor panels.
def build_ui(owner, tk, ttk):
    owner._apply_dark_theme()
    owner._set_window_icon()

    header = ttk.Frame(owner.root)
    header.pack(fill="x", padx=4, pady=(2, 0))
    owner._header_frame = header
    owner._update_logo_for_theme(force=True)

    top = ttk.Frame(owner.root)
    top.pack(fill="x", padx=4, pady=(2, 3))
    owner._toolbar_host = top
    owner._rebuild_toolbar(preserve_find_text=False)
    owner.status = None
    theme = getattr(owner, "_theme", {})
    separator = tk.Frame(
        owner.root,
        bg=theme.get("bg", "#0f131a"),
        bd=0,
        highlightthickness=1,
        highlightbackground=theme.get("logo_border_outer", "#349fc7"),
        highlightcolor=theme.get("logo_border_outer", "#349fc7"),
        height=2,
    )
    separator.pack(fill="x", padx=4, pady=(0, 1))
    separator.pack_propagate(False)
    separator_inner = tk.Frame(
        separator,
        bg=theme.get("bg", "#0f131a"),
        bd=0,
        highlightthickness=1,
        highlightbackground=theme.get("logo_border_inner", "#a9ddf0"),
        highlightcolor=theme.get("logo_border_inner", "#a9ddf0"),
    )
    separator_inner.pack(fill="both", expand=True, padx=0, pady=0)
    owner._body_top_separator = separator
    owner._body_top_separator_inner = separator_inner

    body = ttk.Panedwindow(owner.root, orient="horizontal")

    left = ttk.Frame(body)
    right = ttk.Frame(body)
    owner._editor_right_parent = right
    body.add(left, weight=1)
    body.add(right, weight=2)

    owner.tree = ttk.Treeview(left, show="tree")
    owner.tree.pack(fill="both", expand=True, side="left")
    try:
        tree_inset = 6 if str(getattr(owner, "_tree_style_variant", "B")).upper() == "B" else 0
        owner.tree.configure(padding=(tree_inset, 0, 0, 0))
    except Exception:
        pass
    scroll_style = getattr(owner, "_v_scrollbar_style", "Vertical.TScrollbar")
    tree_scroll = ttk.Scrollbar(
        left, orient="vertical", command=owner.tree.yview, style=scroll_style
    )
    tree_scroll.pack(fill="y", side="right")
    owner.tree.configure(yscrollcommand=tree_scroll.set)

    owner.tree.bind("<Button-1>", owner._on_tree_click_toggle, add="+")
    owner.tree.bind("<Double-1>", owner._on_tree_double_click_guard, add="+")
    owner.tree.bind("<<TreeviewOpen>>", owner.on_expand)
    owner.tree.bind("<<TreeviewClose>>", owner.on_collapse)
    owner.tree.bind("<<TreeviewSelect>>", owner.on_select)
    # Re-apply tree styling now that the widget exists so level tag fonts
    # (main/sub categories) are guaranteed to take effect on initial load.
    owner._apply_tree_style()

    # Enable built-in Tk text undo/redo support (Ctrl+Z / Ctrl+Y)
    owner.text = tk.Text(
        right,
        wrap="none",
        height=10,
        undo=True,
        autoseparators=True,
        maxundo=100,
        padx=6,
    )
    # Keep editor content below INPUT/JSON mode tabs anchored at pane top.
    editor_mode_top_inset = 24
    owner.text.pack(fill="both", expand=True, side="left", pady=(editor_mode_top_inset, 0))
    text_scroll = ttk.Scrollbar(
        right, orient="vertical", command=owner.text.yview, style=scroll_style
    )
    text_scroll.pack(fill="y", side="right", pady=(editor_mode_top_inset, 0))
    owner.text.configure(yscrollcommand=text_scroll.set)
    owner._text_scroll = text_scroll
    owner._build_input_mode_panel(right, scroll_style)
    owner._style_text_widget()
    owner._build_editor_mode_toggle(right)
    owner._refresh_editor_mode_view()
    owner._build_text_context_menu()
    owner.text.bind("<KeyPress>", owner._on_text_keypress, add="+")
    owner.text.bind("<KeyRelease>", owner._on_text_keyrelease, add="+")
    owner.text.bind("<Button-1>", owner._on_text_nav_attempt, add="+")
    owner.text.bind("<B1-Motion>", owner._on_text_nav_attempt, add="+")
    owner.text.bind("<ButtonRelease-1>", owner._on_text_nav_attempt, add="+")
    owner.text.bind("<Double-Button-1>", owner._on_text_nav_attempt, add="+")
    owner.text.bind("<Triple-Button-1>", owner._on_text_nav_attempt, add="+")
    owner.text.bind("<Button-3>", owner._show_text_context_menu, add="+")
    owner.text.bind("<Shift-F10>", owner._show_text_context_menu, add="+")
    owner.text.bind("<Menu>", owner._show_text_context_menu, add="+")
    owner.root.bind("<FocusOut>", owner._on_root_focus_out, add="+")
    owner.root.bind("<FocusIn>", owner._on_root_focus_in, add="+")
    owner.root.bind("<Configure>", owner._on_root_configure, add="+")
    # Run one extra delayed pass so startup picks the correct layout mode.
    owner._schedule_topbar_alignment(delay_ms=120)

    # Undo / Redo keyboard bindings (common Windows shortcuts)
    try:
        owner.text.bind("<Control-z>", owner._safe_edit_undo, add="+")
        owner.text.bind("<Control-y>", owner._safe_edit_redo, add="+")
        # Some keyboards/OS use Ctrl+Shift+Z for redo
        owner.text.bind("<Control-Shift-Z>", owner._safe_edit_redo, add="+")
    except Exception:
        # If widget doesn't support undo methods for any reason, ignore.
        pass

    theme = getattr(owner, "_theme", {})
    credit_bar_bg = theme.get("credit_bg", "#0b1118")
    credit_bar_border = theme.get("credit_border", "#1f2f3f")
    credit_label_fg = theme.get("credit_label_fg", "#b5cade")

    credit_bar = tk.Frame(
        owner.root,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=credit_bar_border,
        highlightcolor=credit_bar_border,
    )
    credit_bar.pack(side="bottom", fill="x", padx=4, pady=(0, 2))
    owner._credit_bar = credit_bar

    credit_left = tk.Frame(
        credit_bar,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_center = tk.Frame(
        credit_bar,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_right = tk.Frame(
        credit_bar,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_left.grid(row=0, column=0, sticky="w", padx=(6, 0), pady=(1, 1))
    credit_center.grid(row=0, column=1, sticky="ew", pady=(1, 1))
    credit_right.grid(row=0, column=2, sticky="e", padx=(0, 6), pady=(1, 1))
    owner._credit_left_slot = credit_left
    owner._credit_center_slot = credit_center
    owner._credit_right_slot = credit_right
    credit_bar.grid_rowconfigure(0, weight=1)
    # Let left/right size to content and keep center as flexible spacer.
    credit_bar.grid_columnconfigure(0, weight=0)
    credit_bar.grid_columnconfigure(1, weight=1)
    credit_bar.grid_columnconfigure(2, weight=0)

    credit_content = tk.Frame(
        credit_left,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_content.pack(side="left")
    owner._credit_content = credit_content

    credit_label = tk.Label(
        credit_content,
        text="DESIGNED BY :",
        bg=credit_bar_bg,
        fg=credit_label_fg,
        font=(owner._preferred_mono_family(), 9, "bold"),
        anchor="w",
        justify="left",
        bd=0,
        highlightthickness=0,
    )
    credit_label.pack(side="left")
    owner._credit_label = credit_label

    credit_badges = tk.Frame(
        credit_content,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_badges.pack(side="left", padx=(8, 0))
    owner._build_credit_badges(credit_badges)
    divider_main = owner._blend_hex_color(credit_bar_border, credit_label_fg, 0.35)
    divider_glow = owner._blend_hex_color(credit_label_fg, "#ffffff", 0.18)
    credit_divider = tk.Canvas(
        credit_content,
        width=8,
        height=18,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_divider.pack(side="left", padx=(8, 6))
    line_main = credit_divider.create_line(3, 2, 3, 16, fill=divider_main, width=1)
    line_glow = credit_divider.create_line(4, 3, 4, 15, fill=divider_glow, width=1)
    owner._credit_badges_divider = credit_divider
    owner._credit_badges_divider_lines = (line_main, line_glow)
    credit_discord_badges = tk.Frame(
        credit_content,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    credit_discord_badges.pack(side="left", padx=(0, 0))
    owner._build_credit_discord_badges(credit_discord_badges)
    discord_divider = tk.Canvas(
        credit_content,
        width=8,
        height=18,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    discord_divider.pack(side="left", padx=(8, 6))
    discord_line_main = discord_divider.create_line(3, 2, 3, 16, fill=divider_main, width=1)
    discord_line_glow = discord_divider.create_line(4, 3, 4, 15, fill=divider_glow, width=1)
    owner._credit_discord_divider = discord_divider
    owner._credit_discord_divider_lines = (discord_line_main, discord_line_glow)
    bug_controls = tk.Frame(
        credit_content,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    bug_controls.pack(side="left", padx=(0, 0))
    owner._build_bug_report_chip(bug_controls)
    theme_divider = tk.Canvas(
        credit_content,
        width=8,
        height=18,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    theme_divider.pack(side="left", padx=(8, 6))
    theme_line_main = theme_divider.create_line(3, 2, 3, 16, fill=divider_main, width=1)
    theme_line_glow = theme_divider.create_line(4, 3, 4, 15, fill=divider_glow, width=1)
    owner._credit_theme_divider = theme_divider
    owner._credit_theme_divider_lines = (theme_line_main, theme_line_glow)

    theme_controls = tk.Frame(
        credit_content,
        bg=credit_bar_bg,
        bd=0,
        highlightthickness=0,
    )
    theme_controls.pack(side="left", padx=(0, 0))
    owner._build_theme_selector(theme_controls)
    owner._build_header_variant_switch(theme_controls, show_title=False)
    owner._apply_footer_layout_variant()

    # Pack main body after footer is created so footer keeps reserved space
    # even when editor font size grows.
    body.pack(fill="both", expand=True, padx=4, pady=(0, 8))

    # Font size keyboard shortcuts
    owner.root.bind("<Control-plus>", lambda e: owner.increase_font_size())
    owner.root.bind("<Control-equal>", lambda e: owner.increase_font_size())  # Ctrl+= on some keyboards
    owner.root.bind("<Control-minus>", lambda e: owner.decrease_font_size())

    active_variant = str(getattr(owner, "_app_theme_variant", "SIINDBAD")).upper()
    other_variant = "KAMUE" if active_variant == "SIINDBAD" else "SIINDBAD"
    owner._schedule_theme_asset_prewarm(targets=(active_variant,), delay_ms=120)
    if bool(getattr(owner, "_startup_loader_enabled", False)):
        owner._startup_loader_deferred_variants = {other_variant}
        owner._show_startup_loader()
    else:
        owner._startup_loader_deferred_variants = set()
        owner._schedule_theme_asset_prewarm(targets=(other_variant,), delay_ms=650)
        if owner._auto_update_startup_enabled():
            owner._schedule_auto_update_check(delay_ms=500)

