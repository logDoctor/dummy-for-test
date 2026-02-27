from fastapi import FastAPI
import uvicorn
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace

# Azure Monitor에 데이터를 보내기 위한 연결 문자열 설정
# 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING을 사용하거나 아래에 직접 입력하세요.
connection_string = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
    "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/",
)

# Application Insights 설정
# Cloud Role Name을 'python-api'로 통일하여 식별성 강화
os.environ["OTEL_SERVICE_NAME"] = "python-api"

# Azure Monitor OpenTelemetry 구성 (초기 설정, connection_string 없이)
configure_azure_monitor()


# 1. Logging Filter: 육하원칙(5W1H) 및 표준 필드 주입
class GlobalDimensionsFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        # 표준 필드 채우기 (user_Id, application_Version 등)
        # Python SDK(OpenTelemetry)에서 record 필드에 직접 넣으면 AI 필드로 매핑됩니다.
        record.user_Id = "test-user-python"
        record.application_Version = "1.0.0"

        # 5W1H 및 공통 속성
        record.custom_dimensions.update(
            {
                "Environment": "Lab",
                "AppVersion": "1.0.0",
                "Where": os.getenv("OTEL_SERVICE_NAME", "python-api"),
            }
        )
        return True


# 수동 로깅을 위한 Logger 설정 및 필터 적용
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addFilter(GlobalDimensionsFilter())

# Azure Monitor OpenTelemetry 구성 (connection_string과 함께 최종 설정)
# 이 한 줄로 HTTP 요청, 종속성, 예외 등이 자동으로 추적됩니다.
configure_azure_monitor(
    connection_string=connection_string,
)

app = FastAPI()


# 2. Middleware: 육하원칙 및 표준 필드(Who/Where/How/User) 자동 주입
@app.middleware("http")
async def add_custom_telemetry(request, call_next):
    span = trace.get_current_span()
    if span:
        # 표준 필드 매핑
        span.set_attribute("enduser.id", "test-user-python")  # user_Id 필드로 매핑됨
        span.set_attribute(
            "service.version", "1.0.0"
        )  # application_Version 필드로 매핑됨

        # 5W1H 속성
        span.set_attribute("Who", request.client.host)
        span.set_attribute("Where", f"python-api:{request.url.path}")
        span.set_attribute("How", request.method)
        span.set_attribute("Environment", "Lab")
        span.set_attribute("AppVersion", "1.0.0")
    response = await call_next(request)
    return response


tracer = trace.get_tracer(__name__)


@app.get("/")
async def root():
    with tracer.start_as_current_span("hello-world-span"):
        # 이제 별도의 extra 설정 없이도 필터에 의해 속성이 자동으로 붙습니다.
        logger.info("Hello World request received via Global Filter")
        return {"message": "Hello from Python with Automated Telemetry!"}


@app.get("/error")
async def trigger_error():
    raise Exception("This is a test exception for Application Insights")


@app.get("/logs")
async def generate_logs():
    logger.info("This is an INFO log from Python")
    logger.warning("This is a WARNING log from Python")
    logger.error("This is an ERROR log from Python")
    return {"message": "Diverse logs generated!"}


@app.get("/custom-event")
async def generate_event():
    with tracer.start_as_current_span("CustomEvent: UserCheckout"):
        logger.info("User checkout process started")
    return {"message": "Custom event span created!"}


@app.get("/dependency")
async def generate_dependency():
    import time

    with tracer.start_as_current_span("Simulated_SQL_Query") as span:
        span.set_attribute("db.system", "mssql")
        span.set_attribute("db.statement", "SELECT * FROM Users")
        time.sleep(0.05)
    return {"message": "Dependency simulated"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
