"""Central service registry for facade/master singleton instances."""

from __future__ import annotations

from dataclasses import dataclass

# Consolidation lock: do not add new top-level files under services/ unless a
# manual architecture override explicitly permits raising the core/services
# combined 90-file ceiling.
from services import infra_facade
from services import input_workflow_facade
from services import json_lifecycle_facade
from services import presentation_facade


@dataclass(frozen=True)
class ServiceRegistry:
    """Registry containing all service facade/master singleton instances."""

    editor_ui: presentation_facade.EditorUICore
    theme: presentation_facade.ThemeManager
    text_context: presentation_facade.TextContextManager
    tree: presentation_facade.TreeManager
    runtime: infra_facade.RuntimeService
    update: infra_facade.UpdateOrchestrator
    telemetry: infra_facade.TelemetryService
    document: json_lifecycle_facade.DocumentService
    input_workflow: input_workflow_facade.InputWorkflowFacade
    input_mode: input_workflow_facade.InputModeManager
    json_engine: json_lifecycle_facade.JsonEngine
    json_view: json_lifecycle_facade.JsonViewManager
    validation: json_lifecycle_facade.ValidationEngine
    json_lifecycle: json_lifecycle_facade.JsonLifecycleFacade


def _build_registry() -> ServiceRegistry:
    editor_ui = presentation_facade.EditorUICore()
    theme = presentation_facade.ThemeManager()
    text_context = presentation_facade.TextContextManager()
    tree = presentation_facade.TreeManager()
    runtime = infra_facade.RuntimeService()
    update = infra_facade.UpdateOrchestrator()
    telemetry = infra_facade.TelemetryService()
    input_workflow = input_workflow_facade.InputWorkflowFacade()
    json_lifecycle = json_lifecycle_facade.JsonLifecycleFacade()
    registry = ServiceRegistry(
        editor_ui=editor_ui,
        theme=theme,
        text_context=text_context,
        tree=tree,
        runtime=runtime,
        update=update,
        telemetry=telemetry,
        document=json_lifecycle.document,
        input_workflow=input_workflow,
        input_mode=input_workflow_facade.InputModeManager(),
        json_engine=json_lifecycle.json_engine,
        json_view=json_lifecycle.json_view,
        validation=json_lifecycle.validation,
        json_lifecycle=json_lifecycle,
    )
    presentation_facade._bind_singletons(
        editor_ui=registry.editor_ui,
        theme=registry.theme,
        text_context=registry.text_context,
        tree=registry.tree,
    )
    infra_facade._bind_singletons(
        runtime=registry.runtime,
        update=registry.update,
        telemetry=registry.telemetry,
    )
    return registry


SERVICES = _build_registry()
