"""Startup loader UI composition service."""
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


# Loader UI extraction keeps widget assembly outside the editor class.
def show_startup_loader(owner: Any, tk: Any, time: Any, startup_loader_core: Any) -> Any:
    if not bool(getattr(owner, "_startup_loader_enabled", False)):
        return
    root = getattr(owner, "root", None)
    if root is None:
        return
    active_variant, required_variants, deferred_variants = startup_loader_core.prepare_loader_variants(
        getattr(owner, "_app_theme_variant", "SIINDBAD"),
        getattr(owner, "_startup_loader_deferred_variants", set()),
    )
    # Loader readiness is tied to the active theme only. The other theme
    # prewarms after loader close to keep startup snappy.
    owner._startup_loader_required_variants = required_variants
    owner._startup_loader_deferred_variants = deferred_variants
    existing = getattr(owner, "_startup_loader_overlay", None)
    if existing is not None and existing.winfo_exists():
        return
    display_scale = max(0.85, min(1.35, float(getattr(owner, "_display_scale", 1.0) or 1.0)))
    loader_scale = max(0.70, min(0.98, 0.75 * display_scale))

    def _s(value, minimum=1):
        return max(int(minimum), int(round(float(value) * loader_scale)))

    def _rgb_to_hex(rgb):
        r, g, b = [max(0, min(255, int(round(v)))) for v in rgb]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _mix_hex(color_a, color_b, ratio):
        ra, ga, ba = owner._hex_to_rgb_tuple(color_a, default_rgb=(18, 24, 32))
        rb, gb, bb = owner._hex_to_rgb_tuple(color_b, default_rgb=(0, 0, 0))
        t = max(0.0, min(1.0, float(ratio)))
        return _rgb_to_hex(
            (
                ra + (rb - ra) * t,
                ga + (gb - ga) * t,
                ba + (bb - ba) * t,
            )
        )

    # Restore original loader palette.
    card_bg = "#020812"
    overlay_bg = "#040d1b" if bool(getattr(owner, "_startup_loader_window_mode", False)) else "#02050c"
    track_top_bg = "#081a2c"
    track_bottom_bg = "#140f22"
    bar_top_fill = "#1f7a8f"
    bar_bottom_fill = "#70479a"
    line_bg = "#08172a"
    line_border = "#335677"
    title_fg = "#d8ecff"
    sub_fg = "#8fb0cd"
    pct_fg = "#d8ecff"

    window_mode = bool(getattr(owner, "_startup_loader_window_mode", False))
    window_width = _s(560)
    window_height = _s(240)
    card_width = window_width if window_mode else _s(540)
    card_height = window_height if window_mode else _s(220)
    if window_mode:
        overlay = tk.Toplevel(root)
        overlay.overrideredirect(True)
        try:
            overlay.attributes("-topmost", True)
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
        overlay.configure(bg=overlay_bg, cursor="watch")
        owner._apply_centered_toplevel_geometry(
            overlay,
            width_px=window_width,
            height_px=window_height,
            min_width=_s(420),
            min_height=_s(180),
            max_width_ratio=0.86,
            max_height_ratio=0.75,
        )
        container = overlay
    else:
        overlay = tk.Frame(root, bg=overlay_bg, bd=0, highlightthickness=0, cursor="watch")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()
        for event_name in ("<Button-1>", "<Button-2>", "<Button-3>", "<Key>"):
            overlay.bind(event_name, lambda _evt: "break")
        container = overlay

    card = tk.Frame(
        container,
        bg=card_bg,
        bd=0,
        highlightthickness=1,
        highlightbackground="#2d4d72",
        highlightcolor="#2d4d72",
    )
    if window_mode:
        card.place(x=0, y=0, width=card_width, height=card_height)
    else:
        card.place(relx=0.5, rely=0.5, anchor="center", width=card_width, height=card_height)

    title_row = tk.Frame(card, bg=card_bg, bd=0, highlightthickness=0)
    title_row.place(x=_s(16), y=_s(20), width=max(_s(200), card_width - _s(100)), height=_s(34))

    title_prefix = tk.Label(
        title_row,
        text="SIINDBAD",
        bg=card_bg,
        fg=title_fg,
        font=(
            owner._resolve_font_family(
                [
                    "Tektur SemiBold",
                    "Tektur",
                ],
                owner._preferred_mono_family(),
            ),
            max(10, _s(17)),
            "bold",
        ),
        bd=0,
        highlightthickness=0,
        anchor="center",
        justify="center",
        width=8,
    )
    title_prefix.pack(side="left")
    title_suffix = tk.Label(
        title_row,
        text=" SHELL SYSTEM SYNC",
        bg=card_bg,
        fg=title_fg,
        font=(
            owner._resolve_font_family(
                [
                    "Tektur SemiBold",
                    "Tektur",
                ],
                owner._preferred_mono_family(),
            ),
            max(10, _s(17)),
            "bold",
        ),
        bd=0,
        highlightthickness=0,
        anchor="w",
        justify="left",
    )
    title_suffix.pack(side="left")

    pct = tk.Label(
        card,
        text="0%",
        bg=card_bg,
        fg=pct_fg,
        font=(
            owner._resolve_font_family(
                [
                    "Coalition",
                ],
                owner._preferred_mono_family(),
            ),
            max(24, _s(32)),
            "bold",
        ),
        bd=0,
        highlightthickness=0,
        anchor="e",
        justify="right",
    )
    # Keep the percentage locked to a static right-edge position.
    pct.place(x=card_width - _s(18), y=_s(6), anchor="ne")

    track_x = _s(16)
    track_width = max(_s(220), card_width - (_s(16) * 2))
    track_height = max(8, _s(16))

    track_top = tk.Frame(
        card,
        bg=card_bg,
        bd=0,
        highlightthickness=0,
    )
    track_top.place(x=track_x, y=_s(70), width=track_width, height=track_height)
    track_top_shell = tk.Label(track_top, bg=card_bg, bd=0, highlightthickness=0)
    track_top_shell.place(x=0, y=0, relwidth=1, relheight=1)
    track_top_shell_photo = owner._startup_loader_rounded_panel_photo(
        track_top_bg,
        line_border,
        track_width,
        track_height,
        border_px=1,
    )
    if track_top_shell_photo is not None:
        track_top_shell.configure(image=track_top_shell_photo)
        track_top_shell.image = track_top_shell_photo
    fill_top_widget = tk.Label(track_top, bg=track_top_bg, bd=0, highlightthickness=0)
    fill_top_widget.place_forget()
    fill_top = {
        "owner": owner,
        "track": track_top,
        "widget": fill_top_widget,
        "color": bar_top_fill,
    }

    track_bottom = tk.Frame(
        card,
        bg=card_bg,
        bd=0,
        highlightthickness=0,
    )
    track_bottom.place(x=track_x, y=_s(96), width=track_width, height=track_height)
    track_bottom_shell = tk.Label(track_bottom, bg=card_bg, bd=0, highlightthickness=0)
    track_bottom_shell.place(x=0, y=0, relwidth=1, relheight=1)
    track_bottom_shell_photo = owner._startup_loader_rounded_panel_photo(
        track_bottom_bg,
        "#5d4682",
        track_width,
        track_height,
        border_px=1,
    )
    if track_bottom_shell_photo is not None:
        track_bottom_shell.configure(image=track_bottom_shell_photo)
        track_bottom_shell.image = track_bottom_shell_photo
    fill_bottom_widget = tk.Label(track_bottom, bg=track_bottom_bg, bd=0, highlightthickness=0)
    fill_bottom_widget.place_forget()
    fill_bottom = {
        "owner": owner,
        "track": track_bottom,
        "widget": fill_bottom_widget,
        "color": bar_bottom_fill,
    }

    line = tk.Label(
        card,
        text="/buffering startup core sectors...",
        bg=line_bg,
        fg=_mix_hex("#d4f0ff", card_bg, 0.18),
        font=(owner._preferred_mono_family(), max(8, _s(10)), "bold"),
        anchor="w",
        justify="left",
        bd=0,
        padx=max(4, _s(8)),
        pady=max(3, _s(6)),
        highlightthickness=1,
        highlightbackground=line_border,
        highlightcolor=line_border,
    )
    line.place(x=track_x, y=_s(136), width=track_width, height=max(20, _s(34)))

    sub = tk.Label(
        card,
        text="siindbad <-> kamue : buffering protocol fusion",
        bg=card_bg,
        fg=sub_fg,
        font=(owner._preferred_mono_family(), max(8, _s(9))),
        anchor="w",
        justify="left",
        bd=0,
        highlightthickness=0,
    )
    sub.place(x=track_x, y=_s(182))

    owner._startup_loader_overlay = overlay
    owner._startup_loader_pct_label = pct
    owner._startup_loader_statement_label = line
    owner._startup_loader_title_prefix_label = title_prefix
    owner._startup_loader_title_suffix_label = title_suffix
    owner._startup_loader_top_fill = fill_top
    owner._startup_loader_bottom_fill = fill_bottom
    owner._startup_loader_started_ts = time.perf_counter()
    owner._startup_loader_ready_ts = None
    owner._startup_loader_statement_index = 0
    owner._startup_loader_line_pool_loading = []
    owner._startup_loader_line_pool_ready = []
    owner._startup_loader_title_variant = "SIINDBAD"
    owner._apply_startup_loader_title_variant()
    if window_mode:
        try:
            overlay.update_idletasks()
            overlay.update()
        except EXPECTED_ERRORS as exc:
            _LOG.debug('expected_error', exc_info=exc)
            pass
    root = getattr(owner, "root", None)
    if root is not None:
        after_id = getattr(owner, "_startup_loader_title_after_id", None)
        if after_id:
            try:
                root.after_cancel(after_id)
            except EXPECTED_ERRORS as exc:
                _LOG.debug('expected_error', exc_info=exc)
                pass
        cycle_ms = max(2200, int(getattr(owner, "_startup_loader_title_cycle_ms", 4200) or 4200))
        owner._startup_loader_title_after_id = root.after(cycle_ms, owner._tick_startup_loader_title)
    owner._update_startup_loader_progress()
    owner._tick_startup_loader_progress()
    owner._tick_startup_loader_statement()
