import os
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def resource_base_dir(module_resource_base_dir_fn: Any) -> Any:
    try:
        return module_resource_base_dir_fn()
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return os.getcwd()


def siindbad_b_sprite_dir(base_dir: Any) -> Any:
    return os.path.join(base_dir, "assets", "buttons", "variants", "B", "r5_sprites")
