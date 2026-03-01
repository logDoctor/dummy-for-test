from fastapi import Request
from opentelemetry import trace


async def add_custom_telemetry_middleware(request: Request, call_next):
    """
    Middleware that intercepts all incoming HTTP requests and automatically
    adds 5W1H context to the current OpenTelemetry Request Span.
    """
    span = trace.get_current_span()

    if span.is_recording():
        # Map standard user and version fields
        span.set_attribute("enduser.id", "test-user-python")
        span.set_attribute("service.version", "1.0.0")

        # Inject 5W1H context into the trace span
        span.set_attribute("Who", request.client.host if request.client else "unknown")
        span.set_attribute("Where", f"python-api:{request.url.path}")
        span.set_attribute("How", request.method)
        span.set_attribute("Environment", "Lab")
        span.set_attribute("AppVersion", "1.0.0")

    response = await call_next(request)
    return response
