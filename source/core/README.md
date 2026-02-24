# Core Suite

Last sync: 2026-02-24 (runtime path-safety hardening, windows runtime JSON helper sync, and bug-report Discord attachment flow updates).

| Module | Purpose |
| --- | --- |
| `constants.py` | Defines shared static configuration values used across editor components, including updater/bug-report token env names, bug-report destination, screenshot-upload limits, submit cooldown settings, input sanitization limits/character policy, optional bug-report Discord forum webhook/tag env names, and mode-scoped tree policy category/key sets. |
| `display_profile.py` | Provides display-scale detection and window/profile geometry helper logic. |
| `editor_state.py` | Defines grouped runtime state dataclasses (`UIState`, `DocumentState`, `UpdateState`, and related buckets) plus centralized flag routing used by `JsonEditor`. |
| `exceptions.py` | Defines shared app exception types and expected-error tuples used by service/core modules. |
| `json_diagnostics.py` | Contains JSON diagnostic parsing and typo/symbol recovery helper rules. |
| `json_error_diagnostics_core.py` | Provides centralized JSON parse-diagnostic builders/formatters used by editor wrappers. |
| `json_error_highlight_core.py` | Provides JSON highlight decision flow while delegating UI render/log callbacks to services. |
| `layout_topbar.py` | Contains topbar spacing, compaction, and centering calculation helpers. |
| `startup_loader.py` | Implements startup loader progress, timing, and prewarm policy math. |
| `update_service.py` | Compatibility re-export for updater retry/backoff/error/download helpers owned by `core/domain_impl/infra/update_service.py`. |
