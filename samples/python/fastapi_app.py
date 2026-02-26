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

# Azure Monitor OpenTelemetry 구성
# 이 한 줄로 HTTP 요청, 종속성, 예외 등이 자동으로 추적됩니다.
configure_azure_monitor(
    connection_string=connection_string,
)

app = FastAPI()
tracer = trace.get_tracer(__name__)


@app.get("/")
async def root():
    with tracer.start_as_current_span("hello-world-span"):
        return {"message": "Hello World from FastAPI with App Insights!"}


@app.get("/error")
async def trigger_error():
    raise Exception("This is a test exception for Application Insights")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
