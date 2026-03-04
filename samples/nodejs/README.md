# Node.js (Express) → Azure Monitor 데이터 흐름 (샘플 기준)

## 이 샘플이 보여주는 것(TL;DR)

- Express 요청을 자동 계측해 **요청 Trace**를 만들고 Azure Monitor로 전송합니다.
- 미들웨어에서 active span에 **5W1H(Who/Where/What/Why/How)** 를 attribute로 주입합니다.
- `/custom-event`에서 **커스텀 메트릭(`custom_event_counter`)** 을 전송합니다.

## 주요 파일

- `express_app.js`: OTel 초기화(`useAzureMonitor`), 5W1H 주입, 라우트별 신호 생성 예시

## 필수 설정 값

- `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - 예: `InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;`
- 서비스 식별(권장)
  - (권장) `OTEL_SERVICE_NAME=node-api`
  - (권장) `OTEL_RESOURCE_ATTRIBUTES=service.version=1.0.0,deployment.environment=Lab`
  - 현재 샘플 코드는 서비스명을 강제하지 않으므로, 환경변수로 지정해두면 KQL 필터가 쉬워집니다.
- 5W1H 필드명은 **고정**
  - `Who`, `Where`, `What`, `Why`, `How`

## 데이터 흐름(요청 1건 기준) – 단계별

```text
[프로세스 시작]
    |
    +--> (중요) useAzureMonitor(...)로 OTel SDK + Exporter 초기화
    |          - Express/HTTP 모듈 로드 전에 실행해야 자동 계측이 붙음
    |
    v
[HTTP 요청 -> Express]
    |
    +--> (자동) Express instrumentation: Request Span 생성
    |
    +--> (수동) app.use(...) 미들웨어:
    |          active span에 5W1H + 공통 필드 attribute 주입
    |
    +--> (수동) 라우트에서 신호 생성
               - span.addEvent(...) (Span 이벤트)
               - meter Counter add(...) (메트릭)
               - throw Error(...) (예외)
    |
    v
[OTel SDK 배치] -> [Azure Monitor Exporter 전송] -> [Application Insights -> LAW]
```

## 5W1H 주입 위치(코드 기준)

- `app.use((req, res, next) => { ... })`
  - `trace.getActiveSpan()`이 null이 아니면, 해당 span에 `Who/Where/What/Why/How`를 세팅합니다.

### active span이 없을 때(컨텍스트가 끊긴 경우)

이 샘플은 `/logs`에서 active span이 없으면 `tracer.startActiveSpan(...)`으로 수동 span을 시작합니다.  
실서비스에서는 “초기화 순서(= useAzureMonitor 먼저)” 또는 async 컨텍스트 전파 문제부터 의심하는 것이 보통 우선입니다.

## Node.js 스택 특징(운영 관점)

### 1) 초기화 순서가 “정확히” 중요함 (require-hooking)

- Node는 모듈 로딩(`require`) 시점에 자동 계측이 패치(몽키패치)되는 경우가 많습니다.
- 그래서 이 샘플처럼 **`useAzureMonitor(...)`를 Express/HTTP보다 먼저 실행**해야,
  Express 라우팅/HTTP 서버 계층에 자동 계측이 정상적으로 붙습니다.

### 2) 컨텍스트 전파는 비동기(Async) 품질에 좌우됨

- `trace.getActiveSpan()`은 “현재 async 컨텍스트에 활성 span이 이어져 있는지”에 의존합니다.
- 아래 상황에서 active span이 `null`이 되는 경우가 흔합니다.
  - 초기화 순서가 깨진 경우
  - 컨텍스트 전파를 깨는 라이브러리(특정 callback/async 패턴)
  - 요청 처리 중 span을 종료/분리해버린 경우
- 이 샘플은 학습용으로 `/logs`에서 “active span이 없으면 수동 span 시작” 분기를 넣어두었습니다.
  운영에서는 “왜 컨텍스트가 끊겼는지”를 먼저 고치는 것이 보통 더 낫습니다.

### 3) Node에선 “로그”보다 “메트릭/트레이스 이벤트”가 먼저 쉬움

- 이 샘플은 **로그 전송 파이프라인을 따로 만들지 않고**, `span.addEvent(...)`와 `AppMetrics`로 확인 가능한 메트릭을 사용합니다.
- `console.log/error`는 환경에 따라 `AppTraces`로 자동 수집되지 않을 수 있습니다.
  “로그를 반드시 `AppTraces`로 보내야 한다”면, 별도의 로그 파이프라인(로거 + OTel logs)을 구성하는 것이 일반적입니다.

### 4) 비용/성능 관점: 메트릭이 기본, 트레이스/로그는 샘플링

- Node 서비스는 트래픽이 빠르게 늘어날 수 있어, 트레이스/로그를 무제한으로 남기면 비용이 급증하기 쉽습니다.
- 운영에서는 “메트릭으로 상태를 보고 → 특정 이슈 구간만 트레이스/로그를 깊게” 보는 전략(샘플링/필터)이 안정적입니다.

## 엔드포인트 → 생성 신호 매트릭스

| Endpoint | 자동 생성(주요) | 수동 생성(주요) | 5W1H 주입 | 주로 확인할 테이블 |
|---|---|---|---|---|
| `GET /` | 요청 Trace | - | 요청 Span attribute | `AppRequests` |
| `GET /health` | 요청 Trace | - | 요청 Span attribute | `AppRequests` |
| `GET /logs` | 요청 Trace | Span Event(예시) | 요청 Span attribute | `AppRequests` (+ Span Event는 표시 위치가 다를 수 있음) |
| `GET /custom-event` | 요청 Trace | 메트릭 `custom_event_counter` + Span Event | 요청 Span attribute | `AppRequests`, `AppMetrics` |
| `GET /dependency` | 요청 Trace | 수동 Span(`GET /users ...`) | 요청 Span attribute | `AppRequests`, `AppDependencies` |
| `GET /error` | 요청 Trace + 예외 | - | 요청 Span attribute | `AppExceptions` |

## KQL로 확인하기

> 우선 “요청(Req)”과 “메트릭(Metric)”부터 확인하는 것을 권장합니다.

### (1) 최근 요청 + 5W1H 확인

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where tostring(Properties["Where"]) startswith "node-api:"
      or AppRoleName == "node-api"
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, Name, Url, ResultCode, DurationMs, Success,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          What = tostring(Properties["What"]),
          Why = tostring(Properties["Why"]),
          How = tostring(Properties["How"])
| take 20
```

### (2) 최근 예외 확인 (`/error`)

```kusto
AppExceptions
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, OuterMessage, ProblemId
| take 20
```

### (3) 커스텀 메트릭 확인 (`custom_event_counter`)

```kusto
AppMetrics
| where TimeGenerated > ago(30m)
| where Name == "custom_event_counter" or Name contains "custom_event"
| order by TimeGenerated desc
| take 50
```

> 메트릭은 즉시 1:1로 보이지 않고 집계/배치로 들어올 수 있습니다.  
> 이름이 헷갈리면 먼저 아래로 “최근 30분에 들어온 메트릭 이름들”을 확인하세요.

```kusto
AppMetrics
| where TimeGenerated > ago(30m)
| summarize count() by Name
| order by count_ desc
```

## 실행

```bash
cd samples/nodejs

export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=...;"
export OTEL_SERVICE_NAME="node-api"
export OTEL_RESOURCE_ATTRIBUTES="service.version=1.0.0,deployment.environment=Lab"

npm init -y
npm i express @azure/monitor-opentelemetry @opentelemetry/api

node express_app.js
```

## 빠른 검증 순서(권장)

```bash
curl -s http://localhost:3000/health
curl -s http://localhost:3000/logs
curl -s http://localhost:3000/custom-event
curl -s http://localhost:3000/dependency
curl -s http://localhost:3000/error
```

## 트러블슈팅

- **요청이 안 보임**
  - `APPLICATIONINSIGHTS_CONNECTION_STRING` 값 확인
  - `useAzureMonitor(...)`가 Express import보다 먼저 실행되는지 확인
  - Azure Logs의 시간 범위를 넓혀서 확인(예: 24시간)
- **5W1H가 비어 있음**
  - KQL에서 `take 5`로 `Properties`를 먼저 확인(실제 키/중첩 구조 확인)
  - 이 샘플은 `Where=node-api:<path>` 형태로 넣으므로 `Properties["Where"]` 기반 필터를 권장
- **메트릭이 안 보임**
  - `/custom-event`를 여러 번 호출 후 1~2분 뒤 재확인(배치/집계 지연)
  - `AppMetrics | where TimeGenerated > ago(30m) | summarize count() by Name`로 실제 metric 이름을 먼저 확인
