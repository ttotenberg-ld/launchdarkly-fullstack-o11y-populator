"""
Error injection logic for realistic observability demos.
Allows configurable error rates for different services and endpoints.
"""

import random
from typing import Optional, Tuple

# Error scenarios with injection rates per service
ERROR_SCENARIOS = {
    "api-gateway": {
        "rate_limit_exceeded": {
            "rate": 0.02,
            "endpoints": ["/api/*"],
            "error_class": "RateLimitError",
            "message": "Rate limit exceeded. Please retry after 60 seconds.",
            "status_code": 429,
        },
        "service_unavailable": {
            "rate": 0.01,
            "endpoints": ["*"],
            "error_class": "ServiceUnavailableError",
            "message": "Downstream service temporarily unavailable",
            "status_code": 503,
        },
    },
    "auth-service": {
        "invalid_token": {
            "rate": 0.05,
            "endpoints": ["/validate", "/refresh"],
            "error_class": "AuthenticationError",
            "message": "Invalid or expired authentication token",
            "status_code": 401,
        },
        "account_locked": {
            "rate": 0.02,
            "endpoints": ["/login"],
            "error_class": "AccountLockedException",
            "message": "Account locked due to too many failed attempts",
            "status_code": 403,
        },
    },
    "user-service": {
        "user_not_found": {
            "rate": 0.03,
            "endpoints": ["/users/*", "/profile"],
            "error_class": "UserNotFoundError",
            "message": "User not found in database",
            "status_code": 404,
        },
        "database_timeout": {
            "rate": 0.01,
            "endpoints": ["*"],
            "error_class": "DatabaseTimeoutError",
            "message": "Database query timed out after 30 seconds",
            "status_code": 504,
        },
    },
    "order-service": {
        "order_validation_failed": {
            "rate": 0.04,
            "endpoints": ["/orders", "/checkout"],
            "error_class": "OrderValidationError",
            "message": "Order validation failed: invalid items in cart",
            "status_code": 400,
        },
        "inventory_sync_error": {
            "rate": 0.02,
            "endpoints": ["/checkout"],
            "error_class": "InventorySyncError",
            "message": "Failed to sync with inventory service",
            "status_code": 500,
        },
    },
    "payment-service": {
        "payment_declined": {
            "rate": 0.06,
            "endpoints": ["/process", "/charge"],
            "error_class": "PaymentDeclinedException",
            "message": "Payment declined by card issuer",
            "status_code": 402,
        },
        "fraud_detected": {
            "rate": 0.02,
            "endpoints": ["/process"],
            "error_class": "FraudDetectionError",
            "message": "Transaction flagged by fraud detection system",
            "status_code": 403,
        },
        "gateway_timeout": {
            "rate": 0.03,
            "endpoints": ["*"],
            "error_class": "PaymentGatewayTimeoutError",
            "message": "Payment gateway did not respond in time",
            "status_code": 504,
        },
    },
    "inventory-service": {
        "out_of_stock": {
            "rate": 0.08,
            "endpoints": ["/reserve", "/check"],
            "error_class": "OutOfStockError",
            "message": "Requested item is out of stock",
            "status_code": 409,
        },
        "warehouse_unreachable": {
            "rate": 0.02,
            "endpoints": ["*"],
            "error_class": "WarehouseConnectionError",
            "message": "Unable to connect to warehouse management system",
            "status_code": 503,
        },
    },
    "notification-service": {
        "email_delivery_failed": {
            "rate": 0.04,
            "endpoints": ["/send", "/email"],
            "error_class": "EmailDeliveryError",
            "message": "Failed to deliver email: SMTP connection refused",
            "status_code": 502,
        },
        "template_not_found": {
            "rate": 0.01,
            "endpoints": ["/send"],
            "error_class": "TemplateNotFoundError",
            "message": "Email template not found",
            "status_code": 404,
        },
    },
    "analytics-service": {
        "event_processing_failed": {
            "rate": 0.02,
            "endpoints": ["/track", "/events"],
            "error_class": "EventProcessingError",
            "message": "Failed to process analytics event",
            "status_code": 500,
        },
        "queue_full": {
            "rate": 0.01,
            "endpoints": ["*"],
            "error_class": "QueueFullError",
            "message": "Event queue is full, events may be dropped",
            "status_code": 503,
        },
    },
    "search-service": {
        "search_timeout": {
            "rate": 0.03,
            "endpoints": ["/search", "/query"],
            "error_class": "SearchTimeoutError",
            "message": "Search query timed out",
            "status_code": 504,
        },
        "index_not_ready": {
            "rate": 0.01,
            "endpoints": ["*"],
            "error_class": "IndexNotReadyError",
            "message": "Search index is currently being rebuilt",
            "status_code": 503,
        },
    },
}


class InjectedError(Exception):
    """Base class for injected errors."""
    
    def __init__(self, message: str, error_type: str, status_code: int = 500):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


def should_inject_error(service_name: str, endpoint: str = "*") -> bool:
    """
    Determine if an error should be injected based on configured rates.
    Returns True if an error should be injected.
    """
    if service_name not in ERROR_SCENARIOS:
        return False
    
    scenarios = ERROR_SCENARIOS[service_name]
    
    for scenario_name, scenario in scenarios.items():
        # Check if endpoint matches
        endpoints = scenario.get("endpoints", ["*"])
        endpoint_matches = "*" in endpoints or any(
            endpoint.startswith(ep.replace("*", "")) for ep in endpoints
        )
        
        if endpoint_matches:
            if random.random() < scenario["rate"]:
                return True
    
    return False


def get_error_for_service(
    service_name: str, 
    endpoint: str = "*"
) -> Optional[Tuple[str, str, int]]:
    """
    Get an error to inject for a service/endpoint combination.
    Returns (error_class, message, status_code) or None if no error should be injected.
    """
    if service_name not in ERROR_SCENARIOS:
        return None
    
    scenarios = ERROR_SCENARIOS[service_name]
    
    # Collect matching scenarios
    matching = []
    for scenario_name, scenario in scenarios.items():
        endpoints = scenario.get("endpoints", ["*"])
        endpoint_matches = "*" in endpoints or any(
            endpoint.startswith(ep.replace("*", "")) for ep in endpoints
        )
        
        if endpoint_matches:
            matching.append((scenario_name, scenario))
    
    if not matching:
        return None
    
    # Try each matching scenario based on its rate
    for scenario_name, scenario in matching:
        if random.random() < scenario["rate"]:
            return (
                scenario["error_class"],
                scenario["message"],
                scenario["status_code"],
            )
    
    return None


def maybe_raise_error(service_name: str, endpoint: str = "*") -> None:
    """
    Possibly raise an injected error based on configured rates.
    Use this at the start of endpoint handlers.
    """
    error_info = get_error_for_service(service_name, endpoint)
    
    if error_info:
        error_class, message, status_code = error_info
        raise InjectedError(message, error_class, status_code)
