import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import SpanProcessor


class DropUnknownRouteProcessor(SpanProcessor):
    def on_end(self, span: trace.Span) -> None:
        # 응답 상태 코드가 404(Not Found)인 경우 Span을 파기(비활성화)합니다.
        if span.attributes and span.attributes.get("http.response.status_code") == 404:
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)


def setup_telemetry(app):
    connection_string = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/",
    )
    os.environ["OTEL_SERVICE_NAME"] = "python-api"

    # Initialize Azure Monitor OpenTelemetry
    configure_azure_monitor(connection_string=connection_string)

    # 필터를 Azure 배송 라인에 끼워넣기
    provider = trace.get_tracer_provider()
    provider.add_span_processor(DropUnknownRouteProcessor())

    # Enable automatic instrumentation for FastAPI
    FastAPIInstrumentor.instrument_app(app)

    return trace.get_tracer(__name__)


tracer = trace.get_tracer(__name__)
