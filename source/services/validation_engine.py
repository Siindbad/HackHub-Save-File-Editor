"""Validation and format domain module."""

from core.domain_impl.support import highlight_label_service
from core.domain_impl.support import label_format_service
from core.domain_impl.support import version_format_service
from core.domain_impl.json import json_diagnostics_core as json_validation_feedback_service
from core.domain_impl.json import json_io_core as validation_service


class ValidationEngine:
    highlight_label_service = highlight_label_service
    json_validation_feedback_service = json_validation_feedback_service
    label_format_service = label_format_service
    validation_service = validation_service
    version_format_service = version_format_service


VALIDATION = ValidationEngine()
