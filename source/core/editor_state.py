"""Structured runtime state buckets for JsonEditor flags."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UIState:
    """Widget and presentation flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentState:
    """Document and find/index flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UpdateState:
    """Update/startup-loader flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiagnosticsState:
    """Diagnostics/error tracking flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InputState:
    """Input-mode flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TreeState:
    """Tree engine/style flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BugReportState:
    """Bug-report and footer-chip flags."""

    flags: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EditorState:
    """Top-level grouped state container to avoid scattered runtime flags."""

    ui: UIState = field(default_factory=UIState)
    document: DocumentState = field(default_factory=DocumentState)
    update: UpdateState = field(default_factory=UpdateState)
    diagnostics: DiagnosticsState = field(default_factory=DiagnosticsState)
    input_mode: InputState = field(default_factory=InputState)
    tree: TreeState = field(default_factory=TreeState)
    bug_report: BugReportState = field(default_factory=BugReportState)

    def _bucket_for_name(self, name: str) -> dict[str, Any]:
        key = str(name or "")
        match key:
            case "data" | "path" | "item_to_path":
                return self.document.flags
            case _ if key.startswith("_input_mode_"):
                return self.input_mode.flags
            case _ if key.startswith("_tree_"):
                return self.tree.flags
            case _ if key.startswith("_update_") or key.startswith("_startup_") or key.startswith("_theme_prewarm_"):
                return self.update.flags
            case _ if key.startswith("_bug_") or key.startswith("_credit_") or key.startswith("_footer_"):
                return self.bug_report.flags
            case _ if key.startswith("_diag_") or key.startswith("_error_") or key.startswith("_crash_"):
                return self.diagnostics.flags
            case _ if key.startswith("_find_") or key.startswith("_list_") or key in {"find_matches", "find_index", "last_find_query"}:
                return self.document.flags
            case _ if key.startswith("_editor_") or key.startswith("_toolbar_") or key.startswith("_header_") or key.startswith("_logo_"):
                return self.ui.flags
            case _:
                return self.ui.flags

    def set_flag(self, name: str, value: Any) -> None:
        self._bucket_for_name(name)[name] = value

    def has_flag(self, name: str) -> bool:
        return name in self._bucket_for_name(name)

    def get_flag(self, name: str, default: Any = None) -> Any:
        return self._bucket_for_name(name).get(name, default)
