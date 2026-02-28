# 프레임워크별 OpenTelemetry 데이터 추출 요약

현재 각 언어 및 프레임워크의 샘플 코드에 구현된 OpenTelemetry(또는 Application Insights SDK/Agent)를 통해 추출할 수 있는 주요 데이터 요소들을 정리한 문서입니다.

모든 스택에서 공통적으로 **5W1H (Who, Where, How 등)** 맥락 정보와 **표준 필드 (AppVersion, Environment 등)**를 로깅 및 텔레메트리에 포함하도록 구성되어 있습니다.

---

## 1. Python (FastAPI)
**방식:** `azure.monitor.opentelemetry` (Azure Monitor OpenTelemetry Distro)

*   **자동 계측 (Auto-instrumentation):**
    *   **HTTP 요청 (Requests):** FastAPI 라우터 및 미들웨어를 통과하는 인바운드 HTTP 요청 자동 추적.
    *   **예외 (Exceptions):** 처리되지 않은 예외 자동 캡처.
    *   **외부 종속성 (Dependencies):** 외부 API 호출, DB 쿼리 등 자동 추적.
*   **사용자 정의 속성 (5W1H 주입):**
    *   **로그 필터 (Logging Filter):** 표준 `logging` 모듈에 필터를 적용하여 모든 로그에 `Environment`, `AppVersion`, `Where`, `user_Id`, `application_Version` 주입.
    *   **도메인 필드 자동 매핑:** `enduser.id` 속성을 통해 Application Insights의 `user_Id` 필드 등 매핑 가능.
    *   **미들웨어 (Middleware):** 인바운드 요청의 현재 Span(스팬)에 `Who`(Client IP/Host), `Where`, `How`(HTTP Method) 등을 속성으로 추가.
*   **사용자 정의 이벤트 (Custom Events):** `tracer.start_as_current_span()`을 사용하여 커스텀 Span 및 로그 기록.
*   **수동 종속성 추가:** Span 속성에 `db.system`, `db.statement` 등을 수동으로 설정해 외부 쿼리 추적 가능.

---

## 2. Node.js (Express)
**방식:** `@azure/monitor-opentelemetry` (Azure Monitor OpenTelemetry Distro)

*   **자동 계측 (Auto-instrumentation):**
    *   **HTTP 요청 & 예외:** Express 앱으로 들어오는 HTTP 요청 및 글로벌 에러 핸들러를 통한 예외 자동 추적.
*   **로그 (Traces):**
    *   `trace.getActiveSpan().addEvent()`를 활용하여 현재 Span에 로그 정보 및 중요도(`log.severity`)를 이벤트 형태로 기록.
*   **사용자 정의 이벤트 및 메트릭 (Custom Events & Metrics):**
    *   **이벤트:** Span의 Event로 비즈니스 로직(예: UserCheckout) 및 추가 속성 기록.
    *   **메트릭:** OpenTelemetry Meter(`meter.createCounter()`)를 통해 비즈니스 지표 누적.
*   **수동 종속성 추적:** `tracer.startActiveSpan()`을 열어 `http.url`, `http.method`, `http.status_code` 등의 속성을 직접 부여하여 종속성 이력 기록.

---

## 3. Go (Gin)
**방식:** `github.com/microsoft/ApplicationInsights-Go/appinsights` (Application Insights SDK)

*   **전역 표준 컨텍스트:** 클라이언트 레벨에서 `ai.cloud.role`, `ai.user.authUserId`, `ai.application.ver` 설정 적용.
*   **5W1H 및 요청 추적 (Gin 미들웨어):**
    *   Request 응답 시간(duration)과 상태 코드 수동 계산 후 `client.Track(request)` 전송.
    *   `Who`(Client IP), `Where`, `How`(HTTP Method)를 `RequestTelemetry.Properties`에 주입.
*   **로그 (Traces) & 예외 (Exceptions):**
    *   `client.TrackTrace()`를 사용하여 INFO, WARN, ERROR 로그 전송.
    *   `client.TrackException()`으로 에러를 전송하여 예외 텔레메트리 캡처.
*   **사용자 정의 이벤트 (Custom Events):** `client.TrackEvent()` (또는 `NewEventTelemetry`)를 사용하여 속성(Properties)과 수치(Metrics)를 함께 기록.
*   **종속성 (Dependencies):** `NewRemoteDependencyTelemetry` 개체를 생성하여 대상(SQL 등), 명령어(Query), 성공 여부 등을 수동/명시적으로 캡처.

---

## 4. .NET/C# (ASP.NET Core)
**방식:** `Azure.Monitor.OpenTelemetry.AspNetCore` (Azure Monitor OpenTelemetry Distro)

*   **자동 계측 (Auto-instrumentation):**
    *   **HTTP 요청, 예외:** 프레임워크 레벨에서 모든 요청과 에러 자동 추집.
    *   **로그:** .NET 표준 `ILogger` 확장을 통해 코드 변경 없이 INFO, WARN, ERROR 등이 Application Insights Traces로 자동 전송.
    *   **종속성:** `HttpClient` 등을 이용한 외부 통신이 Dependency로 자동 수집.
*   **사용자 정의 이벤트 (Custom Events):**
    *   OpenTelemetry 표준인 `ActivitySource`를 사용하여 `StartActivity`로 Span을 생성하고, 내부에 `ActivityEvent`(태그 포함)를 추가하여 커스텀 이벤트 추적.
*   **글로벌 에러 핸들링:** 미들웨어 파이프라인(`app.Use(...)`)에서 발생한 에러를 `ILogger`를 통해 기록함으로써 자연스럽게 수집.

---

## 5. Java (Spring Boot)
**방식:** Application Insights Java 3.x Agent (코드 수정 불필요, 에이전트 기반)

*   **자동 계측 (Auto-instrumentation):**
    *   **전 부문 자동화:** HTTP 맵핑 요청, 예외, 로깅 프레임워크(SLF4J, Logback 등), 외부 호출(`RestTemplate` 등)을 Java Agent가 자동으로 후킹하여 수집.
*   **5W1H 및 사용자 정의 속성 주입 (MDC 활용):**
    *   **Servlet Filter 및 MDC (Mapped Diagnostic Context):** Filter를 활용해 요청의 시작 지점에서 `MDC.put("Env", "Lab")`, `Who`, `AppVersion` 등을 주입.
    *   Java Agent는 SLF4J의 MDC 컨텍스트 값을 추출하여 Application Insights의 **Custom Dimensions**으로 자동 포함시킴.
*   **로그 기반 이벤트 등록:** 커스텀 이벤트 역시 `logger.info("Event_...")` 형태로 기록하면 Agent를 통해 별도 설정 없이 추적됨.
