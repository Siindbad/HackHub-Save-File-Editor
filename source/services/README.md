# Services Suite

| Module | Purpose | When to Update |
| --- | --- | --- |
| `bug_report_api_service.py` | Handles bug-report API/browser submission operations, including screenshot upload and issue creation fallback behavior. | Bug-report GitHub API request flow, auth handling, or browser fallback behavior changes. |
| `bug_report_service.py` | Contains bug-report helper logic for markdown composition, screenshot validation/prep, issue URL construction (including optional body-query omission), and submit cooldown math. | Bug-report formatting, upload guardrails, or submission helper behavior changes. |
| `bug_report_ui_service.py` | Provides the bug-report dialog UI builder/orchestration, including screenshot picker, submit worker state updates, and themed dialog lifecycle wiring. | Bug-report dialog layout, UI interactions, or submit-flow UI orchestration behavior changes. |
| `edit_guard_service.py` | Compatibility shim that forwards legacy imports to `highlight_label_service.py` during the service rename transition. | Legacy import compatibility behavior changes. |
| `error_overlay_service.py` | Provides error-overlay UI helpers for pin placement, tint lifecycle, overlay teardown, and theme refresh behavior. | Error overlay/pin/tint rendering behavior changes. |
| `error_service.py` | Provides error-system helper logic for before/after suggestion parsing, overlay payload shaping, marker color rules, and theme-aware error palettes. | Error overlay payload formatting or marker/palette rule changes. |
| `footer_service.py` | Provides bottom-footer style and visual spec helpers used by badge/chip layout rendering. | Footer variant policy or chip spacing spec changes. |
| `highlight_label_service.py` | Provides edit-safety helpers for network list/context detection, key-rename guard payload shaping, and global JSON key/value label-policy detection/restore/highlight rules. | Highlight-label policy/rules, key-change payload formatting, or global JSON label/highlight behavior changes. |
| `input_mode_service.py` | Provides Input-mode helper logic for scalar detection, field-spec collection, value coercion, and nested path writes. | Input-mode field mapping/coercion behavior changes. |
| `json_error_diag_service.py` | Provides diagnostic note-to-system mapping and normalized diagnostics log entry writing helpers used by editor wrappers. | Diagnostic note routing or runtime diagnostics log-entry formatting behavior changes. |
| `json_error_highlight_render_service.py` | Provides JSON highlight render callbacks used by core decision logic to apply editor highlight tags and diagnostic log writes. | JSON highlight render wiring or callback contract changes. |
| `json_view_service.py` | Provides JSON-view helper behavior such as default no-file message rendering in the editor text widget. | JSON-view default messaging behavior changes. |
| `label_format_service.py` | Provides reusable label-format helpers for tree list display entries (including category-specific labels) and dict-key change detection payloads. | Tree label text policy, category label resolution, or key-change detection helper behavior changes. |
| `loader_service.py` | Provides startup-loader helper logic for statement pools, title variant/color mapping, and progress fill dimensions. | Startup loader line/title/fill helper behavior changes. |
| `runtime_log_service.py` | Provides shared text-log tail and latest-block readers used by crash and diagnostics report flows. | Runtime log parsing/tail extraction behavior changes. |
| `startup_loader_ui_service.py` | Provides startup-loader UI composition and widget wiring while preserving owner-managed progress/tick behavior. | Startup loader UI layout/wiring behavior changes. |
| `theme_asset_service.py` | Provides theme-related asset path helpers used by sprite/icon/theme resource lookups. | Theme asset path resolution logic changes. |
| `theme_service.py` | Provides centralized theme palettes and chip/color mapping helpers for SIINDBAD and KAMUE variants. | Theme color sets or variant mapping behavior changes. |
| `toolbar_service.py` | Provides toolbar helper logic for style resolution, button symbols, display labels, and width presets. | Toolbar style/label/symbol/width mapping behavior changes. |
| `tree_view_service.py` | Provides tree-view helper logic for label mapping, path formatting, selected-path text, and value-based toggle eligibility checks. | Tree display-label/path formatting or expand-toggle eligibility behavior changes. |
| `ui_build_service.py` | Provides main editor UI composition/wiring for tree pane, editor pane, footer controls, and startup-prewarm bootstrap hooks. | Primary editor UI assembly/wiring behavior changes. |
| `update_orchestrator_service.py` | Provides updater orchestration flow for demo/update checks while reusing owner callbacks and existing update helpers. | Update check orchestration or staged update-flow control changes. |
| `update_service.py` | Provides updater service facade exports consumed by UI entrypoints while core logic stays in `core/update_service.py`. | When updater API surface changes or facade exports are adjusted. |
| `update_ui_service.py` | Provides update-related UI dialog/overlay helpers for themed info/confirm prompts (including shared startup-check checkbox state), staged progress/percent rendering, rotating updater header text, and popup lifecycle handling. | Update prompt/overlay rendering behavior changes. |
| `windows_runtime_service.py` | Provides Windows-focused updater/runtime helpers for hidden process launch, installer script handoff (including hidden-window relaunch command), configurable restart-notice delay, and retryable atomic file writes. | Windows EXE update/install runtime behavior changes. |
