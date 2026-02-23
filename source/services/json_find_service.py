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
