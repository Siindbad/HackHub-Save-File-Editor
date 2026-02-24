"""JSON view and find domain module."""

from core.domain_impl.json import json_find_nav_service
from core.domain_impl.json import json_find_service
from core.domain_impl.json import json_text_find_service
from core.domain_impl.json import json_view_render_service
from core.domain_impl.json import json_view_service


class JsonViewManager:
    json_find_nav_service = json_find_nav_service
    json_find_service = json_find_service
    json_text_find_service = json_text_find_service
    json_view_render_service = json_view_render_service
    json_view_service = json_view_service


JSON_VIEW = JsonViewManager()
