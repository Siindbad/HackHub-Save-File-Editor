# Services Suite

Last sync: 2026-02-20 (added cursor-restore diagnostics note routing bucket for autofix/apply cursor anchor triage).

| Module | Purpose |
| --- | --- |
| `bug_report_api_service.py` | Handles bug-report API/browser submission operations, including screenshot upload and issue creation fallback behavior. |
| `bug_report_service.py` | Contains bug-report helper logic for markdown composition, screenshot validation/prep, issue URL construction (including optional body-query omission), and submit cooldown math. |
| `bug_report_ui_service.py` | Provides the bug-report dialog UI builder/orchestration, including screenshot picker, submit worker state updates, and themed dialog lifecycle wiring. |
| `edit_guard_service.py` | Compatibility shim that forwards legacy imports to `highlight_label_service.py` during the service rename transition. |
| `error_overlay_service.py` | Provides error-overlay UI helpers for pin placement, tint lifecycle, overlay teardown, and theme refresh behavior. |
| `error_service.py` | Provides error-system helper logic for before/after suggestion parsing, overlay payload shaping, marker color rules, and theme-aware error palettes. |
| `footer_service.py` | Provides bottom-footer style and visual spec helpers used by badge/chip layout rendering. |
| `highlight_label_service.py` | Provides edit-safety helpers for network list/context detection, key-rename guard payload shaping, and global JSON key/value label-policy detection/restore/highlight rules. |
| `input_bank_style_service.py` | Provides Bank-specific Input-mode row discovery and themed style rendering (account/IBAN labels, provider pill, rounded balance input). |
| `input_mode_service.py` | Provides Input-mode helper logic for scalar detection, field-spec collection, value coercion, and nested path writes. |
| `json_error_diag_service.py` | Provides diagnostic note-to-system mapping and normalized diagnostics log entry writing helpers used by editor wrappers. |
| `json_error_highlight_render_service.py` | Provides JSON highlight render callbacks used by core decision logic to apply editor highlight tags and diagnostic log writes. |
| `json_view_service.py` | Provides JSON-view helper behavior such as default no-file message rendering in the editor text widget. |
| `label_format_service.py` | Provides reusable label-format helpers for tree list display entries (including category-specific labels) and dict-key change detection payloads. |
| `loader_service.py` | Provides startup-loader helper logic for statement pools, title variant/color mapping, and progress fill dimensions. |
| `runtime_log_service.py` | Provides shared text-log tail and latest-block readers used by crash and diagnostics report flows. |
| `startup_loader_ui_service.py` | Provides startup-loader UI composition and widget wiring while preserving owner-managed progress/tick behavior. |
| `theme_asset_service.py` | Provides theme-related asset path helpers used by sprite/icon/theme resource lookups. |
| `theme_service.py` | Provides centralized theme palettes and chip/color mapping helpers for SIINDBAD and KAMUE variants. |
| `toolbar_service.py` | Provides toolbar helper logic for style resolution, button symbols, display labels, and width presets. |
| `tree_mode_service.py` | Provides mode-scoped tree style application helpers so INPUT and JSON tree visuals can evolve independently with shared selection/data behavior. |
| `tree_view_service.py` | Provides tree-view helper logic for label mapping, path formatting, selected-path text, and value-based toggle eligibility checks. |
| `ui_build_service.py` | Provides main editor UI composition/wiring for tree pane, editor pane, footer controls, and startup-prewarm bootstrap hooks. |
| `update_orchestrator_service.py` | Provides updater orchestration flow for demo/update checks while reusing owner callbacks and existing update helpers. |
| `update_service.py` | Provides updater service facade exports consumed by UI entrypoints while core logic stays in `core/update_service.py`. |
| `update_ui_service.py` | Provides update-related UI dialog/overlay helpers for themed info/confirm prompts (including shared startup-check checkbox state), staged progress/percent rendering, rotating updater header text, and popup lifecycle handling. |
| `windows_runtime_service.py` | Provides Windows-focused updater/runtime helpers for hidden process launch, installer script handoff (including hidden-window relaunch command), configurable restart-notice delay, and retryable atomic file writes. |
