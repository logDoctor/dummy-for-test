# OpenTelemetry 아키텍처 요약

## 목적
OTel의 구성요소와 데이터 흐름을 운영자 관점에서 빠르게 이해합니다.

---

## 구성요소

```
┌─────────────────────────────────────────────────────────────┐
│                    애플리케이션 (Python 등)                   │
│                                                             │
│  ┌──────────────┐   ┌────────────────────────────────────┐  │
│  │  OTel API    │   │       Instrumentation              │  │
│  │  (사용자코드) │   │  FastAPIInstrumentor, httpx 등     │  │
│  └──────┬───────┘   └───────────────┬────────────────────┘  │
│         │                           │                       │
│  ┌──────▼───────────────────────────▼────────────────────┐  │
│  │                    OTel SDK                           │  │
│  │   TracerProvider / LoggerProvider / MeterProvider     │  │
│  │   + SpanProcessor (DropUnknownRouteProcessor 등)     │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                             │                               │
│  ┌──────────────────────────▼────────────────────────────┐  │
│  │                  Exporter                             │  │
│  │      Azure Monitor Exporter (배치 전송, 15초/건)      │  │
│  └──────────────────────────┬────────────────────────────┘  │
└─────────────────────────────│───────────────────────────────┘
                              │ HTTPS (443)
                              ▼
                   Azure Monitor Endpoint
                   (Application Insights)
                              │
                    ┌─────────▼─────────┐
                    │  Log Analytics    │
                    │   Workspace (LAW) │
                    └─────────┬─────────┘
                              │ KQL
                    ┌─────────▼─────────┐
                    │   개발자 / 운영팀  │
                    └───────────────────┘
```

---

## 3대 신호 (Three Pillars of Observability)

| 신호 | 핵심 질문 | LAW 테이블 | 예시 |
|---|---|---|---|
| **Trace (추적)** | "어디서 느려졌나?" | `AppRequests`, `AppDependencies` | 결제 요청 전체 경로 분석 |
| **Metric (지표)** | "지금 시스템 상태가 어떤가?" | `AppMetrics` | RPS, 오류율, p95 지연 |
| **Log (로그)** | "정확히 어떤 데이터와 함께 실패했나?" | `AppTraces`, `AppExceptions` | 결제 실패 원인, 감사 기록 |

---

## 데이터 흐름 (단계별)

1. HTTP 요청 진입 → `FastAPIInstrumentor`가 Span 자동 시작
2. 미들웨어에서 5W1H 속성 주입 (`Who`, `Where`, `How`, ...)
3. 비즈니스 로직에서 수동 Span / Log 추가 (`tracer.start_as_current_span`)
4. SpanProcessor가 불필요한 Span 필터링 (`DropUnknownRouteProcessor`)
5. Exporter가 15초 or 500건 단위 배치로 Azure로 전송
6. Azure가 신호 유형별로 분류하여 LAW 테이블에 저장
7. 개발자/운영팀이 KQL로 검색 및 대시보드 활용

---

## 자동 계측 vs 수동 계측

| 구분 | 방법 | 생성 신호 |
|---|---|---|
| **자동 계측** | `FastAPIInstrumentor.instrument_app(app)` | 모든 요청 Trace, 예외 캡처 (코드 추가 불필요) |
| **수동 계측** | `tracer.start_as_current_span("MyEvent")` | 커스텀 비즈니스 이벤트, 감사 Span |
| **로그 계측** | `logger.info("...", extra={"custom_dimensions": {...}})` | AppTraces에 구조화 데이터 포함 |

---

## 실무 포인트

- 자동 계측으로 기본 신호를 확보하고, 운영 가치가 높은 이벤트만 수동 계측 추가
- Trace Context 전파(`traceparent` Header)가 서비스 간 연결의 핵심
- 샘플링 정책과 보관 정책은 독립적으로 설계 (수집량 ≠ 보관량)
- `SpanProcessor`는 Azure로 전송 전 마지막 관문 (필터/변환/보강 가능)
