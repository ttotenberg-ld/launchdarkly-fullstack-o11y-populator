"""
Shared observability configuration for LaunchDarkly services.
Includes W3C Trace Context propagation for distributed tracing.

IMPORTANT: Call create_ld_client() FIRST, then setup_flask_instrumentation()
to ensure proper trace context propagation.
"""

import os
from typing import Optional

import ldclient
from ldclient.config import Config
from ldobserve import ObservabilityConfig, ObservabilityPlugin

# Configure OpenTelemetry propagation for distributed tracing
from opentelemetry import trace
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# NOTE: We do NOT set the global textmap here at module import time.
# The LaunchDarkly SDK's ObservabilityPlugin sets up its own tracer provider,
# which may reset or override propagation settings. We must set the propagator
# AFTER the LD client is initialized, which happens in setup_flask_instrumentation().


def create_observability_config(
    service_name: str,
    service_version: str = "1.0.0",
    environment: Optional[str] = None
) -> ObservabilityConfig:
    """
    Create an ObservabilityConfig for a service.
    
    Args:
        service_name: Name of the service (e.g., 'api-gateway', 'user-service')
        service_version: Version of the service
        environment: Environment name (defaults to ENVIRONMENT env var or 'development')
    
    Returns:
        Configured ObservabilityConfig instance
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    return ObservabilityConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment
    )


def create_ld_client(
    service_name: str,
    service_version: str = "1.0.0",
    sdk_key: Optional[str] = None,
    environment: Optional[str] = None
) -> ldclient.LDClient:
    """
    Create and configure a LaunchDarkly client with observability.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        sdk_key: LaunchDarkly SDK key (defaults to LD_SDK_KEY env var)
        environment: Environment name
    
    Returns:
        Configured LDClient instance
    """
    if sdk_key is None:
        sdk_key = os.getenv('LD_SDK_KEY', 'sdk-key-123abc')
    
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development')
    
    # Create observability config and plugin
    observability_config = create_observability_config(
        service_name=service_name,
        service_version=service_version,
        environment=environment
    )
    
    plugin = ObservabilityPlugin(observability_config)
    
    # Create LD config
    config = Config(
        sdk_key=sdk_key,
        plugins=[plugin]
    )
    
    # Initialize client
    ldclient.set_config(config)
    client = ldclient.get()
    
    print(f"✓ LaunchDarkly SDK initialized for {service_name}")
    print(f"  Version: {service_version}")
    print(f"  Environment: {environment}")
    
    return client


def setup_flask_instrumentation(app):
    """
    Set up Flask and requests instrumentation for distributed tracing.
    
    MUST be called AFTER create_ld_client() so the tracer provider is ready.
    
    This function also configures W3C Trace Context propagation, which MUST happen
    AFTER the LaunchDarkly SDK initializes its tracer provider.
    
    Args:
        app: Flask application instance
    """
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    
    # Set up W3C Trace Context propagation AFTER LD client is initialized
    # This ensures traceparent/tracestate headers are properly parsed from
    # incoming requests and injected into outgoing requests.
    # CRITICAL: This must happen AFTER create_ld_client() to ensure the
    # propagator is active when Flask processes requests.
    set_global_textmap(CompositePropagator([TraceContextTextMapPropagator()]))
    print("  ✓ W3C Trace Context propagation enabled")
    
    # Instrument Flask to capture incoming requests and extract trace context
    FlaskInstrumentor().instrument_app(app)
    
    # Instrument requests library to propagate trace context to downstream services
    RequestsInstrumentor().instrument()
    
    print("  ✓ Flask and requests instrumentation enabled")


def get_common_attributes(service_name: str, endpoint: str = None) -> dict:
    """
    Get common attributes for observability data.
    
    Args:
        service_name: Name of the service
        endpoint: Optional endpoint path
    
    Returns:
        Dictionary of common attributes
    """
    attrs = {
        'source': 'backend',
        'service': service_name,
    }
    
    if endpoint:
        attrs['endpoint'] = endpoint
    
    return attrs
