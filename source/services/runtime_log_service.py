import os


def read_text_file_tail(path, max_chars):
    if not os.path.isfile(path):
        return ""
    limit = max(0, int(max_chars))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError, KeyError, IndexError, ImportError):
        return ""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[-limit:]


def read_latest_block(text, max_chars, marker="\n---\n"):
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
