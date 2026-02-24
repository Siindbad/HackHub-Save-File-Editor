import os
from typing import Any
from core.exceptions import EXPECTED_ERRORS
import logging
_LOG = logging.getLogger(__name__)


def read_text_file_tail(path: Any, max_chars: Any) -> Any:
    if not os.path.isfile(path):
        return ""
    limit = max(0, int(max_chars))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except EXPECTED_ERRORS as exc:
        _LOG.debug('expected_error', exc_info=exc)
        return ""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[-limit:]


def read_latest_block(text: Any, max_chars: Any, marker: Any="\n---\n") -> Any:
    source = str(text or "")
    if not source.strip():
        return ""
    idx = source.rfind(marker)
    if idx >= 0:
        block = source[idx + len(marker) :]
    else:
        block = source
    block = str(block or "").strip()
    if not block:
        return ""
    limit = max(0, int(max_chars))
    if limit > 0 and len(block) > limit:
        return block[-limit:]
    return block
