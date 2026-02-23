# Services Suite

Last sync: 2026-02-23 (toolbar service variant mapping cleaned to A/B-only behavior).

| Module | Purpose |
| --- | --- |
| `bug_report_api_service.py` | Handles bug-report API/browser submission operations, including screenshot upload, issue creation fallback behavior, strict HTTPS/host allowlist request guards, and optional Discord forum webhook mirror posting helpers (with screenshot-thumbnail payload wiring when available). |
| `bug_report_browser_service.py` | Provides bug-report browser fallback helpers for clipboard-first clean issue URL open behavior. |
| `bug_report_context_service.py` | Provides bug-report markdown context assembly helpers for diagnostics/runtime metadata payload composition. |
| `bug_report_cooldown_service.py` | Provides bug-report submit cooldown helpers for remaining-seconds math and submit timestamp normalization. |
| `bug_report_service.py` | Contains bug-report helper logic for markdown composition, screenshot validation/prep, issue URL construction (including optional body-query omission), and submit cooldown math. |
| `bug_report_ui_service.py` | Provides the bug-report dialog UI builder/orchestration, including screenshot picker, submit worker state updates (with Discord mirror sent/skipped/failed status feedback), and themed dialog lifecycle wiring. |
| `clipboard_service.py` | Provides reusable Tk clipboard copy helpers for trimmed text payloads with error-safe fallback behavior. |
| `crash_logging_service.py` | Provides crash-log append and one-time user notice helpers for unhandled exception hooks. |
| `crash_offer_service.py` | Provides crash-report offer scheduling and prompt-handling helpers for pending payload confirmation flow. |
| `crash_report_service.py` | Provides crash-report helper logic for log-tail/latest-block extraction, prompt-state persistence, and pending crash payload hash gating. |
| `diag_log_housekeeping_service.py` | Provides diagnostics log path/date suffix and retention cleanup helpers for runtime/temp legacy files. |
| `document_io_service.py` | Provides JSON and `.hhsav` document I/O helpers for load, save-payload serialization, and deterministic gzip export handoff. |
| `edit_guard_service.py` | Compatibility shim that forwards legacy imports to `highlight_label_service.py` during the service rename transition. |
| `editor_mode_switch_service.py` | Provides editor mode-switch decision helpers for rebuild gating, including root-hide and INPUT Network hidden-group policy changes, plus INPUT refresh-skip checks to reduce flicker while preserving correctness. |
| `editor_purge_service.py` | Hosts delegated `JsonEditor` logic extracted during structural purge so the main editor class remains orchestration-focused instead of embedding large business-logic blocks. |
| `error_hook_service.py` | Provides unhandled exception hook wiring helpers for sys/thread/Tk callbacks and previous-hook forwarding safeguards. |
| `error_overlay_service.py` | Provides error-overlay UI helpers for pin placement, tint lifecycle, overlay teardown, and theme refresh behavior. |
| `error_service.py` | Provides error-system helper logic for before/after suggestion parsing, overlay payload shaping, marker color rules, and theme-aware error palettes. |
| `footer_service.py` | Provides bottom-footer style/spec helpers plus vectorized badge-region detection and pooled badge widget reuse for theme-switch stability. |
| `highlight_label_service.py` | Provides edit-guard helpers for network list/context detection, key-rename guard payload shaping, and global JSON key/value label-policy detection/restore/highlight rules. |
| `input_bank_style_service.py` | Provides Bank-specific Input-mode row discovery and themed style rendering (account/IBAN labels, provider pill, rounded balance input) with editor FONT-linked size scaling support. |
| `input_database_style_service.py` | Provides Database Grades Input-mode matrix detection/rendering with editability-aware cells (editable inputs vs centered read-only values) and editor FONT-linked size scaling support. |
| `input_mode_diag_service.py` | Provides INPUT-mode diagnostics logging helpers for apply failure/result/trace runtime entries. |
| `input_mode_find_service.py` | Provides INPUT-mode find helpers for widget text indexing, entry focus lookup, and scroll-into-view behavior. |
| `input_mode_service.py` | Provides Input-mode helper logic for scalar detection, field-spec collection, value coercion, and nested path writes. |
| `input_network_firewall_style_service.py` | Provides Network FIREWALL Input-mode Concept-2 styled row detection/rendering with non-editable identity fields, editable rule Port/Allowed inputs, and editor FONT-linked size scaling support. |
| `input_network_router_style_service.py` | Provides Network ROUTER Input-mode Concept-2 styled row detection/rendering with framed sections, editable port/state fields, and editor FONT-linked size scaling support. |
| `input_suspicion_phone_style_service.py` | Provides Suspicion Input-mode phone-art renderer with one centered editable value field anchored on theme-specific SIN/KAMUE phone PNG assets and editor FONT-linked size scaling support. |
| `json_apply_commit_service.py` | Provides JSON apply-commit helpers for post-validation value commit, subtree refresh, and status/reset updates. |
| `json_closer_symbol_service.py` | Provides JSON closer-tail symbol helpers for invalid-symbol detection, first-column targeting, and deterministic fix transforms. |
| `json_colon_comma_service.py` | Provides JSON comma/colon/closer rule helpers for span detection and deterministic fix transforms used by diagnostics flows. |
| `json_diagnostics_service.py` | Hosts delegated high-level JSON diagnostics and highlight orchestration extracted from `JsonEditor`, including parse-error interpretation and diagnostic routing wrappers. |
| `json_edit_flow_service.py` | Provides JSON edit-flow helper checks for auto-apply eligibility across parse and validation guard paths. |
| `json_error_diag_service.py` | Provides diagnostic note-to-system mapping and normalized diagnostics log entry writing helpers used by editor wrappers. |
| `json_error_highlight_render_service.py` | Provides JSON highlight render callbacks used by core decision logic to apply editor highlight tags and diagnostic log writes. |
| `json_find_nav_service.py` | Provides JSON find-navigation helpers for previous-root collapse behavior when category traversal changes. |
| `json_find_service.py` | Provides deterministic JSON-mode find traversal helpers that return concrete data paths for Find Next cycling. |
| `json_nearby_line_service.py` | Provides shared nearby-line scan helpers used by JSON diagnostics to find first matching current/previous non-empty lines. |
| `json_open_symbol_service.py` | Provides JSON open-symbol tail helpers for invalid-symbol span detection and deterministic symbol-run removal. |
| `json_parse_feedback_service.py` | Provides shared parse-error feedback handlers for apply/live flows, including overlay/highlight/log fallback behavior. |
| `json_path_service.py` | Provides nested JSON path get/set helpers used by editor value read/write flows. |
| `json_property_key_rule_service.py` | Provides JSON property-key quote and invalid-escape rule helpers for diagnostics span detection and repair transforms. |
| `json_quoted_item_tail_service.py` | Provides JSON quoted-item tail rule helpers for invalid trailing-symbol span detection and fix transforms. |
| `json_repair_service.py` | Hosts delegated JSON repair and symbol-fix helpers extracted from `JsonEditor`, including nearby-line recovery and malformed token cleanup flows. |
| `json_scalar_tail_service.py` | Provides JSON scalar-tail rule helpers for split/invalid-tail detection and deterministic trailing-symbol fix transforms. |
| `json_text_find_service.py` | Provides JSON text-view find helpers for in-buffer next-match traversal and focus handoff behavior. |
| `json_top_level_close_service.py` | Provides JSON top-level close-symbol tail helpers for EOF comma/tail span detection and fix transforms. |
| `json_validation_feedback_service.py` | Provides shared JSON spacing/email/phone validation feedback render helpers for apply/live edit flows. |
| `json_view_render_service.py` | Provides JSON-view render orchestration helpers for text-buffer replacement plus deferred lock/value highlight scheduling. |
| `json_view_service.py` | Provides JSON-view helper behavior such as default no-file message rendering in the editor text widget. |
| `label_format_service.py` | Provides reusable label-format helpers for tree list display entries (including category-specific labels) and dict-key change detection payloads. |
| `loader_service.py` | Provides startup-loader helper logic for statement pools, title variant/color mapping, and progress fill dimensions. |
| `runtime_log_service.py` | Provides shared text-log tail and latest-block readers used by crash and diagnostics report flows. |
| `runtime_paths_service.py` | Provides runtime data directory path resolution helpers with platform-aware base fallbacks and optional create behavior. |
| `startup_loader_ui_service.py` | Provides startup-loader UI composition and widget wiring while preserving owner-managed progress/tick behavior. |
| `text_context_action_service.py` | Provides text-context action selection and click-dispatch helpers for enabled-state routing. |
| `text_context_pointer_service.py` | Provides text-context pointer/action resolution helpers for widget-walk and popup hit-testing behavior. |
| `text_context_state_service.py` | Provides text-context state helpers for selection, clipboard, and undo/redo availability checks. |
| `text_context_widget_service.py` | Provides text-context widget relationship helpers for popup child-path checks. |
| `theme_asset_service.py` | Provides theme-related asset path helpers used by sprite/icon/theme resource lookups. |
| `theme_service.py` | Provides centralized theme palettes/chip mapping plus titlebar no-op guards and idle-batched footer refresh orchestration for stable switch latency. |
| `token_env_service.py` | Provides environment-token resolution helpers for updater and bug-report fallback behavior. |
| `toolbar_service.py` | Provides toolbar helper logic for style resolution, button symbols, display labels, and width presets. |
| `tree_engine_service.py` | Provides shared tree engine mechanics for child population, marker refresh, and click/double-click toggle behavior used by both JSON and INPUT modes. |
| `tree_mode_service.py` | Provides mode-scoped tree style application helpers so INPUT and JSON tree visuals can evolve independently with shared selection/data behavior. |
| `tree_policy_service.py` | Provides mode-scoped tree behavior policy helpers for hidden roots, INPUT disable/no-expand rules (including Network subgroup locks), and INPUT-only red-arrow markers while JSON remains fully expandable without red markers. |
| `tree_view_service.py` | Provides tree-view helper logic for label mapping, path formatting, selected-path text, and value-based toggle eligibility checks. |
| `ui_build_service.py` | Provides main editor UI composition/wiring for tree pane, editor pane, footer controls, startup-prewarm bootstrap hooks, and editor mode/theme/header/input panel builder construction. |
| `ui_dispatch_service.py` | Provides UI-thread dispatch helpers for async/sync callback execution via Tk `after` scheduling. |
| `update_asset_service.py` | Provides update asset download/validation helpers for ZIP/EXE sanity checks, checksum verification, and signature handoff. |
| `update_checksum_service.py` | Provides update checksum parsing/retrieval helpers for SHA-256 extraction and candidate checksum asset lookup. |
| `update_diag_service.py` | Provides update diagnostics log-entry helpers for normalized failure context, mode, and exception-chain details. |
| `update_download_service.py` | Provides update download helper wiring that injects headers and retry-policy callbacks into shared download routines. |
| `update_fallback_service.py` | Provides manual-update fallback prompt/open helpers for release download page routing and status feedback. |
| `update_headers_service.py` | Provides update request-header helpers with bearer-token wiring from runtime token policy. |
| `update_orchestrator_service.py` | Provides updater orchestration flow for demo/update checks while reusing owner callbacks and existing update helpers. |
| `update_release_info_service.py` | Provides latest-release metadata parse/validation helpers for API payload handling. |
| `update_service.py` | Provides updater service facade exports consumed by UI entrypoints while core logic stays in `core/update_service.py`. |
| `update_signature_service.py` | Provides downloaded-update signature verification helpers for Windows Authenticode trust checks. |
| `update_ui_service.py` | Provides update-related UI dialog/overlay helpers for themed info/confirm prompts (including shared startup-check checkbox state), staged progress/percent rendering, rotating updater header text, and popup lifecycle handling. |
| `update_url_service.py` | Provides release/update URL builder helpers for latest API and release-asset download links. |
| `update_version_service.py` | Provides update dist-version resolution helpers with release-tag preference and version-file fallback. |
| `version_format_service.py` | Provides version parsing/formatting helpers used by update and display flows. |
| `windows_runtime_service.py` | Provides Windows-focused updater/runtime helpers for hidden process launch, installer script handoff (including hidden-window relaunch command), strict Program Files elevation detection, direct EXE replacement fallback, ZIP EXE hash-verify apply guard, configurable restart-notice delay, and retryable atomic file writes. |
