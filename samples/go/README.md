# Go (Gin + ApplicationInsights-Go) → Azure Monitor 데이터 흐름 (샘플 기준)

> 이 Go 샘플은 OpenTelemetry가 아니라 **ApplicationInsights-Go(레거시 SDK)** 로 전송합니다.  
> 즉, “자동 계측”보다는 “코드에서 Telemetry를 직접 만들고 `Track(...)`”하는 방식입니다.

## 이 샘플이 보여주는 것(TL;DR)

- Gin 미들웨어에서 요청 시간을 재고 **RequestTelemetry** 를 만들어 `AppRequests`로 보냅니다.
- 라우트에서 `TrackTrace/TrackException/TrackEvent/Track(RemoteDependencyTelemetry)`로 신호를 직접 전송합니다.
- 5W1H는 `RequestTelemetry.Properties[...]`에 넣어 **검색 가능한 Custom Properties**로 만듭니다.

## 주요 파일

- `go_app.go`: TelemetryClient 초기화 + Gin middleware + 엔드포인트별 Track 예시

## 필수 설정 값

- `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - 예: `InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;`
- 서비스 식별(이 샘플은 코드에서 설정)
  - `ai.cloud.role = go-api` (Azure에서 `AppRoleName`으로 보통 조회)
- 5W1H 필드명은 **고정**
  - `Who`, `Where`, `What`, `Why`, `How`

## Track API → LAW 테이블(대략 매핑)

> 워크스페이스 기반 Application Insights 기준 “보통” 아래처럼 들어갑니다.

| Go 코드 | 의미 | 주로 보이는 테이블 |
|---|---|---|
| `client.Track(requestTelemetry)` | 요청(Request) | `AppRequests` |
| `client.Track(dependencyTelemetry)` | 의존성(Dependency) | `AppDependencies` |
| `client.TrackTrace(...)` | 로그/트레이스 | `AppTraces` |
| `client.TrackException(...)` | 예외 | `AppExceptions` |
| `client.TrackEvent(...)` / `client.Track(eventTelemetry)` | 커스텀 이벤트 | `AppEvents` (환경에 따라 다를 수 있음) |

## 데이터 흐름(요청 1건 기준) – 단계별

```text
[HTTP 요청 -> Gin]
    |
    +--> (수동) TelemetryMiddleware:
    |          - start/end 시간으로 duration 계산
    |          - RequestTelemetry 생성
    |          - Properties에 5W1H 주입
    |          - client.Track(requestTelemetry)
    |
    +--> (수동) 라우트에서 신호 생성
               - TrackTrace / TrackException / TrackEvent / Track(Dependency)
    |
    v
[ApplicationInsights-Go 채널 전송] -> [Application Insights -> LAW]
```

## 5W1H 주입 위치(코드 기준)

- `TelemetryMiddleware(...)`
  - `request.Properties["Where"] = "go-api:" + path` 형태로 넣습니다.

## Go 스택 특징(운영 관점)

### 1) “명시적 전송”이라 동작이 예측 가능하지만, 자동 계측은 없다

- 레거시 SDK 방식은 “어떤 신호를 언제 보낼지”가 코드에 그대로 드러나서 디버깅이 쉽습니다.
- 반대로 OpenTelemetry처럼 프레임워크/라이브러리 자동 계측이 붙는 구조가 아니기 때문에,
  **요청/의존성/예외/이벤트를 빠뜨리지 않게 설계**하는 것이 중요합니다.

### 2) 분산 추적(Correlation)은 추가 작업이 필요할 수 있음

- 이 샘플은 “요청 텔레메트리”와 “의존성/이벤트 텔레메트리”를 각각 Track 합니다.
- 운영에서 “요청 1건을 기준으로 의존성/이벤트가 트리 형태로 딸려오게” 하려면,
  보통 Operation/Parent 컨텍스트(예: operation id, parent id)를 맞춰주는 작업이 필요합니다.
  (이 샘플은 학습용으로 단순화되어 있어, 상관관계가 완벽하지 않을 수 있습니다.)

### 3) 종료 시 flush가 매우 중요함

- ApplicationInsights-Go는 내부 채널에 버퍼링했다가 전송합니다.
- 프로세스가 바로 종료되면 일부 신호가 유실될 수 있으니,
  이 샘플처럼 `client.Channel().Close()`로 flush하는 습관이 중요합니다.

## 엔드포인트 → 생성 신호 매트릭스

| Endpoint | 자동 생성(주요) | 수동 생성(주요) | 5W1H 주입 | 주로 확인할 테이블 |
|---|---|---|---|---|
| `GET /` | - | `TrackEvent("HelloWorld_Go")` + 요청 전송 | 요청 Properties | `AppEvents`, `AppRequests` |
| `GET /health` | - | 요청 전송 | 요청 Properties | `AppRequests` |
| `GET /logs` | - | `TrackTrace`(INFO/WARN/ERROR) + 요청 전송 | 요청 Properties | `AppTraces`, `AppRequests` |
| `GET /custom-event` | - | `Track(EventTelemetry("UserCheckout_Go"))` + 요청 전송 | 요청 Properties | `AppEvents`, `AppRequests` |
| `GET /dependency` | - | `Track(RemoteDependencyTelemetry(...))` + 요청 전송 | 요청 Properties | `AppDependencies`, `AppRequests` |
| `GET /error` | - | `TrackException(...)` + 요청 전송 | 요청 Properties | `AppExceptions`, `AppRequests` |

## KQL로 확인하기

### (1) 최근 요청 + 5W1H 확인

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where AppRoleName == "go-api" or tostring(Properties["Where"]) startswith "go-api:"
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
| where AppRoleName == "go-api"
| order by TimeGenerated desc
| project TimeGenerated, OuterMessage, ProblemId
| take 20
```

### (3) 커스텀 이벤트 확인 (`/custom-event`)

```kusto
AppEvents
| where TimeGenerated > ago(30m)
| where Name == "UserCheckout_Go"
| order by TimeGenerated desc
| take 20
```

> 만약 `AppEvents`가 비어 있다면(환경/설정에 따라 다름), 아래처럼 “이벤트 이름”으로 전체 테이블을 먼저 훑어보세요.

```kusto
AppEvents
| where TimeGenerated > ago(30m)
| summarize count() by Name
| order by count_ desc
```

### (4) 의존성 확인 (`/dependency`)

```kusto
AppDependencies
| where TimeGenerated > ago(30m)
| where AppRoleName == "go-api"
| order by TimeGenerated desc
| project TimeGenerated, Name, Target, Type, Data, DurationMs, Success
| take 50
```

## 실행

```bash
cd samples/go

export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=...;"

go mod init go-ai-sample
go get github.com/microsoft/ApplicationInsights-Go/appinsights
go get github.com/gin-gonic/gin

go run go_app.go
```

## 빠른 검증 순서(권장)

```bash
curl -s http://localhost:8080/health
curl -s http://localhost:8080/logs
curl -s http://localhost:8080/custom-event
curl -s http://localhost:8080/dependency
curl -s http://localhost:8080/error
```

## 트러블슈팅

- **데이터가 안 보임**
  - `APPLICATIONINSIGHTS_CONNECTION_STRING` 확인
  - 서버 아웃바운드 443 허용 여부 확인
  - Azure Logs 시간 범위 확장(예: 24시간)
- **5W1H가 비어 있음**
  - `AppRequests | take 5`로 `Properties` 구조를 먼저 확인(키/중첩 구조 확인)
