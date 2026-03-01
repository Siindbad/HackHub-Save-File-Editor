"""Service domain modules with compatibility aliases for consolidated facades."""

import sys
from importlib import import_module

from services.registry import SERVICES

editor_ui_core = import_module("services.presentation_facade")
text_context_manager = import_module("services.presentation_facade")
theme_manager = import_module("services.presentation_facade")
input_mode_manager = import_module("services.input_workflow_facade")
json_view_manager = import_module("services.json_lifecycle_facade")
validation_engine = import_module("services.json_lifecycle_facade")

sys.modules[f"{__name__}.editor_ui_core"] = editor_ui_core
sys.modules[f"{__name__}.text_context_manager"] = text_context_manager
sys.modules[f"{__name__}.theme_manager"] = theme_manager
sys.modules[f"{__name__}.input_mode_manager"] = input_mode_manager
sys.modules[f"{__name__}.json_view_manager"] = json_view_manager
sys.modules[f"{__name__}.validation_engine"] = validation_engine

__all__ = [
    "SERVICES",
    "editor_ui_core",
    "input_mode_manager",
    "json_view_manager",
    "text_context_manager",
    "theme_manager",
    "validation_engine",
]
