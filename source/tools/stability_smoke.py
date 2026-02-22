import argparse
import contextlib
import gc
import importlib
import io
import statistics
import sys
import time
import tracemalloc
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _fmt_mib(num_bytes: int) -> str:
    return f"{float(num_bytes) / (1024.0 * 1024.0):.2f} MiB"


def _percentile(values, pct):
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    pct = max(0.0, min(100.0, float(pct)))
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[idx]


def _pump_events(root, duration_s=0.1, sleep_s=0.01):
    deadline = time.perf_counter() + max(0.0, float(duration_s))
    while time.perf_counter() < deadline:
        root.update_idletasks()
        root.update()
        if sleep_s > 0:
            time.sleep(sleep_s)


def _wait_for_loader_ready(editor, root, timeout_s):
    timeout_s = max(0.1, float(timeout_s))
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        root.update_idletasks()
        root.update()
        started = float(getattr(editor, "_startup_loader_started_ts", 0.0) or 0.0)
        ready = getattr(editor, "_startup_loader_ready_ts", None)
        if started > 0 and ready is not None:
            return True, max(0.0, (float(ready) - started) * 1000.0)
        time.sleep(0.005)
    started = float(getattr(editor, "_startup_loader_started_ts", 0.0) or 0.0)
    if started <= 0:
        return False, 0.0
    return False, max(0.0, (time.perf_counter() - started) * 1000.0)


def _run_quick_close_smoke(editor_cls, destroy_after_ms=350, timeout_s=3.0):
    stderr_capture = io.StringIO()
    with contextlib.redirect_stderr(stderr_capture):
        root = editor = None
        try:
            import tkinter as tk

            root = tk.Tk()
            root._hh_use_startup_loader_window = True
            editor = editor_cls(root, None)
            root.after(max(10, int(destroy_after_ms)), root.destroy)
            deadline = time.perf_counter() + max(0.5, float(timeout_s))
            while time.perf_counter() < deadline:
                try:
                    root.update_idletasks()
                    root.update()
                except tk.TclError:
                    break
                time.sleep(0.01)
        finally:
            if editor is not None:
                try:
                    editor._hide_startup_loader()
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                    pass
            if root is not None:
                try:
                    root.destroy()
                except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                    pass

    stderr_text = stderr_capture.getvalue().lower()
    bad = ("invalid command name" in stderr_text) or ("while executing" in stderr_text)
    return (not bad), stderr_capture.getvalue().strip()


def _run_theme_switch_smoke(
    editor_cls,
    switches=240,
    startup_timeout_s=12.0,
    switch_pause_ms=0.0,
):
    import tkinter as tk

    tracemalloc.start()
    root = editor = None
    try:
        root = tk.Tk()
        root._hh_use_startup_loader_window = True
        editor = editor_cls(root, None)

        ready, ready_ms = _wait_for_loader_ready(editor, root, timeout_s=startup_timeout_s)
        try:
            editor._hide_startup_loader()
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
            pass
        _pump_events(root, duration_s=0.2, sleep_s=0.005)

        gc.collect()
        base_cur, peak_bytes = tracemalloc.get_traced_memory()

        durations = []
        half = max(1, int(switches) // 2)
        switch_pause_s = max(0.0, float(switch_pause_ms)) / 1000.0
        for idx in range(max(2, int(switches))):
            target = "KAMUE" if (idx % 2) else "SIINDBAD"
            t0 = time.perf_counter()
            editor._set_app_theme_variant(target, save=False)
            root.update_idletasks()
            root.update()
            durations.append((time.perf_counter() - t0) * 1000.0)
            if switch_pause_s > 0:
                time.sleep(switch_pause_s)
            if idx + 1 == half:
                gc.collect()
                mid_cur, peak_now = tracemalloc.get_traced_memory()
                peak_bytes = max(peak_bytes, peak_now)
        gc.collect()
        end_cur, peak_now = tracemalloc.get_traced_memory()
        peak_bytes = max(peak_bytes, peak_now)

        avg_ms = statistics.mean(durations)
        p95_ms = _percentile(durations, 95)
        max_ms = max(durations)
        phase1_growth = int(mid_cur - base_cur)
        phase2_growth = int(end_cur - mid_cur)
        total_growth = int(end_cur - base_cur)

        return {
            "ready": bool(ready),
            "ready_ms": float(ready_ms),
            "switches": int(switches),
            "avg_ms": float(avg_ms),
            "p95_ms": float(p95_ms),
            "max_ms": float(max_ms),
            "phase1_growth": phase1_growth,
            "phase2_growth": phase2_growth,
            "total_growth": total_growth,
            "peak_bytes": int(peak_bytes),
        }
    finally:
        tracemalloc.stop()
        if editor is not None:
            try:
                editor._hide_startup_loader()
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                pass
        if root is not None:
            try:
                root.destroy()
            except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
                pass


def _apply_safe_mode_overrides(args):
    # Safe mode is the default local/CI-friendly profile to reduce false failures.
    args.switches = min(int(args.switches), 120)
    args.switch_pause_ms = max(float(args.switch_pause_ms), 8.0)
    # Safe mode runs on shared/hosted runners where scheduling jitter is common.
    # Keep p95 strict for sustained regressions and relax avg/max only enough
    # to avoid false failures from occasional host contention.
    args.max_avg_switch_ms = max(float(args.max_avg_switch_ms), 95.0)
    args.max_switch_ms = max(float(args.max_switch_ms), 2200.0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stability smoke checks for startup/theme-switch behavior."
    )
    parser.add_argument("--module", default="sins_editor")
    # Strict gate exits non-zero when any threshold is exceeded.
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Lower-impact defaults for local checks (fewer switches + pacing sleep).",
    )
    parser.add_argument("--switches", type=int, default=240)
    parser.add_argument(
        "--switch-pause-ms",
        type=float,
        default=0.0,
        help="Optional sleep between theme switches to reduce CPU spikes.",
    )
    parser.add_argument("--startup-timeout-s", type=float, default=12.0)
    parser.add_argument("--quick-close-timeout-s", type=float, default=3.0)
    parser.add_argument("--quick-close-destroy-ms", type=int, default=350)
    parser.add_argument("--max-ready-ms", type=float, default=4000.0)
    parser.add_argument("--max-avg-switch-ms", type=float, default=70.0)
    parser.add_argument("--max-p95-switch-ms", type=float, default=120.0)
    parser.add_argument("--max-switch-ms", type=float, default=280.0)
    parser.add_argument("--max-phase1-growth-kib", type=float, default=2048.0)
    parser.add_argument("--max-phase2-growth-kib", type=float, default=512.0)
    parser.add_argument("--max-total-growth-kib", type=float, default=4096.0)
    parser.add_argument("--max-peak-mib", type=float, default=64.0)
    args = parser.parse_args()

    if args.safe_mode:
        _apply_safe_mode_overrides(args)

    try:
        mod = importlib.import_module(str(args.module))
        editor_cls = getattr(mod, "JsonEditor")
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        print(f"stability_smoke: FAIL (failed to import editor module '{args.module}': {exc})")
        return 2

    try:
        quick_close_ok, quick_close_stderr = _run_quick_close_smoke(
            editor_cls,
            destroy_after_ms=args.quick_close_destroy_ms,
            timeout_s=args.quick_close_timeout_s,
        )
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        print(f"stability_smoke: FAIL (quick-close smoke exception: {exc})")
        return 2

    try:
        metrics = _run_theme_switch_smoke(
            editor_cls,
            switches=args.switches,
            startup_timeout_s=args.startup_timeout_s,
            switch_pause_ms=args.switch_pause_ms,
        )
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError) as exc:
        print(f"stability_smoke: FAIL (theme-switch smoke exception: {exc})")
        return 2

    print("stability_smoke summary")
    print(f"- module: {args.module}")
    print(f"- quick-close callback cleanup: {'PASS' if quick_close_ok else 'FAIL'}")
    if quick_close_stderr:
        print("- quick-close stderr captured:")
        for line in quick_close_stderr.splitlines()[:8]:
            print(f"  {line}")
    print(f"- loader ready observed: {metrics['ready']}")
    print(f"- loader ready time: {metrics['ready_ms']:.2f} ms")
    print(f"- switches: {metrics['switches']}")
    print(f"- switch pause: {max(0.0, float(args.switch_pause_ms)):.2f} ms")
    print(f"- switch avg: {metrics['avg_ms']:.2f} ms")
    print(f"- switch p95: {metrics['p95_ms']:.2f} ms")
    print(f"- switch max: {metrics['max_ms']:.2f} ms")
    print(f"- traced phase1 growth: {_fmt_mib(metrics['phase1_growth'])}")
    print(f"- traced phase2 growth: {_fmt_mib(metrics['phase2_growth'])}")
    print(f"- traced total growth: {_fmt_mib(metrics['total_growth'])}")
    print(f"- traced peak: {_fmt_mib(metrics['peak_bytes'])}")

    if not args.strict:
        return 0

    failures = []
    if not quick_close_ok:
        failures.append("quick-close callback cleanup reported Tcl callback errors")
    if not metrics["ready"]:
        failures.append("loader readiness was not observed within timeout")
    if metrics["ready_ms"] > float(args.max_ready_ms):
        failures.append(f"ready time {metrics['ready_ms']:.2f} ms > {args.max_ready_ms:.2f} ms")
    if metrics["avg_ms"] > float(args.max_avg_switch_ms):
        failures.append(
            f"switch avg {metrics['avg_ms']:.2f} ms > {args.max_avg_switch_ms:.2f} ms"
        )
    if metrics["p95_ms"] > float(args.max_p95_switch_ms):
        failures.append(
            f"switch p95 {metrics['p95_ms']:.2f} ms > {args.max_p95_switch_ms:.2f} ms"
        )
    if metrics["max_ms"] > float(args.max_switch_ms):
        failures.append(
            f"switch max {metrics['max_ms']:.2f} ms > {args.max_switch_ms:.2f} ms"
        )
    if metrics["phase1_growth"] > int(float(args.max_phase1_growth_kib) * 1024):
        failures.append(
            f"phase1 growth {_fmt_mib(metrics['phase1_growth'])} > "
            f"{float(args.max_phase1_growth_kib) / 1024.0:.2f} MiB"
        )
    if metrics["phase2_growth"] > int(float(args.max_phase2_growth_kib) * 1024):
        failures.append(
            f"phase2 growth {_fmt_mib(metrics['phase2_growth'])} > "
            f"{float(args.max_phase2_growth_kib) / 1024.0:.2f} MiB"
        )
    if metrics["total_growth"] > int(float(args.max_total_growth_kib) * 1024):
        failures.append(
            f"total growth {_fmt_mib(metrics['total_growth'])} > "
            f"{float(args.max_total_growth_kib) / 1024.0:.2f} MiB"
        )
    if metrics["peak_bytes"] > int(float(args.max_peak_mib) * 1024 * 1024):
        failures.append(f"peak traced memory {_fmt_mib(metrics['peak_bytes'])} > {args.max_peak_mib:.2f} MiB")

    if failures:
        print("stability_smoke strict gate: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("stability_smoke strict gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
