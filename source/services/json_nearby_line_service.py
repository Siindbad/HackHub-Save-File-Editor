"""Shared nearby-line scanning helper for JSON diagnostics."""
from typing import Any


def find_nearby_line(
    lineno: Any,
    lookback: Any,
    get_line_text_fn: Any,
    predicate_fn: Any,
    expected_errors: Any,
    strip_text: Any=False,
    predicate_kwargs_provider: Any=None,
) -> Any:
    """Find first matching line among current line + previous non-empty lines."""
    if not lineno:
        return None, None
    candidates = []
    try:
        current = get_line_text_fn(lineno)
        if strip_text:
            current = current.strip()
        candidates.append((lineno, current))
    except expected_errors:
        pass

    line = max(lineno - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        try:
            txt = get_line_text_fn(line)
            check = txt.strip() if strip_text else txt
        except expected_errors:
            break
        if check:
            candidates.append((line, txt if not strip_text else check))
            scanned += 1
        line -= 1

    for ln, txt in candidates:
        kwargs = {}
        if callable(predicate_kwargs_provider):
            kwargs = dict(predicate_kwargs_provider(ln, txt) or {})
        if predicate_fn(txt, **kwargs):
            return ln, txt
    return None, None
