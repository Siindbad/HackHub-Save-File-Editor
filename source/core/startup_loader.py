from typing import Any, Callable, Set, Tuple


VALID_THEME_VARIANTS = ("SIINDBAD", "KAMUE")


def normalize_theme_variant(value: Any, default: Any="SIINDBAD") -> str:
    variant = str(value or "").upper()
    if variant in VALID_THEME_VARIANTS:
        return variant
    fallback = str(default or "SIINDBAD").upper()
    return fallback if fallback in VALID_THEME_VARIANTS else "SIINDBAD"


def resolve_required_variants(required_variants: Any, active_variant: Any) -> Set[str]:
    required = {
        str(name).upper()
        for name in (required_variants or set())
        if str(name).upper() in VALID_THEME_VARIANTS
    }
    if required:
        return required
    return {normalize_theme_variant(active_variant)}


def prepare_loader_variants(active_variant: Any, deferred_variants: Any) -> Any:
    active = normalize_theme_variant(active_variant)
    deferred = {
        str(name).upper()
        for name in (deferred_variants or set())
        if str(name).upper() in VALID_THEME_VARIANTS
    }
    deferred.discard(active)
    return active, {active}, deferred


def compute_loader_progress(
    elapsed_ms: float,
    timeline_ms: int,
    ready: bool,
    required_variants: Any,
    active_variant: Any,
    variant_progress_getter: Callable[[str], float],
) -> Tuple[float, float, float]:
    timeline_ms = max(1000, int(timeline_ms or 0))
    elapsed_ms = max(0.0, float(elapsed_ms or 0.0))
    timed_pct = min(100.0, (elapsed_ms * 100.0) / float(timeline_ms))

    required = resolve_required_variants(required_variants, active_variant)
    progress_values = [
        float(variant_progress_getter(name))
        for name in sorted(required)
    ]
    real_overall = (
        sum(progress_values) / float(len(progress_values))
        if progress_values
        else 0.0
    )

    if ready and elapsed_ms >= float(timeline_ms):
        overall = 100.0
    else:
        if ready:
            # Keep cinematic progression strictly timeline-driven after readiness.
            overall = min(99.0, timed_pct)
        else:
            # Keep timeline-driven movement while staying close to real readiness.
            overall = min(99.0, timed_pct)
            overall = min(overall, min(99.0, real_overall + 18.0))
        overall = max(0.0, overall)

    if overall >= 100.0:
        top_pct = 100.0
        bottom_pct = 100.0
    else:
        top_pct = min(99.0, overall * 1.04)
        bottom_pct = max(0.0, min(99.0, overall * 0.92 + 4.0))

    return overall, top_pct, bottom_pct


def compute_loader_hide_hold_ms(elapsed_ms: float, timeline_ms: int, min_hold_ms: int = 250) -> int:
    timeline_ms = max(1000, int(timeline_ms or 0))
    elapsed_ms = max(0.0, float(elapsed_ms or 0.0))
    remaining_ms = max(0, int(round(float(timeline_ms) - elapsed_ms)))
    return max(int(min_hold_ms), remaining_ms)


def normalize_deferred_variants_for_schedule(deferred_variants: Any) -> Tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(name).upper()
                for name in (deferred_variants or set())
                if str(name).upper() in VALID_THEME_VARIANTS
            }
        )
    )


def prewarm_tick_policy(
    loader_visible: bool,
    loader_budget_ms: int,
    idle_budget_ms: int,
    loader_tick_ms: int,
    idle_tick_ms: int,
) -> Any:
    if loader_visible:
        budget_ms = max(2, int(loader_budget_ms or 0))
        max_tasks_this_tick = 2
        next_tick_ms = max(8, int(loader_tick_ms or 0))
    else:
        budget_ms = max(3, int(idle_budget_ms or 0))
        max_tasks_this_tick = 999999
        next_tick_ms = max(8, int(idle_tick_ms or 0))
    return budget_ms, max_tasks_this_tick, next_tick_ms
