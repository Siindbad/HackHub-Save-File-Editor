"""JSON path get/set helpers."""
from typing import Any


def get_value(root_value: Any, path: Any) -> Any:
    """Resolve nested value from root by path keys/indexes."""
    value = root_value
    for key in path:
        value = value[key]
    return value


def set_value(root_value: Any, path: Any, new_value: Any) -> Any:
    """Set nested value by path and return updated root value."""
    if not path:
        return new_value
    parent = root_value
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = new_value
    return root_value
