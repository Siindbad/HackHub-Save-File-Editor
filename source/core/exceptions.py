"""Shared exception classes and expected-error tuple for services/core."""

from __future__ import annotations

from typing import Final, TypeAlias


class AppError(Exception):
    """Base class for expected application-layer failures."""


class AppRuntimeError(RuntimeError, AppError):
    """Raised for runtime operation failures with user-facing context."""


EXPECTED_ERRORS: TypeAlias = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    ImportError,
)

# Named alias for modules that prefer constant-style typing.
EXPECTED_ERRORS_FINAL: Final = EXPECTED_ERRORS
