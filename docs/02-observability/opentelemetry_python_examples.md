# Python(FastAPI) OTel 예시 가이드

## 목적
현재 샘플(`/samples/python/fastapi_app.py`) 기준으로 어떤 엔드포인트가 어떤 신호를 만드는지 정리합니다.

---

## 실행

```bash
cd samples/python
pip install -r requirements.txt
python fastapi_app.py
# 또는
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`

---

## 엔드포인트별 신호 상세

### `GET /api/health` — 기본 정상 응답 확인
```bash
curl http://localhost:8000/api/health
# → {"status": "ok"}
```

**생성되는 신호:**
- `AppRequests`: 요청 1건 (자동, FastAPIInstrumentor)
- `AppTraces`: `INFO "Health check request received"` 로그

---

### `GET /api/logs` — 여러 레벨 로그 한 번에 생성
```bash
curl http://localhost:8000/api/logs
```

**생성되는 신호:**
- `AppTraces` × 3건 (severity: Information, Warning, Error)
- 각 로그에 `custom_dimensions`로 `Environment`, `AppVersion`, `Where` 자동 포함

**LAW 확인 쿼리:**
```kusto
AppTraces
| where Properties["Where"] == "python-api"
| order by TimeGenerated desc
| take 10
```

---

### `GET /api/custom-event` — 커스텀 비즈니스 이벤트 Span
```bash
curl http://localhost:8000/api/custom-event
```

**생성되는 신호:**
- `AppDependencies`: Span 이름 `"CustomEvent: UserCheckout"` (수동 계측)
- `AppTraces`: "User checkout process started..." 로그

**LAW 확인 쿼리:**
```kusto
AppDependencies
| where Name startswith "CustomEvent"
| project TimeGenerated, Name, DurationMs
| order by TimeGenerated desc
```

---

### `GET /api/dependency` — DB 의존성 추적 Span
```bash
curl http://localhost:8000/api/dependency
```

**생성되는 신호:**
- `AppDependencies`: Span `"Simulated_SQL_Query"` + `db.system`, `db.statement` 속성 포함

**LAW 확인 쿼리:**
```kusto
AppDependencies
| where Name == "Simulated_SQL_Query"
| project TimeGenerated, Name, DurationMs,
          DbSystem = tostring(Properties["db.system"]),
          DbStatement = tostring(Properties["db.statement"])
```

---

### `GET /api/secret-data` — 보안 감사(Audit) 로그 ⭐ 핵심
```bash
curl http://localhost:8000/api/secret-data
# → {"message":"...", "user_id":"user-2161", "document_id":44}
```

**생성되는 신호:**
- `AppDependencies`: Span `"Audit_Action: SecretDocumentRead"` + 5개 보안 속성
- `AppTraces`: 감사 로그 1건 + `custom_dimensions`에 `Audit_Action`, `Actor_User_ID`, `Target_Document_ID` 포함

**LAW 확인 쿼리 (텍스트 로그):**
```kusto
AppTraces
| where Message contains "Audit success"
| project TimeGenerated, Message,
          Action = tostring(Properties["custom_dimensions"]["Audit_Action"]),
          UserId = tostring(Properties["custom_dimensions"]["Actor_User_ID"]),
          DocId  = tostring(Properties["custom_dimensions"]["Target_Document_ID"])
| order by TimeGenerated desc
```

**LAW 확인 쿼리 (Span 단위, 소요 시간 포함):**
```kusto
AppDependencies
| where Name == "Audit_Action: SecretDocumentRead"
| project TimeGenerated, DurationMs,
          Actor  = tostring(Properties["Security.Actor"]),
          Target = tostring(Properties["Security.Target"]),
          Result = tostring(Properties["Security.Result"])
| order by TimeGenerated desc
```

---

### `GET /api/error` — 예외 추적 테스트
```bash
curl http://localhost:8000/api/error
# → {"message":"An intentional error occurred..."}
```

**생성되는 신호:**
- `AppExceptions`: 스택 트레이스 포함 자동 캡처 (FastAPIInstrumentor + ASGI 레이어)
- `AppTraces`: `ERROR "Global exception caught: ..."` 로그

**LAW 확인 쿼리:**
```kusto
AppExceptions
| order by TimeGenerated desc
| project TimeGenerated, ProblemId, OuterMessage, AppRoleName
| take 10
```

---

## 핵심 포인트 정리

| 기능 | 코드 위치 | LAW 테이블 |
|---|---|---|
| 모든 요청 자동 추적 | `FastAPIInstrumentor.instrument_app(app)` | `AppRequests` |
| 5W1H 컨텍스트 자동 주입 | `add_custom_telemetry_middleware` | `AppRequests` Properties |
| 구조화 로그 | `logger.info(...)` + `GlobalDimensionsFilter` | `AppTraces` |
| 커스텀 비즈니스 이벤트 | `tracer.start_as_current_span(...)` | `AppDependencies` |
| 예외 자동 캡처 | `@app.exception_handler` + SDK 훅 | `AppExceptions` |
| 404 스팸 필터링 | `DropUnknownRouteProcessor` | (Azure로 전송 안 됨) |
