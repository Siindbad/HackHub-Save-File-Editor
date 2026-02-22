import logging
UPDATE_STAGE_DEFAULT_MESSAGE = {
    "preparing": "Preparing update...\nThe app will restart automatically.",
    "downloading": "Downloading update...\nThis may take a moment.",
    "installing": "Installing update...\nThe app will restart automatically.",
    "restarting": "Update installed.\nRestarting app...",
}

UPDATE_STAGE_TARGET_PCT = {
    "preparing": 10.0,
    "downloading": 62.0,
    "installing": 88.0,
    "restarting": 100.0,
}

UPDATE_LOADER_BAR_COLORS = {
    # Keep updater bars visually aligned with startup loader palette.
    "track_top_bg": "#081a2c",
    "track_bottom_bg": "#140f22",
    "bar_top_fill": "#1f7a8f",
    "bar_bottom_fill": "#70479a",
}
_LOG = logging.getLogger(__name__)


def _log_ignored_exception(context, exc):
    # Record suppressed UI exceptions for diagnostics without changing flow.
    _LOG.debug("%s: %s", context, exc)

def _widget_exists(widget):
    if widget is None:
        return False
    exists_fn = getattr(widget, "winfo_exists", None)
    if callable(exists_fn):
        try:
            return bool(exists_fn())
        except Exception:
            return False
    return True


def _safe_after_cancel(root, after_id):
    if root is None or not after_id:
        return
    try:
        root.after_cancel(after_id)
    except Exception:
        return


def _resolve_update_message(stage, message):
    if message:
        return str(message)
    token = str(stage or "").strip().lower()
    return UPDATE_STAGE_DEFAULT_MESSAGE.get(token, "Updating...")


def _resolve_stage_percent(stage, percent):
    if percent is not None:
        try:
            value = float(percent)
        except Exception:
            value = 0.0
        return max(0.0, min(100.0, value))
    token = str(stage or "").strip().lower()
    mapped = UPDATE_STAGE_TARGET_PCT.get(token)
    if mapped is None:
        return None
    return float(mapped)


def _apply_update_window_chrome(owner, overlay, root):
    if owner is None or overlay is None:
        return
    try:
        icon_setter = getattr(owner, "_set_window_icon_for", None)
        if callable(icon_setter):
            icon_setter(overlay)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    # Force updater popup titlebar to SIINDBAD chrome for consistent update UX.
    siindbad_theme = {}
    try:
        palette_getter = getattr(owner, "_theme_palette_for_variant", None)
        if callable(palette_getter):
            siindbad_theme = dict(palette_getter("SIINDBAD") or {})
    except Exception:
        siindbad_theme = {}
    bg = siindbad_theme.get("title_bar_bg")
    fg = siindbad_theme.get("title_bar_fg")
    border = siindbad_theme.get("title_bar_border")
    if not bg or not fg:
        theme = getattr(owner, "_theme", {}) or {}
        bg = bg or theme.get("title_bar_bg")
        fg = fg or theme.get("title_bar_fg")
        border = border or theme.get("title_bar_border")
    try:
        apply_titlebar = getattr(owner, "_apply_windows_titlebar_theme", None)
        if callable(apply_titlebar):
            apply_titlebar(bg=bg, fg=fg, border=border, window_widget=overlay)
            if root is not None:
                root.after(
                    0,
                    lambda win=overlay, b=bg, f=fg, bd=border: apply_titlebar(
                        bg=b,
                        fg=f,
                        border=bd,
                        window_widget=win,
                    ),
                )
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
def _render_update_overlay_progress(owner, value):
    try:
        pct = max(0.0, min(100.0, float(value)))
    except Exception:
        return
    owner._update_overlay_progress_pct = pct
    pct_label = getattr(owner, "_update_overlay_pct_label", None)
    if pct_label is not None:
        try:
            pct_label.config(text=f"{int(round(pct))}%")
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
    top_bar = getattr(owner, "_update_overlay_top_bar", None)
    bottom_bar = getattr(owner, "_update_overlay_bottom_bar", None)
    try:
        if top_bar is not None:
            top_bar.configure(value=pct)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        if bottom_bar is not None:
            # Keep the lower bar slightly behind to preserve dual-bar depth.
            bottom_bar.configure(value=max(0.0, min(100.0, pct - 8.0)))
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
def show_themed_update_info(
    owner,
    title,
    message,
    tk,
    messagebox,
    startup_check_state=None,
    on_startup_check_change=None,
):
    # Theme-aware modal used for update notices and updater status messages.
    root = getattr(owner, "root", None)
    if root is None:
        try:
            messagebox.showinfo(title, message)
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        return

    theme = getattr(owner, "_theme", {}) or {}
    panel_bg = theme.get("panel", "#161b24")
    window_bg = theme.get("bg", "#0f131a")
    fg = theme.get("fg", "#e6e6e6")
    border = theme.get("logo_border_outer", theme.get("find_border", "#2a5a7a"))
    title_bg = theme.get("title_bar_bg", panel_bg)
    title_fg = theme.get("title_bar_fg", fg)

    dlg = tk.Toplevel(root)
    try:
        dlg.withdraw()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.title(str(title or "Update"))
    try:
        dlg.transient(root)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.configure(bg=window_bg)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.resizable(False, False)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    shell = tk.Frame(
        dlg,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(
        shell,
        bg=title_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    header.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(
        header,
        text=str(title or "Update").upper(),
        bg=title_bg,
        fg=title_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        anchor="w",
        padx=10,
        pady=6,
    ).pack(fill="x")

    body = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    body.pack(fill="both", expand=True, padx=14, pady=(2, 8))
    tk.Label(
        body,
        text=str(message or ""),
        bg=panel_bg,
        fg=fg,
        justify="left",
        anchor="w",
        wraplength=420,
        font=(owner._preferred_mono_family(), 10),
        padx=0,
        pady=0,
    ).pack(fill="x", anchor="w")

    button_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    button_row.pack(fill="x", padx=10, pady=(0, 10))

    check_var = None
    check_applied = {"done": False}
    if startup_check_state is not None:
        check_var = tk.BooleanVar(value=bool(startup_check_state))
        check_btn = tk.Checkbutton(
            button_row,
            text="Check for updates on startup",
            variable=check_var,
            bg=panel_bg,
            fg=fg,
            activebackground=panel_bg,
            activeforeground=fg,
            selectcolor=theme.get("bg", "#0f131a"),
            highlightthickness=0,
            bd=0,
            font=(owner._preferred_mono_family(), 9),
            anchor="w",
            justify="left",
            padx=0,
            pady=0,
        )
        check_btn.pack(side="left", anchor="w")

    def apply_startup_toggle():
        if check_var is None or check_applied["done"]:
            return
        check_applied["done"] = True
        if callable(on_startup_check_change):
            try:
                on_startup_check_change(bool(check_var.get()))
            except Exception as exc:
                _log_ignored_exception("update_ui_service", exc)
    def close_dialog(event=None):
        apply_startup_toggle()
        try:
            dlg.grab_release()
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        try:
            dlg.destroy()
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        return "break" if event is not None else None

    ok_btn = tk.Button(
        button_row,
        text="OK",
        command=close_dialog,
        bg=theme.get("accent", "#202737"),
        fg=theme.get("select_fg", "#ffffff"),
        activebackground=theme.get("button_active", theme.get("accent", "#202737")),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    ok_btn.pack(side="right")

    try:
        owner._apply_centered_toplevel_geometry(
            dlg,
            width_px=500,
            height_px=190,
            anchor_window=root,
            min_width=420,
            min_height=170,
            max_width_ratio=0.70,
            max_height_ratio=0.45,
        )
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.protocol("WM_DELETE_WINDOW", close_dialog)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.bind("<Escape>", close_dialog, add="+")
    dlg.bind("<Return>", close_dialog, add="+")

    try:
        dlg.deiconify()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        owner._apply_windows_titlebar_theme(
            bg=theme.get("title_bar_bg"),
            fg=theme.get("title_bar_fg"),
            border=theme.get("title_bar_border"),
            window_widget=dlg,
        )
        root.after(
            0,
            lambda win=dlg, th=theme: owner._apply_windows_titlebar_theme(
                bg=th.get("title_bar_bg"),
                fg=th.get("title_bar_fg"),
                border=th.get("title_bar_border"),
                window_widget=win,
            ),
        )
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.lift()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.grab_set()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        ok_btn.focus_set()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.wait_window()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
def show_themed_update_confirm(
    owner,
    title,
    message,
    tk,
    messagebox,
    startup_check_state=None,
    on_startup_check_change=None,
):
    # Theme-aware Yes/No modal for update confirmation prompts.
    root = getattr(owner, "root", None)
    if root is None:
        try:
            return bool(messagebox.askyesno(title, message))
        except Exception:
            return False

    theme = getattr(owner, "_theme", {}) or {}
    panel_bg = theme.get("panel", "#161b24")
    window_bg = theme.get("bg", "#0f131a")
    fg = theme.get("fg", "#e6e6e6")
    border = theme.get("logo_border_outer", theme.get("find_border", "#2a5a7a"))
    title_bg = theme.get("title_bar_bg", panel_bg)
    title_fg = theme.get("title_bar_fg", fg)

    dlg = tk.Toplevel(root)
    try:
        dlg.withdraw()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.title(str(title or "Update"))
    try:
        dlg.transient(root)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.configure(bg=window_bg)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.resizable(False, False)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    shell = tk.Frame(
        dlg,
        bg=panel_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    shell.pack(fill="both", expand=True, padx=12, pady=12)

    header = tk.Frame(
        shell,
        bg=title_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground=border,
        highlightcolor=border,
    )
    header.pack(fill="x", padx=10, pady=(10, 8))
    tk.Label(
        header,
        text=str(title or "Update").upper(),
        bg=title_bg,
        fg=title_fg,
        font=(owner._preferred_mono_family(), 11, "bold"),
        anchor="w",
        padx=10,
        pady=6,
    ).pack(fill="x")

    body = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    body.pack(fill="both", expand=True, padx=14, pady=(2, 8))
    tk.Label(
        body,
        text=str(message or ""),
        bg=panel_bg,
        fg=fg,
        justify="left",
        anchor="w",
        wraplength=420,
        font=(owner._preferred_mono_family(), 10),
        padx=0,
        pady=0,
    ).pack(fill="x", anchor="w")

    button_row = tk.Frame(shell, bg=panel_bg, bd=0, highlightthickness=0)
    button_row.pack(fill="x", padx=10, pady=(0, 10))

    result = {"value": False}
    check_var = None
    check_applied = {"done": False}
    if startup_check_state is not None:
        check_var = tk.BooleanVar(value=bool(startup_check_state))
        check_btn = tk.Checkbutton(
            button_row,
            text="Check for updates on startup",
            variable=check_var,
            bg=panel_bg,
            fg=fg,
            activebackground=panel_bg,
            activeforeground=fg,
            selectcolor=theme.get("bg", "#0f131a"),
            highlightthickness=0,
            bd=0,
            font=(owner._preferred_mono_family(), 9),
            anchor="w",
            justify="left",
            padx=0,
            pady=0,
        )
        check_btn.pack(side="left", anchor="w")

    def apply_startup_toggle():
        if check_var is None or check_applied["done"]:
            return
        check_applied["done"] = True
        if callable(on_startup_check_change):
            try:
                on_startup_check_change(bool(check_var.get()))
            except Exception as exc:
                _log_ignored_exception("update_ui_service", exc)
    def close_dialog(event=None):
        apply_startup_toggle()
        try:
            dlg.grab_release()
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        try:
            dlg.destroy()
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        return "break" if event is not None else None

    def choose_yes(event=None):
        result["value"] = True
        return close_dialog(event)

    def choose_no(event=None):
        result["value"] = False
        return close_dialog(event)

    yes_btn = tk.Button(
        button_row,
        text="Yes",
        command=choose_yes,
        bg=theme.get("accent", "#202737"),
        fg=theme.get("select_fg", "#ffffff"),
        activebackground=theme.get("button_active", theme.get("accent", "#202737")),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    yes_btn.pack(side="right")

    no_btn = tk.Button(
        button_row,
        text="No",
        command=choose_no,
        bg=theme.get("panel", "#161b24"),
        fg=theme.get("fg", "#e6e6e6"),
        activebackground=theme.get("accent", "#202737"),
        activeforeground=theme.get("select_fg", "#ffffff"),
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        cursor="hand2",
        font=(owner._preferred_mono_family(), 10, "bold"),
    )
    no_btn.pack(side="right", padx=(0, 8))

    try:
        owner._apply_centered_toplevel_geometry(
            dlg,
            width_px=500,
            height_px=210,
            anchor_window=root,
            min_width=420,
            min_height=180,
            max_width_ratio=0.70,
            max_height_ratio=0.46,
        )
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.protocol("WM_DELETE_WINDOW", choose_no)
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    dlg.bind("<Escape>", choose_no, add="+")
    dlg.bind("<Return>", choose_yes, add="+")

    try:
        dlg.deiconify()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        owner._apply_windows_titlebar_theme(
            bg=theme.get("title_bar_bg"),
            fg=theme.get("title_bar_fg"),
            border=theme.get("title_bar_border"),
            window_widget=dlg,
        )
        root.after(
            0,
            lambda win=dlg, th=theme: owner._apply_windows_titlebar_theme(
                bg=th.get("title_bar_bg"),
                fg=th.get("title_bar_fg"),
                border=th.get("title_bar_border"),
                window_widget=win,
            ),
        )
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.lift()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.grab_set()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        yes_btn.focus_set()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    try:
        dlg.wait_window()
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    return bool(result["value"])


def show_update_overlay(owner, message, tk, ttk):
    # Blocking progress overlay while update download/apply is in progress.
    if getattr(owner, "_update_overlay", None):
        return
    overlay = tk.Toplevel(owner.root)
    overlay.title("Updating...")
    popup_scale = max(0.9, min(1.25, float(getattr(owner, "_display_scale", 1.0) or 1.0)))
    owner._apply_centered_toplevel_geometry(
        overlay,
        width_px=int(round(360 * popup_scale)),
        height_px=int(round(120 * popup_scale)),
        min_width=320,
        min_height=110,
        max_width_ratio=0.72,
        max_height_ratio=0.40,
    )
    overlay.resizable(False, False)
    overlay.transient(owner.root)
    overlay.grab_set()
    _apply_update_window_chrome(owner, overlay, getattr(owner, "root", None))
    frame = ttk.Frame(overlay, padding=12)
    frame.pack(fill="both", expand=True)

    header = tk.Frame(frame, bg=getattr(owner, "_theme", {}).get("panel", "#161b24"), bd=0, highlightthickness=0)
    header.pack(fill="x", pady=(0, 8))

    title_prefix = tk.Label(
        header,
        text="UPDATE SYSTEM SYNC",
        bg=getattr(owner, "_theme", {}).get("panel", "#161b24"),
        fg=getattr(owner, "_theme", {}).get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="w",
        justify="left",
    )
    title_prefix.pack(side="left")

    pct_label = tk.Label(
        header,
        text="0%",
        bg=getattr(owner, "_theme", {}).get("panel", "#161b24"),
        fg=getattr(owner, "_theme", {}).get("fg", "#e6e6e6"),
        font=(owner._preferred_mono_family(), 12, "bold"),
        anchor="e",
        justify="right",
    )
    pct_label.pack(side="right")

    label = ttk.Label(frame, text=_resolve_update_message("preparing", message))
    label.pack(anchor="w", pady=(0, 8))
    top_bar = ttk.Progressbar(frame, mode="determinate", maximum=100)
    top_bar.pack(fill="x")
    bottom_bar = ttk.Progressbar(frame, mode="determinate", maximum=100)
    bottom_bar.pack(fill="x", pady=(6, 0))

    owner._update_overlay = overlay
    owner._update_overlay_label = label
    owner._update_overlay_top_bar = top_bar
    owner._update_overlay_bottom_bar = bottom_bar
    owner._update_overlay_pct_label = pct_label
    owner._update_overlay_title_prefix_label = title_prefix
    owner._update_overlay_title_suffix_label = None
    owner._update_overlay_title_variant = "UPDATE"
    owner._update_overlay_title_after_id = None
    owner._update_overlay_progress_pct = 0.0
    owner._update_overlay_stage = "preparing"
    try:
        style = ttk.Style(overlay)
        style.configure(
            "Update.Top.Horizontal.TProgressbar",
            troughcolor=UPDATE_LOADER_BAR_COLORS["track_top_bg"],
            background=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            darkcolor=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            lightcolor=UPDATE_LOADER_BAR_COLORS["bar_top_fill"],
            bordercolor=UPDATE_LOADER_BAR_COLORS["track_top_bg"],
            thickness=11,
        )
        style.configure(
            "Update.Bottom.Horizontal.TProgressbar",
            troughcolor=UPDATE_LOADER_BAR_COLORS["track_bottom_bg"],
            background=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            darkcolor=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            lightcolor=UPDATE_LOADER_BAR_COLORS["bar_bottom_fill"],
            bordercolor=UPDATE_LOADER_BAR_COLORS["track_bottom_bg"],
            thickness=11,
        )
        top_bar.configure(style="Update.Top.Horizontal.TProgressbar")
        bottom_bar.configure(style="Update.Bottom.Horizontal.TProgressbar")
    except Exception as exc:
        _log_ignored_exception("update_ui_service", exc)
    if getattr(owner, "_theme", None):
        theme = owner._theme
        overlay.configure(bg=theme["bg"])
        try:
            frame.configure(style="Update.TFrame")
            label.configure(background=theme["bg"], foreground=theme["fg"])
            style = ttk.Style(overlay)
            style.configure("Update.TFrame", background=theme["bg"])
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
    _render_update_overlay_progress(owner, UPDATE_STAGE_TARGET_PCT["preparing"])


def update_update_overlay(owner, message=None, stage=None, percent=None, pulse=False):
    # Update progress text + staged percentage without rebuilding overlay widgets.
    overlay = getattr(owner, "_update_overlay", None)
    label = getattr(owner, "_update_overlay_label", None)
    if overlay and label and _widget_exists(overlay):
        stage_token = str(stage or "").strip().lower()
        if stage_token:
            owner._update_overlay_stage = stage_token
        shown_message = _resolve_update_message(stage_token, message)
        try:
            label.config(text=shown_message)
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
        target_pct = _resolve_stage_percent(stage_token, percent)
        if target_pct is not None:
            _render_update_overlay_progress(owner, target_pct)
        elif bool(pulse):
            current = float(getattr(owner, "_update_overlay_progress_pct", 0.0) or 0.0)
            # Keep download stage moving subtly when byte totals are unknown.
            pulse_target = max(0.0, min(96.0, current + 1.2))
            _render_update_overlay_progress(owner, pulse_target)


def close_update_overlay(owner):
    # Remove overlay and clear cached widget references.
    root = getattr(owner, "root", None)
    _safe_after_cancel(root, getattr(owner, "_update_overlay_title_after_id", None))
    owner._update_overlay_title_after_id = None
    overlay = getattr(owner, "_update_overlay", None)
    if overlay:
        try:
            overlay.destroy()
        except Exception as exc:
            _log_ignored_exception("update_ui_service", exc)
    owner._update_overlay = None
    owner._update_overlay_label = None
    owner._update_overlay_top_bar = None
    owner._update_overlay_bottom_bar = None
    owner._update_overlay_pct_label = None
    owner._update_overlay_title_prefix_label = None
    owner._update_overlay_title_suffix_label = None
    owner._update_overlay_title_variant = "SIINDBAD"
    owner._update_overlay_progress_pct = 0.0
    owner._update_overlay_stage = ""


