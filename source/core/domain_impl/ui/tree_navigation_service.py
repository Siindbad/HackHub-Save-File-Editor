"""Tree path/group resolution helpers for find-navigation and selection restore."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_EXPECTED_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError,
    AttributeError,
    KeyError,
    IndexError,
    TypeError,
    ValueError,
)


def find_search_value_summary(value: Any, max_tokens: int = 24, max_chars: int = 360) -> str:
    """Return a compact scalar-only summary to keep find-index entries bounded."""
    tokens: list[str] = []
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = str(value).strip()
        if text:
            tokens.append(text)
    elif isinstance(value, dict):
        for child in value.values():
            if len(tokens) >= int(max_tokens):
                break
            if isinstance(child, (str, int, float, bool)) or child is None:
                text = str(child).strip()
                if text:
                    tokens.append(text)
    elif isinstance(value, list):
        for child in value:
            if len(tokens) >= int(max_tokens):
                break
            if isinstance(child, (str, int, float, bool)) or child is None:
                text = str(child).strip()
                if text:
                    tokens.append(text)
    joined = " ".join(tokens)
    if len(joined) > int(max_chars):
        return joined[: int(max_chars)]
    return joined


def _has_loading_child(owner: Any, item_id: Any, *, expected_errors: tuple[type[BaseException], ...]) -> bool:
    tree = getattr(owner, "tree", None)
    if tree is None:
        return False
    try:
        children = tree.get_children(item_id)
    except expected_errors:
        return False
    if len(children) != 1:
        return False
    try:
        return tree.item(children[0], "text") == "(loading)"
    except expected_errors:
        return False


def _populate_children(owner: Any, item_id: Any, *, expected_errors: tuple[type[BaseException], ...]) -> None:
    populate = getattr(owner, "_populate_children", None)
    if callable(populate):
        try:
            populate(item_id)
        except expected_errors:
            return


def network_group_for_list_index(
    owner: Any,
    list_path: Any,
    row_index: Any,
    *,
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS,
) -> str | None:
    """Resolve grouped Network list row type for a concrete list index."""
    if not isinstance(list_path, list) or not isinstance(row_index, int):
        return None
    getter = getattr(owner, "_get_value", None)
    if not callable(getter):
        return None
    try:
        list_value = getter(list_path)
    except expected_errors:
        return None
    if not isinstance(list_value, list):
        return None
    if row_index < 0 or row_index >= len(list_value):
        return None
    is_network_list = getattr(owner, "_is_network_list", None)
    if callable(is_network_list) and not bool(is_network_list(list_path, list_value)):
        return None
    row = list_value[row_index]
    if isinstance(row, dict):
        group = str(row.get("type", "") or "").strip()
        return group or "UNKNOWN"
    return "UNKNOWN"


def ensure_tree_group_item_loaded(
    owner: Any,
    list_path: Any,
    group: Any,
    *,
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS,
) -> Any:
    """Ensure grouped Network bucket node exists and return its tree item id."""
    parent_id = ensure_tree_item_for_path(owner, list_path, expected_errors=expected_errors)
    if parent_id is None:
        return None
    if _has_loading_child(owner, parent_id, expected_errors=expected_errors):
        _populate_children(owner, parent_id, expected_errors=expected_errors)
    tree = getattr(owner, "tree", None)
    item_to_path = getattr(owner, "item_to_path", None)
    if tree is None or not isinstance(item_to_path, dict):
        return None

    def _find_group_item() -> Any:
        try:
            children = tree.get_children(parent_id)
        except expected_errors:
            return None
        for child in children:
            item_path = item_to_path.get(child)
            if (
                isinstance(item_path, tuple)
                and len(item_path) == 3
                and item_path[0] == "__group__"
                and item_path[1] == list_path
                and item_path[2] == group
            ):
                return child
        return None

    group_item = _find_group_item()
    if group_item is not None:
        return group_item
    _populate_children(owner, parent_id, expected_errors=expected_errors)
    return _find_group_item()


def resolve_grouped_list_item(
    owner: Any,
    current_item: Any,
    prefix: Any,
    *,
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS,
) -> Any:
    """Resolve grouped Network row path under ROUTER/DEVICE/FIREWALL bucket nodes."""
    if not current_item:
        return None
    if not isinstance(prefix, list) or len(prefix) < 2:
        return None
    list_path = prefix[:-1]
    row_index = prefix[-1]
    if not isinstance(row_index, int):
        return None
    group = network_group_for_list_index(owner, list_path, row_index, expected_errors=expected_errors)
    if not group:
        return None
    group_item = ensure_tree_group_item_loaded(owner, list_path, group, expected_errors=expected_errors)
    if group_item is None:
        return None
    if _has_loading_child(owner, group_item, expected_errors=expected_errors):
        _populate_children(owner, group_item, expected_errors=expected_errors)
    tree = getattr(owner, "tree", None)
    item_to_path = getattr(owner, "item_to_path", None)
    if tree is None or not isinstance(item_to_path, dict):
        return None
    try:
        children = tree.get_children(group_item)
    except expected_errors:
        return None
    for child in children:
        child_path = item_to_path.get(child)
        if isinstance(child_path, list) and child_path == prefix:
            return child
    return None


def ensure_tree_item_for_path(
    owner: Any,
    target_path: Any,
    *,
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS,
) -> Any:
    """Expand tree nodes as needed and resolve a concrete tree item id for path."""
    if not isinstance(target_path, list):
        return None
    current_item = ""
    if not target_path:
        return current_item
    tree = getattr(owner, "tree", None)
    item_to_path = getattr(owner, "item_to_path", None)
    if tree is None or not isinstance(item_to_path, dict):
        return None

    for depth, _key in enumerate(target_path):
        if current_item:
            if _has_loading_child(owner, current_item, expected_errors=expected_errors):
                _populate_children(owner, current_item, expected_errors=expected_errors)
        else:
            try:
                has_root_children = bool(tree.get_children(""))
            except expected_errors:
                has_root_children = True
            if not has_root_children:
                _populate_children(owner, "", expected_errors=expected_errors)

        prefix = target_path[: depth + 1]
        next_item = None
        try:
            children = tree.get_children(current_item)
        except expected_errors:
            children = []
        for child in children:
            child_path = item_to_path.get(child)
            if isinstance(child_path, list) and child_path == prefix:
                next_item = child
                break

        if next_item is None:
            _populate_children(owner, current_item, expected_errors=expected_errors)
            try:
                children = tree.get_children(current_item)
            except expected_errors:
                children = []
            for child in children:
                child_path = item_to_path.get(child)
                if isinstance(child_path, list) and child_path == prefix:
                    next_item = child
                    break

        if next_item is None:
            next_item = resolve_grouped_list_item(owner, current_item, prefix, expected_errors=expected_errors)
        if next_item is None:
            return None
        current_item = next_item
    return current_item


@dataclass(slots=True)
class TreeNavigationAdapter:
    """Owner-bound tree-navigation facade used by JsonEditor wrappers."""

    owner: Any
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS

    def resolve_path(self, path: Any) -> Any:
        return ensure_tree_item_for_path(self.owner, path, expected_errors=self.expected_errors)

    def get_group_for_index(self, list_path: Any, row_index: Any) -> str | None:
        return network_group_for_list_index(
            self.owner,
            list_path,
            row_index,
            expected_errors=self.expected_errors,
        )

    def resolve_grouped_list_item(self, current_item: Any, prefix: Any) -> Any:
        return resolve_grouped_list_item(
            self.owner,
            current_item,
            prefix,
            expected_errors=self.expected_errors,
        )

    def ensure_group_item_loaded(self, list_path: Any, group: Any) -> Any:
        return ensure_tree_group_item_loaded(
            self.owner,
            list_path,
            group,
            expected_errors=self.expected_errors,
        )

    @staticmethod
    def find_summary(value: Any, max_tokens: int = 24, max_chars: int = 360) -> str:
        return find_search_value_summary(value, max_tokens=max_tokens, max_chars=max_chars)


def bind(
    owner: Any,
    *,
    expected_errors: tuple[type[BaseException], ...] = DEFAULT_EXPECTED_ERRORS,
) -> TreeNavigationAdapter:
    """Create owner-bound tree-navigation adapter for UI orchestration wrappers."""
    return TreeNavigationAdapter(owner=owner, expected_errors=expected_errors)
