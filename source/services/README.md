# Services Suite

Last sync: 2026-03-01 (Phase 2 consolidation moved JSON lifecycle and INPUT workflow orchestration into facade masters with compatibility shims).

| Module | Purpose |
| --- | --- |
| `bug_report_manager.py` | Compatibility shim exposing legacy bug-report module symbols via `infra_facade` telemetry exports. |
| `document_service.py` | Compatibility shim exposing legacy document service symbols via `json_lifecycle_facade`. |
| `infra_facade.py` | Consolidated infrastructure facade for runtime, update pipeline, and telemetry/bug-report orchestration symbols. |
| `input_workflow_facade.py` | Consolidated INPUT workflow facade for INPUT mode render/find/diag orchestration plus game-specific INPUT style services. |
| `json_engine.py` | Compatibility shim exposing legacy `JSON_ENGINE` access via `json_lifecycle_facade`. |
| `json_lifecycle_facade.py` | Consolidated JSON lifecycle facade for document load/save, JSON diagnostics/repair, JSON view/find, and validation formatting services. |
| `presentation_facade.py` | Consolidated presentation facade for UI assembly, theme assets/colors, text-context actions, and tree services. |
| `registry.py` | Central `SERVICES` registry that initializes facade/master singleton instances for service access. |
| `runtime_service.py` | Compatibility shim exposing legacy runtime singleton access via `infra_facade`. |
| `tree_manager.py` | Compatibility shim exposing legacy tree singleton access via `presentation_facade`. |
| `update_orchestrator.py` | Compatibility shim exposing legacy update singleton access via `infra_facade`. |
