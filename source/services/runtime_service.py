"""Runtime domain module."""

from core.domain_impl.infra import runtime_log_service
from core.domain_impl.infra import runtime_paths_service
from core.domain_impl.infra import token_env_service
from core.domain_impl.infra import windows_runtime_service


class RuntimeService:
    runtime_log_service = runtime_log_service
    runtime_paths_service = runtime_paths_service
    token_env_service = token_env_service
    windows_runtime_service = windows_runtime_service


RUNTIME = RuntimeService()
