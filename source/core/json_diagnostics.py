import difflib
import re
from typing import Callable, Optional, Tuple


LineGetter = Callable[[int], str]
PrevNonEmptyLineFinder = Callable[[int], Optional[int]]
# Core note: this module is intentionally pure and line-oriented so editor and tests
# can reuse the same diagnostic decisions without Tk/runtime side effects.


def expected_closer_before_position(
    line_getter: LineGetter,
    target_line: int,
    target_col: int,
) -> Optional[str]:
    """Return expected closer at a position using the active open-bracket stack."""
    try:
        target_line = max(int(target_line), 1)
        target_col = max(int(target_col), 0)
    except Exception:
        return None

    stack = []
    in_string = False
    escape = False
    for ln in range(1, target_line + 1):
        raw = str(line_getter(ln) or "")
        limit = target_col if ln == target_line else len(raw)
        if limit < 0:
            limit = 0
        for idx, ch in enumerate(raw):
            if idx >= limit:
                break
            if escape:
                escape = False
                continue
            if in_string:
                if ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch in "{[":
                stack.append(ch)
            elif ch in "}]":
                if not stack:
                    continue
                top = stack[-1]
                if (top == "{" and ch == "}") or (top == "[" and ch == "]"):
                    stack.pop()
                else:
                    # Keep stack intact so expected closer still points to
                    # the active unmatched container.
                    continue
    if not stack:
        return None
    return "}" if stack[-1] == "{" else "]"


def find_wrong_closing_symbol_line(
    line_getter: LineGetter,
    lineno: int,
    lookback: int = 2,
) -> Optional[Tuple[int, int, int, str, str, str, str]]:
    """Detect mismatched closing symbol, e.g. `]` when `}` is expected."""
    if not lineno:
        return None

    candidates = [max(int(lineno), 1)]
    line = max(int(lineno) - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        text = str(line_getter(line) or "")
        if text.strip():
            candidates.append(line)
            scanned += 1
        line -= 1

    for ln in candidates:
        raw = str(line_getter(ln) or "")
        stripped = raw.strip()
        if not stripped:
            continue
        # Skip normal property lines; this rule is for standalone bad token
        # lines where a closer was expected.
        if stripped.startswith('"') and ":" in stripped:
            continue
        first_col = None
        for idx, ch in enumerate(raw):
            if not ch.isspace():
                first_col = idx
                break
        if first_col is None:
            continue
        expected = expected_closer_before_position(line_getter, ln, first_col)
        if not expected:
            continue
        found = raw[first_col]
        if found == expected:
            continue
        run_end = first_col
        while run_end < len(raw):
            ch = raw[run_end]
            if ch.isspace() or ch in ('"', "'"):
                break
            run_end += 1
        if run_end <= first_col:
            run_end = first_col + 1
        bad_token = raw[first_col:run_end]
        fixed = raw[:first_col] + expected + raw[run_end:]
        return ln, first_col, run_end, bad_token, expected, stripped, fixed.strip()
    return None


def find_missing_list_close_before_object_end(
    line_getter: LineGetter,
    prev_non_empty_line_before: PrevNonEmptyLineFinder,
    lineno: int,
    lookback: int = 4,
) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    """Detect missing `]` where a key line ends with `[` before `}`.

    Returns (line, insert_col, before, after) and prefers the key line:
        Before: "likedPosts": [
        After:  "likedPosts": []
    """
    if not lineno:
        return None, None, None, None

    candidate_lines = [max(int(lineno), 1)]
    line = max(int(lineno) - 1, 1)
    scanned = 0
    while line >= 1 and scanned < lookback:
        text = str(line_getter(line) or "")
        if text.strip():
            candidate_lines.append(line)
            scanned += 1
        line -= 1

    for ln in candidate_lines:
        # Pattern target: key line ending with "[" followed by a closer-only line.
        raw = str(line_getter(ln) or "")
        stripped = raw.strip()
        if not stripped or not stripped.startswith("}"):
            continue
        prev_ln = prev_non_empty_line_before(ln)
        if not prev_ln:
            continue
        prev_raw = str(line_getter(prev_ln) or "")
        prev_text = prev_raw.strip()
        prev_compact = "".join(prev_text.split())
        if prev_text == "[" or prev_compact.endswith(":["):
            bracket_col = prev_raw.rfind("[")
            if bracket_col >= 0:
                fixed_raw = prev_raw[:bracket_col] + "[]" + prev_raw[bracket_col + 1 :]
                return prev_ln, int(bracket_col + 1), prev_text, fixed_raw.strip()
            # Fallback if line was normalized unexpectedly.
            return prev_ln, len(prev_raw.rstrip()), prev_text, (prev_text + "]")

    return None, None, None, None


def suggest_json_literal_from_token(token) -> Optional[str]:
    token_l = str(token or "").strip().lower()
    if not token_l:
        return None
    literals = ("true", "false", "null")
    if token_l in literals:
        return token_l
    # Direct close-match typo recovery (e.g. "flase" -> "false").
    close = difflib.get_close_matches(token_l, literals, n=1, cutoff=0.62)
    if close:
        return close[0]
    # Missing-leading-char style typo (e.g. "rue" -> "true").
    for lit in literals:
        if lit.endswith(token_l) and (len(lit) - len(token_l)) <= 2:
            return lit
    return None


def boolean_literal_typo_diagnostic(line_text) -> Optional[dict]:
    if not line_text:
        return None
    raw = str(line_text).rstrip()
    # Match object member with a bareword token value.
    m = re.match(
        r'^(?P<head>\s*"[^"]+"\s*:\s*)(?P<token>[A-Za-z_][A-Za-z0-9_]*)(?P<tail>\s*,?\s*)$',
        raw,
    )
    if not m:
        return None
    token = m.group("token") or ""
    suggested = suggest_json_literal_from_token(token)
    if not suggested:
        return None
    if token.lower() == suggested:
        return None
    head = m.group("head") or ""
    tail = m.group("tail") or ""
    start_col = len(head)
    end_col = start_col + len(token)
    after = f"{head}{suggested}{tail}"
    return {
        "start_col": start_col,
        "end_col": end_col,
        "after": after,
        "suggested": suggested,
    }


def find_nearby_boolean_literal_typo_line(
    line_getter: LineGetter,
    lineno: int,
    lookback: int = 3,
):
    # Prefer current error line first, then scan nearby non-empty lines.
    if not lineno:
        return None, None, None
    candidates = []
    try:
        candidates.append((lineno, line_getter(lineno)))
    except Exception:
        pass
    line = max(int(lineno) - 1, 1)
    scanned = 0
    while line >= 1 and scanned < int(max(0, lookback)):
        try:
            txt = line_getter(line)
        except Exception:
            break
        if str(txt or "").strip():
            candidates.append((line, txt))
            scanned += 1
        line -= 1
    for ln, txt in candidates:
        diag = boolean_literal_typo_diagnostic(txt)
        if diag:
            return ln, txt, diag
    return None, None, None
