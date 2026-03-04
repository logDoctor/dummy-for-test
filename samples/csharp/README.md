# .NET (ASP.NET Core) → Azure Monitor 데이터 흐름 (샘플 기준)

## 이 샘플이 보여주는 것(TL;DR)

- `AddOpenTelemetry().UseAzureMonitor()`로 **요청/의존성/예외**를 자동 계측하고 Azure Monitor로 전송합니다.
- 미들웨어에서 `Activity.Current`에 **5W1H(Who/Where/What/Why/How)** 를 tag로 주입합니다.
- `ActivitySource`로 만든 **커스텀 Activity** 는 “리스너(= Source 등록)”가 없으면 export되지 않을 수 있습니다(이 샘플은 문서로만 안내).

## 주요 파일

- `Program.cs`: OTel + Azure Monitor 설정, 5W1H 미들웨어, 라우트 예시
- `csharp_app.csproj`: `Azure.Monitor.OpenTelemetry.AspNetCore` 패키지 참조

## 필수 설정 값

- `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - 예: `InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;`
- 서비스 식별(권장)
  - (권장) `OTEL_SERVICE_NAME=dotnet-api`
- 5W1H 필드명은 **고정**
  - `Who`, `Where`, `What`, `Why`, `How`

## 데이터 흐름(요청 1건 기준) – 단계별

```text
[프로세스 시작]
    |
    +--> AddOpenTelemetry().UseAzureMonitor()
    |      - OTel SDK + Azure Monitor Exporter 구성
    |      - ASP.NET Core 요청/의존성 자동 계측 활성화
    |
    v
[HTTP 요청 -> ASP.NET Core]
    |
    +--> (자동) 요청 Activity/Span 생성 (Request)
    |
    +--> (수동) app.Use(...) 미들웨어:
    |          Activity.Current에 5W1H tag 주입
    |
    +--> (수동) 라우트에서 신호 생성
               - ILogger 로그(추가 설정 시 AppTraces)
               - ActivitySource.StartActivity(...) (커스텀 Activity)
               - HttpClient 호출(자동 Dependency)
               - throw Exception(...) (예외)
    |
    v
[OTel SDK 배치] -> [Azure Monitor Exporter 전송] -> [Application Insights -> LAW]
```

## 5W1H 주입 위치(코드 기준)

- `app.Use(async (context, next) => { ... Activity.Current.AddTag(...) ... })`
  - 요청 처리 중 활성화된 `Activity.Current`에 tag를 추가합니다.
  - Azure 쪽에서는 보통 `AppRequests.Properties["Who"]` 같은 형태로 조회합니다.

## .NET 스택 특징(운영 관점)

### 1) `Activity`가 “표준”이라 자동 계측/상관관계가 강함

- .NET은 `System.Diagnostics.Activity`가 런타임 표준(사실상 W3C Trace Context의 구현체)이라,
  프레임워크/라이브러리들이 `Activity.Current` 기반으로 자동 계측을 잘 붙입니다.
- 이 구조 덕분에 “요청 → 의존성(HttpClient) → 예외” 같은 상관관계가 비교적 안정적으로 잡힙니다.

### 2) 태그(Tag)는 “검색/필터 키”가 되므로 값 설계가 중요

- 이 샘플은 5W1H를 tag로 넣는데, 운영에서도 충분히 유용합니다.
- 운영 팁
  - `Who/Where/What/Why/How`는 팀 전체에서 **고정 필드명**으로 쓰면 KQL 재사용성이 좋아집니다.
  - UUID/랜덤 값 같은 고카디널리티 tag는 비용/성능을 악화시키기 쉬우니 주의하세요.

### 3) 도메인 이벤트(커스텀 span)는 `ActivitySource`가 정석

- .NET에서 “비즈니스 이벤트를 트레이스로 남기기”는 `ActivitySource`가 가장 자연스럽습니다.
- 단, **`AddSource("...")`로 수집 대상을 등록**해야 export됩니다(아래 섹션 참고).

## 엔드포인트 → 생성 신호 매트릭스

| Endpoint | 자동 생성(주요) | 수동 생성(주요) | 5W1H 주입 | 주로 확인할 테이블 |
|---|---|---|---|---|
| `GET /` | 요청 Trace | - | 요청 Activity tag | `AppRequests` |
| `GET /health` | 요청 Trace | - | 요청 Activity tag | `AppRequests` |
| `GET /logs` | 요청 Trace | `ILogger` 로그 | 요청 Activity tag | `AppRequests` (+ 로그는 설정에 따라 `AppTraces`) |
| `GET /custom-event` | 요청 Trace | `ActivitySource` 커스텀 Activity | 요청 Activity tag | `AppRequests` (+ 커스텀 Activity는 설정 필요) |
| `GET /dependency` | 요청 Trace + 의존성 | `HttpClient` 호출 | 요청 Activity tag | `AppDependencies` |
| `GET /error` | 요청 Trace + 예외 | - | 요청 Activity tag | `AppExceptions` |

## KQL로 확인하기

### (1) 최근 요청 + 5W1H 확인

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where tostring(Properties["Where"]) startswith "dotnet-api:"
      or AppRoleName == "dotnet-api"
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

### (3) 최근 의존성 확인 (`/dependency`)

```kusto
AppDependencies
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, Name, Target, DurationMs, Success
| take 50
```

### (4) (선택) 로그 확인 (`/logs`)

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, SeverityLevel, Message
| take 50
```

## “커스텀 Activity가 안 보이는” 흔한 이유(중요)

이 코드의 `ActivitySource("DotNetOTelSample")`로 만든 Activity는 **TracerProvider에 Source 등록이 없으면** `StartActivity(...)`가 `null`을 반환하고, 결과적으로 Azure로 export되지 않을 수 있습니다.

문서 예시(코드 변경은 하지 않음):

```csharp
// (예시) TracerProvider가 이 Source를 수집하도록 등록
builder.Services.AddOpenTelemetry()
  .WithTracing(tracing => tracing.AddSource("DotNetOTelSample"))
  .UseAzureMonitor();
```

## 로그(ILogger) 관련

`ILogger` 로그가 `AppTraces`로 들어오는지는 “OTel Logging 파이프라인 구성 여부”에 따라 달라질 수 있습니다.  
이 샘플은 **Trace 중심 흐름 설명**을 목표로 합니다(로그는 보조).

운영에서 “로그도 반드시 보내기”가 목표라면 보통 아래 중 하나를 선택합니다(코드 변경은 이 샘플 범위 밖).

- OpenTelemetry Logging 파이프라인을 켜고 Azure Monitor 로그 exporter를 추가
- 또는 별도의 로깅 전략(예: 구조화 로그 + 수집 에이전트)로 `AppTraces`/`CustomLogs`에 적재

## 실행

```bash
cd samples/csharp

export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=...;"
export OTEL_SERVICE_NAME="dotnet-api"

dotnet restore
dotnet run
```

## 빠른 검증 순서(권장)

```bash
curl -s http://localhost:5000/health
curl -s http://localhost:5000/logs
curl -s http://localhost:5000/custom-event
curl -s http://localhost:5000/dependency
curl -s http://localhost:5000/error
```

> 포트는 실행 환경에 따라 다를 수 있으니, `dotnet run` 출력의 listening URL을 기준으로 호출하세요.

## 트러블슈팅

- **요청/예외가 안 보임**
  - `APPLICATIONINSIGHTS_CONNECTION_STRING` 확인
  - 서버 아웃바운드 443 허용 여부 확인
  - Azure Logs 시간 범위 확장(예: 24시간)
- **5W1H가 비어 있음**
  - `AppRequests`에서 `Properties`를 `take 5`로 먼저 확인(키/중첩 구조 확인)
  - 이 샘플은 요청 미들웨어에서만 tag를 넣으므로, 의존성(`AppDependencies`)에 그대로 안 보일 수 있음
- **`/custom-event`가 안 보임**
  - `ActivitySource`가 TracerProvider에 등록되어 있는지(리스너 유무) 확인
