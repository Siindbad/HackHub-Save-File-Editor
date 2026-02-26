"""JSON-mode find helpers for deterministic data-path matching."""
from typing import Any


def build_json_find_matches(owner: Any, query_lower: Any) -> Any:
    """Build deterministic JSON-mode path matches for Find Next traversal."""
    needle = str(query_lower or "").strip().casefold()
    if not needle:
        return []

    matches = []
    seen = set()
    hidden_keys = owner._hidden_root_tree_keys_for_mode("JSON")

    def _add(path):
        if not isinstance(path, list) or not path:
            return
        key = tuple(path)
        if key in seen:
            return
        seen.add(key)
        matches.append(path)

    def _walk(value, path):
        if isinstance(value, dict):
            keys = list(value.keys())
            if not path:
                keys = sorted(keys, key=lambda raw: str(owner._tree_display_label_for_key(raw)).casefold())
            for key in keys:
                if not path and owner._normalize_root_tree_key(key) in hidden_keys:
                    continue
                child_path = path + [key]
                key_text = f"{key} {owner._tree_display_label_for_key(key)}".casefold()
                if needle in key_text:
                    _add(child_path)
                _walk(value.get(key), child_path)
            return

        if isinstance(value, list):
            labeler = owner._list_labelers.get(tuple(path))
            for idx, item in enumerate(value):
                child_path = path + [idx]
                if labeler:
                    label = str(labeler(idx, item))
                elif owner._is_database_table_rows_path(path):
                    label = str(owner._database_table_row_label(idx, item))
                else:
                    label = f"[{idx}]"
                if needle in label.casefold():
                    _add(child_path)
                _walk(item, child_path)
            return

        value_text = str(value).casefold() if value is not None else "none"
        if needle in value_text:
            if len(path) > 1:
                _add(path[:-1])
            _add(path)

    _walk(owner.data, [])
    return matches


def filter_json_find_matches(owner: Any, prior_matches: Any, query_lower: Any) -> Any:
    """Narrow existing matches for extended queries without rebuilding full-tree scan."""
    needle = str(query_lower or "").strip().casefold()
    if not needle:
        return []
    if not isinstance(prior_matches, list) or not prior_matches:
        return []
    cache = getattr(owner, "_json_find_path_token_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(owner, "_json_find_path_token_cache", cache)

    matches = []
    seen = set()
    for path in prior_matches:
        # Group sentinels are kept only when query still matches group text metadata.
        if isinstance(path, tuple) and len(path) == 3 and path[0] == "__group__":
            group_text = f"{path[1]} {path[2]}".casefold()
            if needle in group_text and path not in seen:
                seen.add(path)
                matches.append(path)
            continue
        if not isinstance(path, list) or not path:
            continue
        key = tuple(path)
        token_text = cache.get(key)
        if token_text is None:
            token_text = _path_token_text(owner, path)
            cache[key] = token_text
        if needle in token_text and key not in seen:
            seen.add(key)
            matches.append(path)
    return matches


def _path_token_text(owner: Any, path: list[Any]) -> str:
    value = _resolve_path_value(getattr(owner, "data", None), path)
    if value is _PATH_MISSING:
        return ""

    tokens = []
    tail = path[-1]
    if isinstance(tail, str):
        display = str(getattr(owner, "_tree_display_label_for_key", lambda raw: raw)(tail))
        tokens.append(str(tail))
        tokens.append(display)
    elif isinstance(tail, int):
        parent_path = path[:-1]
        labeler = getattr(owner, "_list_labelers", {}).get(tuple(parent_path))
        if labeler:
            try:
                tokens.append(str(labeler(tail, value)))
            except (TypeError, ValueError):
                tokens.append(f"[{tail}]")
        elif bool(getattr(owner, "_is_database_table_rows_path", lambda _path: False)(parent_path)):
            tokens.append(str(getattr(owner, "_database_table_row_label", lambda i, _v: f"[{i}]")(tail, value)))
        else:
            tokens.append(f"[{tail}]")

    if isinstance(value, (dict, list)):
        summary_fn = getattr(owner, "_find_search_value_summary", None)
        if callable(summary_fn):
            tokens.append(str(summary_fn(value)))
    elif value is None:
        tokens.append("none")
    else:
        tokens.append(str(value))

    return " ".join(tok for tok in tokens if tok).casefold()


_PATH_MISSING = object()


def _resolve_path_value(root: Any, path: list[Any]) -> Any:
    cursor = root
    for part in path:
        if isinstance(cursor, dict) and isinstance(part, str):
            if part not in cursor:
                return _PATH_MISSING
            cursor = cursor.get(part)
            continue
        if isinstance(cursor, list) and isinstance(part, int):
            if part < 0 or part >= len(cursor):
                return _PATH_MISSING
            cursor = cursor[part]
            continue
        return _PATH_MISSING
    return cursor
