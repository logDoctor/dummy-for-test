import time
import random
from fastapi import APIRouter
from logger import logger
from telemetry import tracer

router = APIRouter()


@router.get("/")
async def root():
    # Logs inside routes will carry the context automatically
    logger.info("Hello World request received via Global Filter")
    return {"message": "Hello from Python with Automated Telemetry!"}


@router.get("/error")
async def trigger_error():
    # Exceptions are automatically captured by the SDK
    raise Exception("This is a test exception for Application Insights")


@router.get("/logs")
async def generate_logs():
    logger.info("This is an INFO log from Python")
    logger.warning("This is a WARNING log from Python")
    logger.error("This is an ERROR log from Python")
    return {"message": "Diverse logs generated!"}


@router.get("/custom-event")
async def generate_event():
    # Example of generating a custom span/event
    with tracer.start_as_current_span("CustomEvent: UserCheckout"):
        logger.info("User checkout process started. Custom business event logged.")
    return {"message": "Custom event span created!"}


@router.get("/dependency")
async def generate_dependency():
    # Manual tracking of an external dependency (e.g., DB or external API)
    with tracer.start_as_current_span("Simulated_SQL_Query") as span:
        span.set_attribute("db.system", "mssql")
        span.set_attribute("db.statement", "SELECT * FROM Users")
        time.sleep(0.05)
    return {"message": "Dependency simulated"}


@router.get("/secret-data")
async def view_secret_data():
    """
    [핵심 예제] "누가 언제 어디서 어떻게 중요 데이터를 조회했는가"
    비즈니스 감사(Audit) 이벤트를 Custom Properties 에 기록하는 엔드포인트입니다.
    """
    user_id = f"user-{random.randint(1000, 9999)}"
    document_id = random.randint(1, 100)

    with tracer.start_as_current_span("Audit_Action: 1급 기밀 문서 조회") as span:
        span.set_attribute("Security.Actor", user_id)
        span.set_attribute("Security.Action", "File_Download")
        span.set_attribute(
            "Security.Target", f"Chairman_Salary_Report_{document_id}.pdf"
        )

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

        span.set_attribute("Security.Result", "Success")

    return {
        "message": "비밀 문서 조회 성공! (LAW 창고에 이 로깅이 완벽하게 전송되었습니다)",
        "user_id": user_id,
        "document_id": document_id,
    }
