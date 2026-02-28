"""Compatibility shim for consolidated telemetry core."""

from .telemetry_core import *  # noqa: F401,F403
from .telemetry_core import _open_https_request  # noqa: F401
