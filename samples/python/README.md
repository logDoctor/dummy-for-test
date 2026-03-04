# Python (FastAPI) → Azure Monitor 데이터 흐름 (샘플 기준)

## 이 샘플이 보여주는 것(TL;DR)

- **HTTP 요청/의존성/예외**는 OpenTelemetry가 Span으로 기록하고, Exporter가 Azure Monitor로 전송합니다.
- **로그**는 Python `logging`에 필터를 붙여 `custom_dimensions`(5W1H 포함)을 자동 주입하고 Azure로 전송합니다.
- Azure 쪽에서는 보통 `AppRequests`/`AppDependencies`/`AppTraces`/`AppExceptions`/`AppMetrics` 테이블에서 확인합니다(워크스페이스 기반 Application Insights).

## 주요 파일

- `fastapi_app.py`: 단일 파일 샘플(OTel 초기화, 5W1H 미들웨어, 로그 필터, 커스텀 SpanProcessor 포함)
- `requirements.txt`: 의존성 목록

## 필수 설정 값

- `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - 예: `InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;`
- 서비스 식별(이 샘플은 코드에서 설정)
  - `fastapi_app.py`에서 `OTEL_SERVICE_NAME=python-api`로 설정합니다.
- 5W1H 필드명은 **고정**
  - `Who`, `Where`, `What`, `Why`, `How` (대/소문자 포함)

## 데이터 흐름(요청 1건 기준) – 단계별

```text
[클라이언트 HTTP 요청]
        |
        v
 FastAPI 라우팅
        |
        +--> (자동) FastAPIInstrumentor: Request Span 시작/종료
        |
        +--> (수동) @app.middleware("http"):
        |        Span attribute로 5W1H + 공통 필드 주입
        |
        +--> (수동) 라우트에서 신호 생성
                 - logger.info/warning/error (로그)
                 - tracer.start_as_current_span(...) (커스텀 Span/의존성)
                 - Exception 발생 (예외)
        |
        v
 OpenTelemetry SDK
  - TracerProvider / SpanProcessor(커스텀) / BatchSpanProcessor(배치)
  - (로그) GlobalDimensionsFilter로 custom_dimensions 보강
        |
        v
 Azure Monitor Exporter
  - 직렬화(Envelope) + 배치 전송 + 재시도
  - (옵션) 오프라인 버퍼링(디스크 임시 저장 후 재전송)
        |
        v
 Application Insights (workspace-based) -> Log Analytics Workspace(LAW)
  - AppRequests / AppDependencies / AppTraces / AppExceptions / AppMetrics
```

## 이 샘플의 커스터마이즈 포인트(코드 기준)

- `configure_azure_monitor(...)`
  - Azure Monitor Exporter 파이프라인(Trace/Log/Metric)을 구성하는 시작점입니다.
- `FastAPIInstrumentor.instrument_app(app)`
  - 모든 HTTP 요청을 자동으로 추적(Request Span 생성)합니다.
- 5W1H 주입 위치: `@app.middleware("http")`
  - 요청 span에 `Who/Where/What/Why/How`를 attribute로 주입합니다.
- `GlobalDimensionsFilter`
  - Python `logging` record에 `custom_dimensions`를 만들어 5W1H + 공통 필드를 자동 주입합니다.
  - 결과적으로 `AppTraces.Properties["custom_dimensions"]`에서 조회하도록 설계되어 있습니다.
- `DropUnknownRouteProcessor`
  - 404 같은 노이즈(span)를 줄이려는 목적의 커스텀 `SpanProcessor`입니다.

## Python 스택 특징(운영 관점)

### 1) “구조화 로그”를 가장 싸고 강하게 만들기 좋음

- Python은 표준 `logging` 생태계가 탄탄해서, **로그를 구조화(= key/value)하는 비용이 낮습니다.**
- 이 샘플은 `GlobalDimensionsFilter`로 모든 로그에 기본 `custom_dimensions`를 깔아두고,
  엔드포인트에서 `logger.info(..., extra={"custom_dimensions": {...}})`로 **감사/보안 같은 고가치 필드만 추가**하도록 구성돼 있습니다.
- 운영 팁
  - `custom_dimensions` 키는 팀 전체에서 **고정된 이름**을 쓰는 것이 KQL 비용을 줄입니다.
  - UUID/랜덤 해시 같은 **고카디널리티 값**을 “필터 키”로 남발하면 비용/성능이 급격히 나빠질 수 있습니다.
  - 민감정보(이름/전화/주민/카드 등)는 원문 저장을 피하고 마스킹/익명화 후 저장하세요.

### 2) Trace/Log 상관관계(Correlation)가 비교적 쉬움

- OTel 자동 계측(FastAPIInstrumentor)으로 요청 span이 활성화된 상태에서 로그를 남기면,
  (환경/SDK 설정에 따라) **로그와 트레이스가 같은 operation으로 묶여** “이 요청의 로그만” 같은 디버깅이 쉬워집니다.
- 아래 KQL 섹션에 “OperationId로 묶어서 보기(가능한 경우)” 예시를 포함합니다.

### 3) 비동기/백그라운드 작업은 컨텍스트 전파가 관건

- 요청 처리 중에는 `trace.get_current_span()`가 잘 동작하지만,
  요청과 분리된 백그라운드 작업(스케줄러/스레드/큐 소비자)에서는 **현재 span이 없을 수 있습니다.**
- 이런 작업은 별도의 span을 시작하고(`tracer.start_as_current_span(...)`), 필요한 컨텍스트(Who/Where/What/Why/How)는 명시적으로 넣는 쪽이 안전합니다.

## 엔드포인트 → 생성 신호 매트릭스

| Endpoint | 자동 생성(주요) | 수동 생성(주요) | 5W1H 주입 | 주로 확인할 테이블 |
|---|---|---|---|---|
| `GET /api/health` | 요청 Trace | `logger.info` | 요청 Span + 로그 `custom_dimensions` | `AppRequests`, `AppTraces` |
| `GET /api/logs` | 요청 Trace | INFO/WARN/ERROR 로그 | 로그 `custom_dimensions` | `AppTraces` |
| `GET /api/custom-event` | 요청 Trace | `CustomEvent: UserCheckout` Span + 로그 | 요청/커스텀 Span attribute | `AppDependencies`, `AppTraces` |
| `GET /api/dependency` | 요청 Trace | `Simulated_SQL_Query` Span | Span attribute(`db.*` 포함) | `AppDependencies` |
| `GET /api/secret-data` | 요청 Trace | 감사(Audit) Span + 감사 로그(custom_dimensions) | Span attribute + 로그 custom_dimensions | `AppDependencies`, `AppTraces` |
| `GET /api/error` | 요청 Trace + 예외 | `logger.error`(핸들러) | 요청 Span + 로그 custom_dimensions | `AppExceptions`, `AppTraces` |

## KQL로 확인하기

> 먼저 Azure Portal → Log Analytics Workspace → Logs 에서 시간 범위를 최근 30분~24시간으로 잡고 실행합니다.

### (1) 최근 요청 확인

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where AppRoleName == "python-api" or tostring(Properties["Where"]) startswith "python-api:"
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, Name, Url, ResultCode, DurationMs, Success,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          What = tostring(Properties["What"]),
          Why = tostring(Properties["Why"]),
          How = tostring(Properties["How"])
| take 20
```

### (2) 감사(Audit) 로그 확인 (`/api/secret-data`)

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where Message contains "Audit success"
| project TimeGenerated, AppRoleName, SeverityLevel, Message,
          Action = tostring(Properties["custom_dimensions"]["Audit_Action"]),
          UserId = tostring(Properties["custom_dimensions"]["Actor_User_ID"]),
          DocId  = tostring(Properties["custom_dimensions"]["Target_Document_ID"]),
          Where  = tostring(Properties["custom_dimensions"]["Where"]),
          Who    = tostring(Properties["custom_dimensions"]["Who"])
| order by TimeGenerated desc
| take 50
```

### (3) 감사(Audit) Span 확인(소요 시간 포함)

```kusto
AppDependencies
| where TimeGenerated > ago(30m)
| where Name == "Audit_Action: SecretDocumentRead"
| project TimeGenerated, AppRoleName, Name, DurationMs,
          Actor  = tostring(Properties["Security.Actor"]),
          Target = tostring(Properties["Security.Target"]),
          Result = tostring(Properties["Security.Result"])
| order by TimeGenerated desc
| take 50
```

### (4) 최근 예외 확인 (`/api/error`)

```kusto
AppExceptions
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, OuterMessage, ProblemId
| take 20
```

### (5) (선택) “한 요청” 기준으로 로그/의존성 묶어보기

> `OperationId` 컬럼이 없거나 이름이 다르면, 먼저 `AppRequests | take 1`로 스키마를 확인하세요.

```kusto
let opId = toscalar(
  AppRequests
  | where TimeGenerated > ago(30m)
  | where AppRoleName == "python-api" or tostring(Properties["Where"]) startswith "python-api:"
  | top 1 by TimeGenerated desc
  | project OperationId
);

AppTraces
| where TimeGenerated > ago(30m)
| where OperationId == opId
| order by TimeGenerated desc
| project TimeGenerated, SeverityLevel, Message, Properties
| take 50
```

## 실행

```bash
cd samples/python

export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=...;"

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

## 빠른 검증 순서(권장)

```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/logs
curl -s http://localhost:8000/api/custom-event
curl -s http://localhost:8000/api/dependency
curl -s http://localhost:8000/api/secret-data
curl -s http://localhost:8000/api/error
```

> 호출 후 Azure 쪽 반영까지 **몇 초~수십 초 지연**이 있을 수 있습니다(배치 전송/네트워크/수집 지연).

## 트러블슈팅

- **데이터가 아예 안 들어옴**
  - `APPLICATIONINSIGHTS_CONNECTION_STRING` 값/따옴표/공백 확인
  - VM/컨테이너의 아웃바운드 443이 Azure Monitor 엔드포인트로 열려있는지 확인
  - Azure Logs 화면의 시간 범위를 넓혀서 확인(예: 24시간)
- **요청은 보이는데 5W1H가 비어 있음**
  - `GET /api/...` 경로로 호출했는지 확인(미들웨어는 해당 라우트 기준)
  - KQL에서 `tostring(Properties["Where"])`로 실제 저장 키를 먼저 확인
- **로그 custom_dimensions가 안 보임**
  - 로그 쿼리에서 `Properties`를 `take 5`로 덤프해 실제 구조 확인
- **전송 지연/간헐적 누락**
  - 배치 전송이므로 즉시 보이지 않을 수 있음(1~2분 후 재확인)
  - 네트워크 단절 시 Exporter가 임시 경로(예: Linux `/var/tmp/`, Windows `%TEMP%`)에 오프라인 버퍼 파일을 만들 수 있음

## 참고(이 저장소 내부)

- 전체 흐름(파이썬 기준 요약): `projects/오픈텔레메트리-애저모니터-데이터흐름.md`
