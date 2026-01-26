"""
Shared utilities for LaunchDarkly Observability Demo services.
"""

from .users import USER_PERSONAS, get_random_user, get_user_context
from .error_injection import should_inject_error, get_error_for_service, ERROR_SCENARIOS
from .observability import create_ld_client, create_observability_config
from .service_names import SERVICE_REGISTRY, VIRTUAL_SERVICE_NAMES, get_random_virtual_service

__all__ = [
    'USER_PERSONAS',
    'get_random_user',
    'get_user_context',
    'should_inject_error',
    'get_error_for_service',
    'ERROR_SCENARIOS',
    'create_ld_client',
    'create_observability_config',
    'SERVICE_REGISTRY',
    'VIRTUAL_SERVICE_NAMES',
    'get_random_virtual_service',
]
