"""
Service registry and virtual service names for the demo.
"""

import random
from typing import Dict, List

# Actual service registry with their configurations
SERVICE_REGISTRY: Dict[str, dict] = {
    "api-gateway": {
        "port": 5000,
        "description": "API Gateway - Routes requests and handles auth validation",
        "downstream": ["auth-service", "user-service", "order-service", "search-service"],
    },
    "auth-service": {
        "port": 5001,
        "description": "Authentication Service - Login, token validation, sessions",
        "downstream": ["analytics-service"],
    },
    "user-service": {
        "port": 5002,
        "description": "User Service - User profiles, preferences, settings",
        "downstream": ["analytics-service", "notification-service"],
    },
    "order-service": {
        "port": 5003,
        "description": "Order Service - Order processing, checkout flow",
        "downstream": ["payment-service", "inventory-service", "notification-service"],
    },
    "payment-service": {
        "port": 5004,
        "description": "Payment Service - Payment processing and validation",
        "downstream": ["notification-service"],
    },
    "inventory-service": {
        "port": 5005,
        "description": "Inventory Service - Stock management, reservations",
        "downstream": ["notification-service"],
    },
    "notification-service": {
        "port": 5006,
        "description": "Notification Service - Email, push, SMS notifications",
        "downstream": [],
    },
    "analytics-service": {
        "port": 5007,
        "description": "Analytics Service - Event tracking and metrics",
        "downstream": [],
    },
    "search-service": {
        "port": 5008,
        "description": "Search Service - Product and user search",
        "downstream": ["inventory-service"],
    },
}

# Virtual service names for display/simulation purposes
# These make it look like we have even more services
VIRTUAL_SERVICE_NAMES: List[str] = [
    "edge-proxy",
    "rate-limiter",
    "cache-layer",
    "auth-validator",
    "session-manager",
    "config-service",
    "feature-evaluator",
    "metric-collector",
    "log-aggregator",
    "trace-exporter",
    "event-bus",
    "message-queue",
    "job-scheduler",
    "webhook-handler",
    "cdn-origin",
    "load-balancer",
    "circuit-breaker",
    "retry-handler",
]


def get_random_virtual_service() -> str:
    """Get a random virtual service name."""
    return random.choice(VIRTUAL_SERVICE_NAMES)


def get_service_url(service_name: str, use_docker: bool = True) -> str:
    """
    Get the URL for a service.
    
    Args:
        service_name: Name of the service
        use_docker: If True, use Docker service names; otherwise use localhost
    
    Returns:
        Service URL
    """
    if service_name not in SERVICE_REGISTRY:
        raise ValueError(f"Unknown service: {service_name}")
    
    port = SERVICE_REGISTRY[service_name]["port"]
    
    if use_docker:
        return f"http://{service_name}:{port}"
    else:
        return f"http://localhost:{port}"


def get_downstream_services(service_name: str) -> List[str]:
    """Get the list of downstream services for a given service."""
    if service_name not in SERVICE_REGISTRY:
        return []
    return SERVICE_REGISTRY[service_name]["downstream"]


def get_all_service_names() -> List[str]:
    """Get all actual service names."""
    return list(SERVICE_REGISTRY.keys())
