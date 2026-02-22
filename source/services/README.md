# Services Suite

Last sync: 2026-02-22 (exception-hardening sweep across service fallback, diagnostics, and UI safety paths).

| Module | Purpose |
| --- | --- |
| `bug_report_api_service.py` | Handles bug-report API/browser submission operations, including screenshot upload, issue creation fallback behavior, strict HTTPS/host allowlist request guards, and optional Discord forum webhook mirror posting helpers (with screenshot-thumbnail payload wiring when available). |
| `bug_report_service.py` | Contains bug-report helper logic for markdown composition, screenshot validation/prep, issue URL construction (including optional body-query omission), and submit cooldown math. |
| `bug_report_ui_service.py` | Provides the bug-report dialog UI builder/orchestration, including screenshot picker, submit worker state updates (with Discord mirror sent/skipped/failed status feedback), and themed dialog lifecycle wiring. |
| `edit_guard_service.py` | Compatibility shim that forwards legacy imports to `highlight_label_service.py` during the service rename transition. |
| `editor_mode_switch_service.py` | Provides editor mode-switch decision helpers for rebuild gating and INPUT refresh-skip checks to reduce flicker while preserving correctness. |
| `error_overlay_service.py` | Provides error-overlay UI helpers for pin placement, tint lifecycle, overlay teardown, and theme refresh behavior. |
| `error_service.py` | Provides error-system helper logic for before/after suggestion parsing, overlay payload shaping, marker color rules, and theme-aware error palettes. |
| `footer_service.py` | Provides bottom-footer style and visual spec helpers used by badge/chip layout rendering. |
| `highlight_label_service.py` | Provides edit-safety helpers for network list/context detection, key-rename guard payload shaping, and global JSON key/value label-policy detection/restore/highlight rules. |
| `input_bank_style_service.py` | Provides Bank-specific Input-mode row discovery and themed style rendering (account/IBAN labels, provider pill, rounded balance input) with editor FONT-linked size scaling support. |
| `input_database_style_service.py` | Provides Database Grades Input-mode matrix detection/rendering with editability-aware cells (editable inputs vs centered read-only values) and editor FONT-linked size scaling support. |
| `input_mode_service.py` | Provides Input-mode helper logic for scalar detection, field-spec collection, value coercion, and nested path writes. |
| `input_network_firewall_style_service.py` | Provides Network FIREWALL Input-mode Concept-2 styled row detection/rendering with non-editable identity fields, editable rule Port/Allowed inputs, and editor FONT-linked size scaling support. |
| `input_network_router_style_service.py` | Provides Network ROUTER Input-mode Concept-2 styled row detection/rendering with framed sections, editable port/state fields, and editor FONT-linked size scaling support. |
| `input_suspicion_phone_style_service.py` | Provides Suspicion Input-mode phone-art renderer with one centered editable value field anchored on theme-specific SIN/KAMUE phone PNG assets and editor FONT-linked size scaling support. |
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
| `tree_engine_service.py` | Provides shared tree engine mechanics for child population, marker refresh, and click/double-click toggle behavior used by both JSON and INPUT modes. |
| `tree_mode_service.py` | Provides mode-scoped tree style application helpers so INPUT and JSON tree visuals can evolve independently with shared selection/data behavior. |
| `tree_policy_service.py` | Provides mode-scoped tree behavior policy helpers for hidden roots, INPUT disable/no-expand rules (including Network subgroup locks), and INPUT-only red-arrow markers while JSON remains fully expandable without red markers. |
| `tree_view_service.py` | Provides tree-view helper logic for label mapping, path formatting, selected-path text, and value-based toggle eligibility checks. |
| `ui_build_service.py` | Provides main editor UI composition/wiring for tree pane, editor pane, footer controls, startup-prewarm bootstrap hooks, and editor mode/theme/header/input panel builder construction. |
| `update_orchestrator_service.py` | Provides updater orchestration flow for demo/update checks while reusing owner callbacks and existing update helpers. |
| `update_service.py` | Provides updater service facade exports consumed by UI entrypoints while core logic stays in `core/update_service.py`. |
| `update_ui_service.py` | Provides update-related UI dialog/overlay helpers for themed info/confirm prompts (including shared startup-check checkbox state), staged progress/percent rendering, rotating updater header text, and popup lifecycle handling. |
| `windows_runtime_service.py` | Provides Windows-focused updater/runtime helpers for hidden process launch, installer script handoff (including hidden-window relaunch command), configurable restart-notice delay, and retryable atomic file writes. |
