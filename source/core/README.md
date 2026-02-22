# Core Suite

Last sync: 2026-02-22 (version prep to 1.3.6 plus startup loader teardown hardening for quick-close stability smoke).

| Module | Purpose |
| --- | --- |
| `constants.py` | Defines shared static configuration values used across editor components, including updater/bug-report token env names, bug-report destination, screenshot-upload limits, submit cooldown settings, optional bug-report Discord forum webhook/tag env names, and mode-scoped tree policy category/key sets. |
| `display_profile.py` | Provides display-scale detection and window/profile geometry helper logic. |
| `json_diagnostics.py` | Contains JSON diagnostic parsing and typo/symbol recovery helper rules. |
| `json_error_diagnostics_core.py` | Provides centralized JSON parse-diagnostic builders/formatters used by editor wrappers. |
| `json_error_highlight_core.py` | Provides JSON highlight decision flow while delegating UI render/log callbacks to services. |
| `layout_topbar.py` | Contains topbar spacing, compaction, and centering calculation helpers. |
| `startup_loader.py` | Implements startup loader progress, timing, and prewarm policy math. |
| `update_service.py` | Implements updater retry/backoff/error classification (including Windows file-lock/access guidance) and download primitives. |
