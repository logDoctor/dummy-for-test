# 로그/트레이스/메트릭은 왜 필요한가

## 목적
운영 상황에서 로그(Log), 트레이스(Trace), 메트릭(Metric)을 각각 왜 써야 하는지 빠르게 판단하기 위한 정리입니다.

## 로그 (Log)
### 왜 있는가
- 사건의 상세 증거를 남기기 위해 사용합니다.
- 에러 원인, 입력값, 비즈니스 이벤트를 재구성할 수 있습니다.

### 주로 답하는 질문
- "정확히 어떤 에러가 났나?"
- "어떤 사용자/데이터에서 실패했나?"

### 대표 사용 사례
- 예외 원인 분석
- 보안 감사(누가 무엇을 조회/변경했는지)
- 배포 후 회귀 이슈 확인

## 트레이스 (Trace)
### 왜 있는가
- 요청 1건의 전체 흐름을 서비스 간으로 연결해서 보기 위해 사용합니다.
- 병목 구간과 실패 지점을 단계별로 찾을 수 있습니다.

### 주로 답하는 질문
- "어디서 느려졌나?"
- "어느 서비스 호출에서 끊겼나?"

### 대표 사용 사례
- API 지연 원인 분석
- 마이크로서비스 체인 장애 추적
- 외부 의존성(DB/API) 지연 확인

## 메트릭 (Metric)
### 왜 있는가
- 시스템 상태를 숫자 추세로 빠르게 감시하기 위해 사용합니다.
- 알람과 용량 계획에 가장 적합합니다.

### 주로 답하는 질문
- "지금 서비스가 건강한가?"
- "오류율/지연이 평소보다 증가했나?"

### 대표 사용 사례
- RPS, 오류율, p95/p99 지연 모니터링
- SLO/SLA 관제
- 트래픽 증가 대응(오토스케일 기준)

## 세 가지를 같이 쓰는 방법
1. 메트릭으로 이상 징후를 먼저 감지합니다.
2. 트레이스로 요청 경로와 병목 구간을 좁힙니다.
3. 로그로 정확한 원인과 데이터 문맥을 확인합니다.

## 예시 코드 (Python)
아래는 OpenTelemetry를 쓰는 FastAPI 기준으로, 각각을 어떻게 찍는지 최소 예시입니다.

### 로그 (Log) 예시
```python
import logging

logger = logging.getLogger("app")

logger.info("checkout started", extra={"custom_dimensions": {"user_id": "u-123"}})
logger.error(
    "payment failed",
    extra={"custom_dimensions": {"order_id": "o-100", "error_code": "PAYMENT_503"}},
)
```

### 트레이스 (Trace) 예시
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("CustomEvent: Checkout") as span:
    span.set_attribute("user_id", "u-123")
    span.set_attribute("order_id", "o-100")
    # 여기에서 외부 API 호출/DB 쿼리 등을 수행
```

### 메트릭 (Metric) 예시
```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

requests_total = meter.create_counter("demo_requests_total")
latency_ms = meter.create_histogram("demo_latency_ms")

requests_total.add(1, {"route": "/api/health", "method": "GET"})
latency_ms.record(123.4, {"route": "/api/dependency"})
```

## 한 줄 요약
- 메트릭: "이상이 생겼는지" 빠르게 본다.
- 트레이스: "어디서 문제인지" 경로를 좁힌다.
- 로그: "왜 문제인지" 증거를 확보한다.
