# Java (Spring Boot + Java Agent) → Azure Monitor 데이터 흐름 (샘플 기준)

## 이 샘플이 보여주는 것(TL;DR)

- Java는 코드에 SDK를 심는 대신, **Application Insights Java Agent(권장 방식)** 로 요청/의존성/예외를 자동 계측합니다.
- 요청 단위 표준 필드(5W1H)는 **Servlet Filter에서 `MDC`로 주입**하고, 에이전트가 이를 Custom Dimensions로 수집합니다.
- Azure 쪽에서는 보통 `AppRequests`/`AppDependencies`/`AppTraces`/`AppExceptions`에서 확인합니다(워크스페이스 기반 Application Insights).

## 주요 파일

- `src/main/java/com/example/demo/DemoApplication.java`
  - `TelemetryFilter`: 요청 단위로 5W1H를 `MDC`에 세팅
  - `HelloController`: 로그/의존성/에러를 발생시키는 엔드포인트 제공
- `applicationinsights.json`
  - `role.name`(서비스 식별), 기본 custom dimensions 예시
- `pom.xml`: Spring Boot 빌드 설정

## 필수 설정 값

- `APPLICATIONINSIGHTS_CONNECTION_STRING`
  - 예: `InstrumentationKey=...;IngestionEndpoint=...;LiveEndpoint=...;`
- 서비스 식별(이 샘플은 `applicationinsights.json` 기준)
  - `role.name: "java-api"` (Azure에서 `AppRoleName`으로 조회하는 기준이 됩니다)
- 5W1H 필드명은 **고정**
  - `Who`, `Where`, `What`, `Why`, `How`

## 데이터 흐름(요청 1건 기준) – 단계별

```text
[JVM 시작]
    |
    +--> -javaagent:applicationinsights-agent-<ver>.jar
    |      - 자동 계측 활성화(요청/의존성/예외 등)
    |      - 로그 프레임워크(MDC)에서 Custom Dimensions 추출
    |
    v
[HTTP 요청 -> Spring Boot]
    |
    +--> (수동) TelemetryFilter:
    |          MDC에 5W1H + 공통 필드 세팅
    |
    +--> (자동) Java Agent:
    |          Request/Dependency/Exception 자동 수집
    |
    +--> (수동) 컨트롤러에서 SLF4J 로그 출력
    |          - Agent가 MDC 값을 함께 수집
    |
    v
[Java Agent 전송] -> [Application Insights -> LAW]
```

## 5W1H 주입 위치(코드 기준)

- `TelemetryFilter#doFilter(...)`
  - `MDC.put("Where", "java-api:" + path)` 형태로 넣습니다.
  - 요청이 끝나면 `MDC.clear()`로 정리합니다(요청 간 오염 방지).

## Java 스택 특징(운영 관점)

### 1) “에이전트 1개로 자동 계측”이 가장 큰 장점

- Java는 애플리케이션 코드에 SDK를 깊게 넣기보다, **JVM 시작 시 `-javaagent`만 추가**해서
  요청/의존성/예외 같은 핵심 신호를 빠르게 확보하는 전략이 현실적으로 가장 효율적인 경우가 많습니다.
- 팀/서비스가 많을수록 “코드 수정 없는 일괄 적용”이 운영 비용을 크게 낮춥니다.

### 2) `MDC`는 ThreadLocal이라 “서블릿”에선 강하지만, 비동기에서는 주의

- `MDC`는 보통 ThreadLocal 기반이라, Spring MVC(서블릿)처럼 요청이 한 스레드에서 처리되는 모델에서 안정적입니다.
- 비동기 처리(예: 별도 스레드/리액티브 체인)로 넘어가면 MDC가 자동으로 이어지지 않을 수 있어,
  그런 경우엔 별도의 컨텍스트 전파 전략이 필요합니다.
- 이 샘플은 요청 종료 시 `MDC.clear()`를 호출해 요청 간 오염을 방지합니다.

### 3) “로그를 표준화”하는 것이 Java에선 특히 큰 효과

- Java는 팀마다 로그 포맷/라이브러리가 갈리기 쉬운데, MDC에 5W1H를 고정 키로 넣으면
  KQL에서 “언어/서비스가 달라도 같은 쿼리”를 재사용하기 쉬워집니다.

### 4) 샘플링/비용은 `applicationinsights.json`에서 먼저 조절하는 편이 안전

- Java 서비스는 트래픽이 큰 경우가 많아서, 무제한 트레이스/로그 수집은 비용이 급증하기 쉽습니다.
- 운영에선 보통 “요청/의존성 자동 계측 + 샘플링(%)”으로 기본을 잡고,
  이슈 구간만 더 깊게(추가 attribute/로그) 파는 방식이 안정적입니다.

## 엔드포인트 → 생성 신호 매트릭스

| Endpoint | 자동 생성(주요) | 수동 생성(주요) | 5W1H 주입 | 주로 확인할 테이블 |
|---|---|---|---|---|
| `GET /` | 요청 Trace | `logger.info` | MDC(로그) + 요청 | `AppRequests`, `AppTraces` |
| `GET /health` | 요청 Trace | - | 요청 | `AppRequests` |
| `GET /logs` | 요청 Trace | INFO/WARN/ERROR 로그 | MDC | `AppTraces` |
| `GET /custom-event` | 요청 Trace | “이벤트성 로그” | MDC | `AppTraces` |
| `GET /dependency` | 요청 Trace + 의존성 | `RestTemplate` 호출 | MDC(요청) | `AppDependencies` |
| `GET /error` | 요청 Trace + 예외 | `logger.error` + 예외 throw | MDC(로그) | `AppExceptions`, `AppTraces` |

## `applicationinsights.json` 위치/읽힘(운영 팁)

- 에이전트는 `applicationinsights.json`을 통해 `role.name`, sampling, 기본 custom dimension 등을 설정합니다.
- 운영에서는 **에이전트 JAR과 함께 배포**하고, 실행 디렉터리에서 설정 파일을 찾을 수 있게 두는 방식이 가장 단순합니다.
  - (권장) `applicationinsights-agent-*.jar`와 `applicationinsights.json`을 같은 디렉터리에 두고 실행

## KQL로 확인하기

### (1) 최근 요청 + 5W1H 확인

```kusto
AppRequests
| where TimeGenerated > ago(30m)
| where AppRoleName == "java-api" or tostring(Properties["Where"]) startswith "java-api:"
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, Name, Url, ResultCode, DurationMs, Success,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          What = tostring(Properties["What"]),
          Why = tostring(Properties["Why"]),
          How = tostring(Properties["How"])
| take 20
```

### (2) 최근 로그 + MDC(= 5W1H) 확인

```kusto
AppTraces
| where TimeGenerated > ago(30m)
| where AppRoleName == "java-api"
| order by TimeGenerated desc
| project TimeGenerated, SeverityLevel, Message,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          What = tostring(Properties["What"]),
          Why = tostring(Properties["Why"]),
          How = tostring(Properties["How"])
| take 50
```

### (3) 최근 예외 확인 (`/error`)

```kusto
AppExceptions
| where TimeGenerated > ago(30m)
| order by TimeGenerated desc
| project TimeGenerated, AppRoleName, OuterMessage, ProblemId
| take 20
```

### (4) 최근 의존성 확인 (`/dependency`)

```kusto
AppDependencies
| where TimeGenerated > ago(30m)
| where AppRoleName == "java-api"
| order by TimeGenerated desc
| project TimeGenerated, Name, Target, DurationMs, Success
| take 50
```

## 실행(예시)

```bash
cd samples/java

export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=...;"

mvn -q clean package

# Agent JAR은 별도 다운로드 후 경로 지정
java -javaagent:/path/to/applicationinsights-agent-3.x.x.jar \
  -jar target/demo-0.0.1-SNAPSHOT.jar
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
  - `-javaagent:` 옵션이 실제로 붙어 실행되었는지 확인
  - 서버 아웃바운드 443 허용 여부 확인
  - Azure Logs 시간 범위 확장(예: 24시간)
- **MDC(5W1H)가 안 보임**
  - `TelemetryFilter`가 모든 요청 경로에 적용되는지 확인
  - `AppTraces | take 5`로 `Properties` 구조를 먼저 확인(키/중첩 구조 확인)
