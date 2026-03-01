import os
import time
import logging
import random
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import SpanProcessor

# ==========================================
# 1. Configuration & OpenTelemetry Setup
# ==========================================
connection_string = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
    "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/",
)

# Set base Cloud Role Name for Application Insights
os.environ["OTEL_SERVICE_NAME"] = "python-api"


# 1. 쓸데없는 짐(Span)을 폐기하는 커스텀 필터 만들기
class DropUnknownRouteProcessor(SpanProcessor):
    def on_end(self, span: trace.Span) -> None:
        # 응답 상태 코드가 404(Not Found)인 경우
        if span.attributes and span.attributes.get("http.response.status_code") == 404:
            # Azure로 택배를 보내지 않고 그 자리에서 Span을 파기(비활성화)합니다.
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)


# Initialize Azure Monitor OpenTelemetry
configure_azure_monitor(connection_string=connection_string)

# 필터를 Azure 배송 라인에 찰칵! 하고 끼워넣기
provider = trace.get_tracer_provider()
provider.add_span_processor(DropUnknownRouteProcessor())

# Acquire tracer for custom manual spanning
tracer = trace.get_tracer(__name__)


# ==========================================
# 2. Logging Setup with 5W1H standard fields
# ==========================================
class GlobalDimensionsFilter(logging.Filter):
    """
    Injects 5W1H (Who, Where, How, etc.) and standard Application Insights fields
    into every standard Python log emitted by this application.
    """

    def filter(self, record):
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        # Standard Application Insights mapped fields
        record.user_Id = "test-user-python"
        record.application_Version = "1.0.0"

        # Custom dimensions (5W1H Context)
        record.custom_dimensions.update(
            {
                "Environment": "Lab",
                "AppVersion": "1.0.0",
                "Where": os.environ.get("OTEL_SERVICE_NAME", "python-api"),
            }
        )
        return True


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(GlobalDimensionsFilter())

# ==========================================
# 3. FastAPI Application & Middleware
# ==========================================
app = FastAPI(title="Log Doctor Python Sample API")

# Enable automatic instrumentation for FastAPI to generate AppRequests
FastAPIInstrumentor.instrument_app(app)


@app.middleware("http")
async def add_custom_telemetry(request: Request, call_next):
    """
    Middleware that intercepts all incoming HTTP requests and automatically
    adds 5W1H context to the current OpenTelemetry Request Span.
    """
    # OpenTelemetry automatically starts a span for incoming HTTP requests.
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


# ==========================================
# 4. Business Logic (Routes)
# ==========================================


@app.get("/")
async def root():
    # Logs inside routes will carry the context automatically
    logger.info("Hello World request received via Global Filter")
    return {"message": "Hello from Python with Automated Telemetry!"}


@app.get("/error")
async def trigger_error():
    # Exceptions are automatically captured by the SDK
    raise Exception("This is a test exception for Application Insights")


@app.get("/logs")
async def generate_logs():
    logger.info("This is an INFO log from Python")
    logger.warning("This is a WARNING log from Python")
    logger.error("This is an ERROR log from Python")
    return {"message": "Diverse logs generated!"}


@app.get("/custom-event")
async def generate_event():
    # Example of generating a custom span/event
    with tracer.start_as_current_span("CustomEvent: UserCheckout"):
        logger.info("User checkout process started. Custom business event logged.")
    return {"message": "Custom event span created!"}


@app.get("/dependency")
async def generate_dependency():
    # Manual tracking of an external dependency (e.g., DB or external API)
    with tracer.start_as_current_span("Simulated_SQL_Query") as span:
        span.set_attribute("db.system", "mssql")
        span.set_attribute("db.statement", "SELECT * FROM Users")
        time.sleep(0.05)

    return {"message": "Dependency simulated"}


@app.get("/secret-data")
async def view_secret_data():
    """
    [핵심 예제] "누가 언제 어디서 어떻게 중요 데이터를 조회했는가"
    비즈니스 감사(Audit) 이벤트를 Custom Properties 에 기록하는 엔드포인트입니다.
    """
    # 1. 랜덤 유저 ID 및 랜덤 문서 ID 생성
    user_id = f"user-{random.randint(1000, 9999)}"
    document_id = random.randint(1, 100)

    # 2. 커스텀 블록(Span)으로 작업 전체를 묶어서 상세 속성(Custom Properties) 기록
    with tracer.start_as_current_span("Audit_Action: 1급 기밀 문서 조회") as span:
        # 블록에 영원히 지워지지 않는 낙인(스티커) 쾅쾅 찍기
        span.set_attribute("Security.Actor", user_id)
        span.set_attribute("Security.Action", "File_Download")
        span.set_attribute(
            "Security.Target", f"Chairman_Salary_Report_{document_id}.pdf"
        )

        # 파일 다운로드 로직 시뮬레이션 (0.1 ~ 0.5초 대기)
        time.sleep(random.uniform(0.1, 0.5))

        # 3. 중요 이벤트 텍스트 로그(AppTraces)에도 명시적으로 딕셔너리 기록
        logger.info(
            f"보안 감사: 사용자({user_id})가 기밀 문서({document_id}) 조회에 성공했습니다.",
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

        # 작업 성공 결과 기록
        span.set_attribute("Security.Result", "Success")

    return {
        "message": "비밀 문서 조회 성공! (LAW 창고에 이 로깅이 완벽하게 전송되었습니다)",
        "user_id": user_id,
        "document_id": document_id,
    }


# Optional: Custom Exception Handler to return clean JSON while still relying on OpenTelemetry's automatic exception tracing
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception caught: {exc}")
    # We still let the SDK capture the exception trace automatically because it hooks into the ASGI layer.
    return JSONResponse(
        status_code=500,
        content={
            "message": "An intentional error occurred and was logged to Azure Monitor."
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
