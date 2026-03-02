# 현대 로그 설계 실무

## 목적
"텍스트 로그"에서 "운영 가능한 로그"로 전환하기 위한 실무 기준입니다.

---

## 원칙 1: 구조화 로그 (Structured Logging)

❌ **나쁜 예 (plain text):**
```
[2026-03-01 13:00:01] ERROR - payment failed for user 1234, order 9999, code 503
```

✅ **좋은 예 (structured JSON):**
```json
{
  "timestamp": "2026-03-01T13:00:01Z",
  "severity": "ERROR",
  "event": "payment_failed",
  "user_id": "user-1234",
  "order_id": "order-9999",
  "error_code": "PAYMENT_503",
  "duration_ms": 3050
}
```

메시지는 짧게, 핵심 데이터는 Key-Value로 분리합니다.  
→ KQL로 `error_code == "PAYMENT_503"`처럼 필터가 즉시 가능해집니다.

---

## 원칙 2: 컨텍스트 자동 주입 (Context Injection)

요청마다 공통 필드를 손으로 입력하지 말고, **미들웨어/필터에서 자동으로 붙여줍니다.**

Python FastAPI 예시 (`fastapi_app.py` 참고):
```python
@app.middleware("http")
async def add_custom_telemetry_middleware(request: Request, call_next):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("Who", request.client.host)
        span.set_attribute("Where", f"python-api:{request.url.path}")
        span.set_attribute("How", request.method)
        span.set_attribute("Environment", "Production")
    return await call_next(request)
```

**최소 권장 자동 주입 필드:**

| 필드 | 설명 |
|---|---|
| `trace_id` | 요청 단위 고유 식별자 |
| `service` / `Where` | 어느 마이크로서비스인지 |
| `environment` | dev / staging / production |
| `version` | 배포 버전 (디버깅 기준) |
| `client_ip` / `Who` | 요청자 IP |
| `method` / `How` | HTTP 메서드 |
| `path` | 요청 경로 |

---

## 원칙 3: 상관관계(Trace) 연결

서비스 A → 서비스 B → DB로 이어지는 요청에서,  
**같은 Trace ID가 모든 서비스 로그에 흘러야** 단일 요청 흐름 전체를 볼 수 있습니다.

OpenTelemetry는 이 Context Propagation을 HTTP Header(`traceparent`)로 자동 전달합니다.

---

## 권장 로그 레벨 기준

| 레벨 | 사용 기준 | 예시 |
|---|---|---|
| `INFO` | 정상 비즈니스 이벤트 | 주문 완료, 로그인 성공, 파일 업로드 |
| `WARNING` | 재시도 가능한 이슈 | 외부 API 지연, 캐시 미스, 임계치 근접 |
| `ERROR` | 사용자에게 영향이 있는 실패 | 결제 실패, DB 연결 끊김 |
| `DEBUG` | 개발/단기 진단 전용 | 운영 환경 기본 **OFF** |

---

## 안티패턴 (하면 안 되는 것들)

| 안티패턴 | 문제 | 대안 |
|---|---|---|
| 긴 텍스트 덤프 무분별 저장 | GB 비용 폭탄, 검색 불가 | 메시지 짧게, 데이터는 필드로 |
| 서비스마다 필드명이 다름 | `userId` vs `user_id` vs `UserId` 혼재 | 팀 공통 스키마 문서 강제화 |
| PII/민감정보 마스킹 안 함 | 개인정보보호법 위반 | 카드번호/주민번호는 마스킹 후 저장 |
| DEBUG 로그 운영 ON | 불필요한 ingestion 비용 | 환경변수로 레벨 제어 |

---

## 체크리스트

- [ ] 모든 주요 이벤트가 JSON 구조로 남는가?
- [ ] 표준 필드 이름이 팀 전체에서 동일한가?
- [ ] 고비용 로그(DEBUG/대용량 payload) 제어 장치가 있는가?
- [ ] 민감정보 마스킹이 적용돼 있는가?
- [ ] 로그 레벨이 환경변수로 제어 가능한가?
