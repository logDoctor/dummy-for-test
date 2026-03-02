import logging
import os
import random
import time

import uvicorn
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import SpanProcessor

"""
Single-file FastAPI sample (easy mode)

Run:
1) pip install -r requirements.txt
2) uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000

Quick start:
- Open docs: http://localhost:8000/docs
- Guide endpoint: GET http://localhost:8000/api/
"""


class GlobalDimensionsFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        record.user_Id = "test-user-python"
        record.application_Version = "1.0.0"
        record.custom_dimensions.update(
            {
                "Environment": "Lab",
                "AppVersion": "1.0.0",
                "Where": os.environ.get("OTEL_SERVICE_NAME", "python-api"),
            }
        )
        return True


def setup_logger(name="app"):
    app_logger = logging.getLogger(name)
    app_logger.setLevel(logging.INFO)
    app_logger.addFilter(GlobalDimensionsFilter())
    return app_logger


class DropUnknownRouteProcessor(SpanProcessor):
    def on_end(self, span: trace.Span) -> None:
        if span.attributes and span.attributes.get("http.response.status_code") == 404:
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)


def setup_telemetry(app: FastAPI):
    connection_string = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/",
    )
    os.environ["OTEL_SERVICE_NAME"] = "python-api"
    configure_azure_monitor(connection_string=connection_string)
    provider = trace.get_tracer_provider()
    provider.add_span_processor(DropUnknownRouteProcessor())
    FastAPIInstrumentor.instrument_app(app)
    return trace.get_tracer(__name__)


logger = setup_logger()
app = FastAPI(title="Log Doctor Python Sample API (Single File)")
tracer = setup_telemetry(app)
router = APIRouter(prefix="/api", tags=["examples"])


@app.middleware("http")
async def add_custom_telemetry_middleware(request: Request, call_next):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("enduser.id", "test-user-python")
        span.set_attribute("service.version", "1.0.0")
        span.set_attribute("Who", request.client.host if request.client else "unknown")
        span.set_attribute("Where", f"python-api:{request.url.path}")
        span.set_attribute("How", request.method)
        span.set_attribute("Environment", "Lab")
        span.set_attribute("AppVersion", "1.0.0")
    return await call_next(request)


@router.get("/", summary="시작 가이드 + 기능별 호출 예시")
async def start_here():
    return {
        "message": "아래 순서대로 호출하면 기능을 바로 확인할 수 있습니다.",
        "how_to_run": {
            "install": "pip install -r requirements.txt",
            "start": "uvicorn fastapi_app:app --reload --host 0.0.0.0 --port 8000",
            "docs": "http://localhost:8000/docs",
        },
        "recommended_order": [
            "GET /api/health",
            "GET /api/logs",
            "GET /api/custom-event",
            "GET /api/dependency",
            "GET /api/secret-data",
            "GET /api/error",
        ],
        "examples": {
            "health": "GET /api/health",
            "logs": "GET /api/logs",
            "custom_event": "GET /api/custom-event",
            "dependency": "GET /api/dependency",
            "secret_data": "GET /api/secret-data",
            "error_test": "GET /api/error",
        },
        "note": "요청하신 대로 down 라우트는 없습니다.",
    }


@router.get("/health", summary="기본 정상 응답")
async def health():
    logger.info("Health check request received")
    return {"status": "ok"}


@router.get("/logs", summary="INFO/WARNING/ERROR 로그 예시")
async def generate_logs():
    logger.info("This is an INFO log from Python")
    logger.warning("This is a WARNING log from Python")
    logger.error("This is an ERROR log from Python")
    return {"message": "Diverse logs generated"}


@router.get("/custom-event", summary="커스텀 비즈니스 이벤트 Span 예시")
async def generate_event():
    with tracer.start_as_current_span("CustomEvent: UserCheckout"):
        logger.info("User checkout process started. Custom business event logged.")
    return {"message": "Custom event span created"}


@router.get("/dependency", summary="외부 의존성(DB/API) 추적 예시")
async def generate_dependency():
    with tracer.start_as_current_span("Simulated_SQL_Query") as span:
        span.set_attribute("db.system", "mssql")
        span.set_attribute("db.statement", "SELECT * FROM Users")
        time.sleep(0.05)
    return {"message": "Dependency simulated"}


@router.get("/secret-data", summary="보안 감사(Audit) 로그 예시")
async def view_secret_data():
    user_id = f"user-{random.randint(1000, 9999)}"
    document_id = random.randint(1, 100)

    with tracer.start_as_current_span("Audit_Action: SecretDocumentRead") as span:
        span.set_attribute("Security.Actor", user_id)
        span.set_attribute("Security.Action", "File_Download")
        span.set_attribute("Security.Target", f"confidential_{document_id}.pdf")
        time.sleep(random.uniform(0.1, 0.5))
        logger.info(
            f"Audit success: user({user_id}) viewed document({document_id})",
            extra={
                "custom_dimensions": {
                    "Audit_Action": "VIEW_DOCUMENT",
                    "Target_Document_ID": document_id,
                    "Actor_User_ID": user_id,
                    "Is_Success": True,
                    "Severity": "Critical",
                }
            },
        )
        span.set_attribute("Security.Result", "Success")

    return {
        "message": "Secret document view logged successfully",
        "user_id": user_id,
        "document_id": document_id,
    }


@router.get("/error", summary="예외 추적 테스트")
async def trigger_error():
    raise Exception("This is a test exception for Application Insights")


app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "An intentional error occurred and was logged to Azure Monitor."
        },
    )


if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000)
