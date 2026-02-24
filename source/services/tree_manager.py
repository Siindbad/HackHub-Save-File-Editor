"""Tree domain module."""

from core.domain_impl.ui import tree_engine_service
from core.domain_impl.ui import tree_mode_service
from core.domain_impl.ui import tree_policy_service
from core.domain_impl.ui import tree_view_service


class TreeManager:
    tree_engine_service = tree_engine_service
    tree_mode_service = tree_mode_service
    tree_policy_service = tree_policy_service
    tree_view_service = tree_view_service


TREE = TreeManager()
