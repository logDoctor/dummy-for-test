# 프레임워크별 추출 데이터 요약

## 목적
스택별로 "무엇이 자동"이고 "무엇을 수동"으로 넣어야 하는지 한 번에 비교합니다.

---

## 자동 계측 vs 수동 계측 비교표

| 스택 | 자동 계측 내용 | 수동 추가 필요 |
|---|---|---|
| **Python (FastAPI)** | HTTP 요청Trace, 예외, 기본 의존성 | `start_as_current_span()` 비즈니스 이벤트, 감사 필드 |
| **Node.js (Express)** | Express 요청 추적, 기본 예외 | Span 이벤트, 커스텀 메트릭 |
| **.NET (ASP.NET Core)** | 모든 요청/응답, 로그 자동 수집 | `ActivitySource` 기반 도메인 이벤트 |
| **Java (Spring Boot)** | 에이전트 기반 자동 계측 (코드 변경 최소) | 비즈니스 도메인 Attribute 확장 |
| **Go** | HTTP 핸들러/클라이언트 계측 구성 필요 | 고가치 도메인 필드 명시 |

---

## Python (FastAPI) 상세

### 자동 수집 (코드 추가 없음)
```python
FastAPIInstrumentor.instrument_app(app)
# → AppRequests: 모든 HTTP 요청/응답 자동 캡처
# → AppExceptions: 미처리 예외 자동 캡처
```

### 수동 계측 A: 커스텀 비즈니스 이벤트
```python
with tracer.start_as_current_span("CustomEvent: UserCheckout") as span:
    span.set_attribute("order.id", "order-9999")
    span.set_attribute("payment.method", "card")
    # → AppDependencies 테이블에 기록
```

### 수동 계측 B: 감사 로그 (Custom Properties 포함)
```python
logger.info(
    "Audit: document viewed",
    extra={
        "custom_dimensions": {
            "Audit_Action": "VIEW_DOCUMENT",
            "Actor_User_ID": user_id,
            "Target_Document_ID": document_id,
        }
    }
)
# → AppTraces.Properties["custom_dimensions"] 에 저장
```

---

## Node.js (Express) 상세

### 자동 수집
```javascript
const { NodeTracerProvider } = require("@opentelemetry/sdk-trace-node");
const { ExpressInstrumentation } = require("@opentelemetry/instrumentation-express");
// → AppRequests 자동 수집
```

### 수동 계측
```javascript
const span = tracer.startSpan("CustomEvent: ProcessOrder");
span.setAttribute("order.id", "order-123");
span.end();
```

---

## Java (Spring Boot) 상세

Java는 **Java 에이전트 방식**이 가장 권장됩니다. 코드를 거의 수정하지 않습니다.

```json
// applicationinsights.json 에서 자동 수집 설정
{
  "role": { "name": "java-api" },
  "sampling": { "percentage": 10 }
}
```

수동으로 추가할 때:
```java
Span span = tracer.spanBuilder("BusinessEvent: Checkout").startSpan();
span.setAttribute("user.id", userId);
span.end();
```

---

## 결론

| 원칙 | 이유 |
|---|---|
| **자동 계측으로 먼저 시작** | 코드 변경 없이 기본 신호를 즉시 확보 |
| **비즈니스 가치 높은 이벤트만 수동 추가** | 불필요한 수집 → 비용 증가 |
| **감사/보안 데이터는 반드시 수동 명시** | 자동 계측은 비즈니스 의미를 모름 |
