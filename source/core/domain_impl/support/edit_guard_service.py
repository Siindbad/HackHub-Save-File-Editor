"""Compatibility shim for the renamed highlight label service.

This module remains for older imports while active code uses
`services.highlight_label_service`.
"""

from core.domain_impl.support import highlight_label_service as _impl


def __getattr__(name):
    return getattr(_impl, name)


def __dir__():
    return sorted(set(globals().keys()) | set(dir(_impl)))
