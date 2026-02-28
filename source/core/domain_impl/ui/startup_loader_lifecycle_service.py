"""Startup loader lifecycle orchestration service."""

from typing import Any


def update_startup_loader_progress(owner: Any, *, time_module: Any, startup_loader_core: Any) -> None:
    overlay = getattr(owner, "_startup_loader_overlay", None)
    if overlay is None or not overlay.winfo_exists():
        return
    if bool(getattr(owner, "_startup_loader_finishing", False)):
        return
    started = float(getattr(owner, "_startup_loader_started_ts", 0.0) or 0.0)
    now = time_module.perf_counter()
    elapsed_ms = max(0.0, (now - started) * 1000.0) if started > 0 else 0.0
    timeline_ms = max(1000, int(getattr(owner, "_startup_loader_extra_hold_ms", 1800) or 1800))
    ready = getattr(owner, "_startup_loader_ready_ts", None) is not None
    overall, _top_pct, _bottom_pct = startup_loader_core.compute_loader_progress(
        elapsed_ms=elapsed_ms,
        timeline_ms=timeline_ms,
        ready=ready,
        required_variants=getattr(owner, "_startup_loader_required_variants", set()),
        active_variant=getattr(owner, "_app_theme_variant", "SIINDBAD"),
        variant_progress_getter=owner._startup_loader_variant_progress,
    )
    show_pct = owner._smooth_startup_loader_progress(overall, now_ts=now)
    top_pct, bottom_pct = startup_loader_core.compute_loader_fill_percentages(show_pct)

    owner._set_startup_loader_bar_fill(getattr(owner, "_startup_loader_top_fill", None), top_pct)
    owner._set_startup_loader_bar_fill(getattr(owner, "_startup_loader_bottom_fill", None), bottom_pct)

    pct_label = getattr(owner, "_startup_loader_pct_label", None)
    if pct_label is not None and pct_label.winfo_exists():
        pct_label.configure(text=f"{int(show_pct)}%")


def is_startup_full_load_ready(owner: Any, *, startup_loader_core: Any) -> bool:
    required = startup_loader_core.resolve_required_variants(
        getattr(owner, "_startup_loader_required_variants", set()),
        getattr(owner, "_app_theme_variant", "SIINDBAD"),
    )
    warmed = set(getattr(owner, "_theme_prewarm_done", set()))
    if required.issubset(warmed):
        return True
    totals = getattr(owner, "_theme_prewarm_total_by_variant", {})
    done = getattr(owner, "_theme_prewarm_done_by_variant", {})
    for variant in required:
        total = int(totals.get(variant, 0) or 0)
        finished = int(done.get(variant, 0) or 0)
        if total <= 0 or finished < total:
            return False
    return True


def on_startup_full_load_ready(owner: Any, *, tk_module: Any, time_module: Any, startup_loader_core: Any) -> None:
    if getattr(owner, "_startup_loader_ready_ts", None) is not None:
        return
    if not is_startup_full_load_ready(owner, startup_loader_core=startup_loader_core):
        return
    owner._startup_loader_ready_ts = time_module.perf_counter()
    owner._update_startup_loader_progress()
    owner._tick_startup_loader_statement()
    root = getattr(owner, "root", None)
    if root is None:
        return
    after_id = getattr(owner, "_startup_loader_hide_after_id", None)
    if after_id:
        try:
            root.after_cancel(after_id)
        except (tk_module.TclError, RuntimeError, ValueError):
            pass
    started = float(getattr(owner, "_startup_loader_started_ts", 0.0) or 0.0)
    elapsed_ms = max(0.0, (time_module.perf_counter() - started) * 1000.0) if started > 0 else 0.0
    timeline_ms = max(1000, int(getattr(owner, "_startup_loader_extra_hold_ms", 1800) or 1800))
    hold_ms = startup_loader_core.compute_loader_hide_hold_ms(
        elapsed_ms=elapsed_ms,
        timeline_ms=timeline_ms,
        min_hold_ms=250,
    )
    owner._startup_loader_hide_after_id = root.after(hold_ms, owner._hide_startup_loader)


def hide_startup_loader(owner: Any, *, tk_module: Any, time_module: Any, startup_loader_core: Any) -> None:
    root = getattr(owner, "root", None)
    overlay = getattr(owner, "_startup_loader_overlay", None)
    overlay_exists = False
    if overlay is not None:
        try:
            overlay_exists = bool(overlay.winfo_exists())
        except (tk_module.TclError, RuntimeError, AttributeError, ValueError):
            overlay_exists = False
    if (
        root is not None
        and overlay_exists
        and bool(getattr(owner, "_startup_loader_ready_ts", None) is not None)
    ):
        now = time_module.perf_counter()
        if not bool(getattr(owner, "_startup_loader_finishing", False)):
            owner._startup_loader_finishing = True
            owner._startup_loader_finish_started_ts = float(now)
            progress_after_id = getattr(owner, "_startup_loader_progress_after_id", None)
            if progress_after_id:
                try:
                    root.after_cancel(progress_after_id)
                except (tk_module.TclError, RuntimeError, ValueError):
                    pass
                owner._startup_loader_progress_after_id = None
            start_pct = 0.0
            try:
                pct_label = getattr(owner, "_startup_loader_pct_label", None)
                if pct_label is not None and pct_label.winfo_exists():
                    text = str(pct_label.cget("text") or "").strip().replace("%", "")
                    start_pct = max(0.0, min(100.0, float(text or 0.0)))
            except (tk_module.TclError, RuntimeError, AttributeError, ValueError, TypeError):
                start_pct = 0.0
            start_pct = max(
                start_pct,
                float(getattr(owner, "_startup_loader_display_pct", 0.0) or 0.0),
            )
            owner._startup_loader_finish_start_pct = float(start_pct)
            owner._startup_loader_finish_reached_100_ts = 0.0
        elapsed_ms = max(
            0.0,
            (
                float(now)
                - float(getattr(owner, "_startup_loader_finish_started_ts", now) or now)
            ) * 1000.0,
        )
        dwell_ms = max(
            120.0,
            float(getattr(owner, "_startup_loader_complete_dwell_ms", 260) or 260),
        )
        progress = max(0.0, min(1.0, elapsed_ms / dwell_ms))
        start_pct = float(getattr(owner, "_startup_loader_finish_start_pct", 0.0) or 0.0)
        show_pct = start_pct + ((100.0 - start_pct) * progress)
        show_pct = max(
            float(getattr(owner, "_startup_loader_display_pct", 0.0) or 0.0),
            min(100.0, float(show_pct)),
        )
        show_pct = min(
            show_pct,
            float(getattr(owner, "_startup_loader_display_pct", 0.0) or 0.0) + 2.0,
        )
        owner._startup_loader_display_pct = show_pct
        if show_pct >= 100.0:
            if float(getattr(owner, "_startup_loader_finish_reached_100_ts", 0.0) or 0.0) <= 0.0:
                owner._startup_loader_finish_reached_100_ts = float(now)
        else:
            owner._startup_loader_finish_reached_100_ts = 0.0
        reached_100_ts = float(getattr(owner, "_startup_loader_finish_reached_100_ts", 0.0) or 0.0)
        hold_elapsed_ms = (
            max(0.0, (float(now) - reached_100_ts) * 1000.0)
            if reached_100_ts > 0.0
            else 0.0
        )
        final_hold_ms = max(
            0.0,
            float(getattr(owner, "_startup_loader_finish_visible_hold_ms", 140) or 140),
        )
        top_pct, bottom_pct = startup_loader_core.compute_loader_fill_percentages(show_pct)
        try:
            owner._set_startup_loader_bar_fill(getattr(owner, "_startup_loader_top_fill", None), top_pct)
            owner._set_startup_loader_bar_fill(getattr(owner, "_startup_loader_bottom_fill", None), bottom_pct)
            pct_label = getattr(owner, "_startup_loader_pct_label", None)
            if pct_label is not None and pct_label.winfo_exists():
                pct_label.configure(text=f"{int(show_pct)}%")
            statement = getattr(owner, "_startup_loader_statement_label", None)
            if statement is not None and statement.winfo_exists():
                statement.configure(text="/startup shell handshake complete.")
            overlay.update_idletasks()
        except (tk_module.TclError, RuntimeError, AttributeError, ValueError):
            pass
        should_continue = startup_loader_core.should_continue_finish_animation(
            progress=progress,
            show_pct=show_pct,
        )
        if should_continue or hold_elapsed_ms < final_hold_ms:
            owner._startup_loader_hide_after_id = root.after(16, owner._hide_startup_loader)
            return

    if root is not None:
        for attr in (
            "_startup_loader_text_after_id",
            "_startup_loader_hide_after_id",
            "_startup_loader_progress_after_id",
            "_startup_loader_title_after_id",
        ):
            after_id = getattr(owner, attr, None)
            if after_id:
                try:
                    root.after_cancel(after_id)
                except (tk_module.TclError, RuntimeError, ValueError):
                    pass
            setattr(owner, attr, None)

    if overlay is not None and overlay_exists:
        try:
            overlay.destroy()
        except (tk_module.TclError, RuntimeError, AttributeError):
            pass
    if root is not None and bool(getattr(owner, "_startup_loader_window_mode", False)):
        alpha_fade_armed = False
        try:
            owner._apply_dark_theme()
            owner._style_text_widget()
            owner._apply_tree_style()
            owner._apply_tree_mode_style()
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            theme_bg = str((getattr(owner, "_theme", {}) or {}).get("bg", "#0f131a"))
            root.configure(bg=theme_bg)
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            root.update_idletasks()
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            root.attributes("-alpha", 0.0)
            alpha_fade_armed = True
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            alpha_fade_armed = False
        try:
            root.deiconify()
            root.update_idletasks()
            root.update()
            root.lift()
        except (tk_module.TclError, RuntimeError, AttributeError):
            pass
        if alpha_fade_armed:
            try:
                root.after(48, lambda target=root: owner._restore_startup_root_alpha(target))
            except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
                owner._restore_startup_root_alpha(root)
        try:
            root.focus_force()
        except (tk_module.TclError, RuntimeError, AttributeError):
            pass
    owner._startup_loader_overlay = None
    owner._startup_loader_pct_label = None
    owner._startup_loader_statement_label = None
    owner._startup_loader_title_prefix_label = None
    owner._startup_loader_title_suffix_label = None
    owner._startup_loader_top_fill = None
    owner._startup_loader_bottom_fill = None
    owner._startup_loader_display_pct = 0.0
    owner._startup_loader_last_progress_ts = 0.0
    owner._startup_loader_finishing = False
    owner._startup_loader_finish_started_ts = 0.0
    owner._startup_loader_finish_start_pct = 0.0
    owner._startup_loader_finish_reached_100_ts = 0.0
    deferred = startup_loader_core.normalize_deferred_variants_for_schedule(
        getattr(owner, "_startup_loader_deferred_variants", set())
    )
    owner._startup_loader_deferred_variants = set()
    if root is not None and deferred:
        try:
            owner._schedule_theme_asset_prewarm(targets=deferred, delay_ms=180)
        except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
            pass
    # Run auto update-check after loader teardown so startup stays responsive.
    if root is not None and owner._auto_update_startup_enabled():
        owner._schedule_auto_update_check(delay_ms=350)
    owner._schedule_crash_report_offer()


def restore_startup_root_alpha(target: Any, *, tk_module: Any) -> None:
    if target is None:
        return
    try:
        target.attributes("-alpha", 1.0)
    except (tk_module.TclError, RuntimeError, AttributeError, TypeError, ValueError):
        return
