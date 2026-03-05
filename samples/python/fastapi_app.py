import asyncio
import logging
import os
import random
from datetime import datetime, timezone

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
    """AppTraces에 공통 필드를 자동 주입하는 로깅 필터"""

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


class DropUnknownRouteProcessor(SpanProcessor):
    def on_start(self, span: trace.Span, parent_context=None) -> None:
        pass

    def on_end(self, span: trace.Span) -> None:
        if span.attributes and span.attributes.get("http.response.status_code") == 404:
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)


def setup_telemetry(app: FastAPI):
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        logging.getLogger("app").warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING is not set. Telemetry will not be sent to Azure Monitor."
        )
        return trace.get_tracer(__name__)
    os.environ["OTEL_SERVICE_NAME"] = "python-api"
    configure_azure_monitor(connection_string=connection_string)
    provider = trace.get_tracer_provider()
    provider.add_span_processor(DropUnknownRouteProcessor())
    FastAPIInstrumentor.instrument_app(app)
    return trace.get_tracer(__name__)


def setup_logger(name="app"):
    app_logger = logging.getLogger(name)
    app_logger.setLevel(logging.INFO)
    app_logger.addFilter(GlobalDimensionsFilter())
    return app_logger


logger = setup_logger()
app = FastAPI(title="Log Doctor Python Sample API (Single File)")
tracer = setup_telemetry(app)
router = APIRouter(prefix="/api", tags=["examples"])


# ==========================================
# Middleware: Context Injection (통합 표준)
# ==========================================
@app.middleware("http")
async def add_custom_telemetry_middleware(request: Request, call_next):
    span = trace.get_current_span()
    if span.is_recording():
        service_name = os.environ.get("OTEL_SERVICE_NAME", "python-api")
        user_id = request.headers.get("x-user-id", "test-user-python")
        six_w_one_h = {
            "6W1H.Who": user_id,
            "6W1H.When": datetime.now(timezone.utc).isoformat(),
            "6W1H.Where": f"{service_name}:{request.url.path}",
            "6W1H.What": f"{request.method} {request.url.path}",
            "6W1H.Why": "API request handling",
            "6W1H.How": "FastAPI middleware + OpenTelemetry auto instrumentation",
        }

        span.set_attribute("enduser.id", user_id)
        span.set_attribute("service.version", "1.0.0")
        span.set_attribute("Environment", "Lab")
        span.set_attribute("AppVersion", "1.0.0")
        for key, value in six_w_one_h.items():
            span.set_attribute(key, value)
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
            "GET /api/normalized-log?scenario=good (정규화 표준 준수 예시)",
            "GET /api/normalized-log?scenario=bad  (정규화 위반 예시)",
        ],
        "examples": {
            "health": "GET /api/health",
            "logs": "GET /api/logs",
            "custom_event": "GET /api/custom-event",
            "dependency": "GET /api/dependency",
            "secret_data": "GET /api/secret-data",
            "error_test": "GET /api/error",
            "normalized_log_good": "GET /api/normalized-log?scenario=good",
            "normalized_log_bad": "GET /api/normalized-log?scenario=bad",
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
        await asyncio.sleep(0.05)
    return {"message": "Dependency simulated"}


@router.get("/secret-data", summary="보안 감사(Audit) 로그 예시")
async def view_secret_data():
    user_id = f"user-{random.randint(1000, 9999)}"
    document_id = random.randint(1, 100)

    with tracer.start_as_current_span("Audit_Action: SecretDocumentRead") as span:
        span.set_attribute("Security.Actor", user_id)
        span.set_attribute("Security.Action", "File_Download")
        span.set_attribute("Security.Target", f"confidential_{document_id}.pdf")
        await asyncio.sleep(random.uniform(0.1, 0.5))
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


# ==========================================
# /api/normalized-log — AppTraces 정규화 표준 시연
# ==========================================
@router.get("/normalized-log", summary="AppTraces 정규화 표준 시연 (Log Doctor 기준)")
async def normalized_log_demo(scenario: str = "good"):
    """
    Log Doctor가 정의한 AppTraces 정규화 표준을 보여주는 템플릿 API.

    scenario=good → 표준을 준수한 로그 (Log Doctor: criticality=medium/high, 정상 판정)
    scenario=bad  → 표준 위반 로그    (Log Doctor: normalization_issue 처방 생성)

    [정규화 표준 체크리스트]
    ✅ 구조화된 메시지 (key=value 또는 명확한 문장)
    ✅ CustomDimensions에 5W1H 포함 (Who, What, Why 필수 / Where, How는 미들웨어 자동)
    ✅ SeverityLevel 명시 (logger.info / warning / error)
    ✅ 민감정보 마스킹 (이메일, 비밀번호 등)
    ✅ trace_id 연결 (OperationId — OpenTelemetry 자동 처리)
    """
    if scenario == "good":
        return _log_good_examples()
    elif scenario == "bad":
        return _log_bad_examples()
    else:
        return {"error": "scenario는 'good' 또는 'bad'만 허용됩니다."}


def _log_good_examples() -> dict:
    """✅ 정규화 표준을 준수한 로그 예시"""

    # --- 예시 1: INFO — 주문 처리 성공 ---
    logger.info(
        "주문 처리 완료: order_id=order-789, payment=success",
        extra={
            "custom_dimensions": {
                # 비즈니스 컨텍스트
                "user_id": "user-456",
                "order_id": "order-789",
                "payment_method": "card",
                "amount": 29000,
                "result": "SUCCESS",
                "duration_ms": 320,
            }
        },
    )

    # --- 예시 2: WARNING — 느린 응답 감지 ---
    logger.warning(
        "외부 결제 API 응답 지연: target=payment-api.com, duration_ms=4800",
        extra={
            "custom_dimensions": {
                "user_id": "user-456",
                "target": "payment-api.com",
                "duration_ms": 4800,
                "threshold_ms": 3000,
                "result": "SLOW",
            }
        },
    )

    # --- 예시 3: ERROR — 에러, 민감정보 마스킹 적용 ---
    logger.error(
        "사용자 인증 실패: user=jo***@company.com, reason=invalid_password",
        extra={
            "custom_dimensions": {
                "user_id": "jo***@company.com",  # ✅ 마스킹 처리
                "error_code": "AUTH_INVALID_PASSWORD",
                "attempt_count": 3,
                "result": "FAILED",
                # ❌ 절대 넣으면 안 되는 것: "password": "abc123"  → 마스킹 필수
            }
        },
    )

    return {
        "scenario": "good",
        "description": "Log Doctor 정규화 표준을 준수한 로그 3건이 AppTraces에 기록되었습니다.",
        "log_doctor_expected": {
            "log_1": {
                "severity": "INFO",
                "criticality": "medium",
                "masking": "✅",
            },
            "log_2": {
                "severity": "WARNING",
                "criticality": "medium",
                "masking": "✅",
            },
            "log_3": {
                "severity": "ERROR",
                "criticality": "high",
                "masking": "✅",
            },
        },
        "check_in_law": (
            "AppTraces "
            "| where TimeGenerated > ago(5m) "
            "| where OperationName contains 'normalized-log' "
            "| project TimeGenerated, Message, SeverityLevel, CustomDimensions"
        ),
    }


def _log_bad_examples() -> dict:
    """❌ 정규화 표준 위반 로그 예시 — Log Doctor가 처방을 생성하는 패턴"""

    # --- 위반 1: 구조화 없음 + SeverityLevel 불명확 ---
    # (logger.info를 쓰긴 했지만 메시지에 아무 컨텍스트 없음)
    logger.info("Processing...")

    # --- 위반 2: 민감정보 노출 ---
    logger.error(
        "Login failed for john@company.com password=abc123",  # ❌ 평문 비밀번호
        extra={
            "custom_dimensions": {
                # ❌ 5W1H 없음
                # ❌ Who 없음
                # ❌ What 없음
                "raw_info": "john@company.com:abc123",  # ❌ 민감정보 노출
            }
        },
    )

    # --- 위반 3: Debug 로그를 프로덕션에 방치 ---
    logger.debug(
        "DB query params: SELECT * FROM users WHERE id=%s, params=('user-456',)"
        # ❌ DEBUG 로그가 프로덕션에 있으면 Log Doctor가 'prevent' 처방 생성
    )

    # --- 위반 4: 반복 노이즈 로그 ---
    for _ in range(5):
        logger.info("Health check OK")  # ❌ 의미 없는 반복 로그

    return {
        "scenario": "bad",
        "description": "정규화 표준 위반 로그 4종이 AppTraces에 기록되었습니다.",
        "log_doctor_expected": {
            "violation_1": {
                "issue": "구조화 없음",
                "prescription": "메시지에 컨텍스트 추가",
                "severity": "medium",
            },
            "violation_2": {
                "issue": "민감정보(이메일, 비밀번호) 평문 노출",
                "prescription": "jo***@company.com 형태로 마스킹, password 필드 제거",
                "severity": "high",
            },
            "violation_3": {
                "issue": "DEBUG 로그가 프로덕션에 존재",
                "prescription": "로그 레벨을 INFO 이상으로 설정 (logging.setLevel(INFO))",
                "severity": "medium",
            },
            "violation_4": {
                "issue": "동일 메시지 반복 (노이즈)",
                "prescription": "Health check 로그는 주기적 집계 또는 필터링 권장",
                "severity": "low",
            },
        },
        "check_in_law": (
            "AppTraces "
            "| where TimeGenerated > ago(5m) "
            "| where OperationName contains 'normalized-log' "
            "| project TimeGenerated, Message, SeverityLevel, CustomDimensions"
        ),
    }


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
