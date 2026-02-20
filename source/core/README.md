# Core Suite

Simple reference for shared core modules in `core/`.
Helper-note policy: keep short inline helper comments in sync whenever core logic changes.
Last sync: 2026-02-19 (token-scope hardening sync).

| Module | Purpose | When to Update |
| --- | --- | --- |
| `constants.py` | Defines shared static configuration values used across editor components, including updater/bug-report token env names, bug-report destination, screenshot-upload limits, and submit cooldown settings. | When app-level constants or defaults change. |
| `display_profile.py` | Provides display-scale detection and window/profile geometry helper logic. | UI scaling, DPI, or geometry behavior changes. |
| `json_diagnostics.py` | Contains JSON diagnostic parsing and typo/symbol recovery helper rules. | JSON diagnostics or fix-heuristic updates. |
| `json_error_diagnostics_core.py` | Provides centralized JSON parse-diagnostic builders/formatters used by editor wrappers. | JSON diagnostic decision/formatting behavior changes. |
| `json_error_highlight_core.py` | Provides JSON highlight decision flow while delegating UI render/log callbacks to services. | JSON error highlight decision/routing behavior changes. |
| `layout_topbar.py` | Contains topbar spacing, compaction, and centering calculation helpers. | Toolbar layout behavior changes. |
| `startup_loader.py` | Implements startup loader progress, timing, and prewarm policy math. | Loader timing/progress policy updates. |
| `update_service.py` | Implements updater retry/backoff/error classification (including Windows file-lock/access guidance) and download primitives. | Updater pipeline behavior or Windows update error-messaging rules change. |
