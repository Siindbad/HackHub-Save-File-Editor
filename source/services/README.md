# Services Suite

Last sync: 2026-02-28 (editor UI/input manager wiring expanded to route loader/pane-lock/asset/render dispatch orchestration through dedicated core services).

| Module | Purpose |
| --- | --- |
| `bug_report_manager.py` | Bug-report, crash-report, and diagnostics-log orchestration domain. |
| `document_service.py` | Document load/save/export and editor document mode-switch orchestration domain. |
| `editor_ui_core.py` | Core UI assembly domain for loader, toolbar, footer, startup loader UI, README popup rendering, and dispatch helpers. |
| `input_mode_manager.py` | INPUT mode rendering/find/diagnostics/value-mapping orchestration domain. |
| `json_engine.py` | JSON diagnostics, repair, path, apply/feedback, and syntax-rule orchestration domain. |
| `json_view_manager.py` | JSON view/render/find-navigation/text-find/find-orchestration domain. |
| `runtime_service.py` | Runtime paths/logs, token/env resolution, and OS/runtime helper orchestration domain. |
| `text_context_manager.py` | Text-context popup state/pointer/action/widget/menu-style orchestration domain. |
| `theme_manager.py` | Theme and INPUT style orchestration domain, including prewarm and RGBA cache flow. |
| `tree_manager.py` | Tree engine, mode policy, and tree-view behavior orchestration domain. |
| `update_orchestrator.py` | Full update pipeline orchestration domain (URL, headers, download, checksum, signature, UI, fallback). |
| `validation_engine.py` | Validation and formatting domain for input sanitization and label/version formatting helpers. |
