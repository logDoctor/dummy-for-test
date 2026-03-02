# Observability 3요소 정리

## 목적
Trace, Metric, Log를 각각 언제 쓰는지 결정 기준을 제공합니다.

---

## 각 신호의 역할과 사용 시점

### 📍 Trace — "어디서 느려졌나?"

요청 1건이 여러 서비스를 통과하는 전체 경로를 기록합니다.  
각각의 서비스/구간을 **Span**이라는 단위로 기록하고, 모든 Span이 **Trace ID**로 연결됩니다.

```
[요청 진입] ──→ [인증 Span: 50ms] ──→ [비즈니스 로직 Span: 2000ms ❌] ──→ [DB Span: 5ms]
```
→ 이 수치를 보면 "비즈니스 로직에서 병목 발생"을 즉시 파악합니다.

**LAW 테이블:** `AppRequests` (서버 Span), `AppDependencies` (외부 호출/DB Span)

**확인 쿼리:**
```kusto
AppDependencies
| where DurationMs > 1000  // 1초 이상 걸린 외부 호출
| project TimeGenerated, Name, DurationMs, Target
| order by DurationMs desc
```

---

### 📊 Metric — "지금 시스템 상태가 어떤가?"

숫자 집계값(카운터, 히스토그램)으로 시스템 전반의 건강 상태를 빠르게 확인합니다.  
알람(Alert Rule)의 기준값으로 가장 많이 사용됩니다.

| 메트릭 | 설명 | 경보 기준 예시 |
|---|---|---|
| RPS (Requests Per Second) | 초당 요청 수 | 평소 대비 3배 이상 증가 시 |
| Error Rate | 전체 요청 중 실패 비율 | 5% 초과 시 |
| p95 Latency | 상위 5% 느린 요청의 응답 시간 | 2초 초과 시 |
| CPU / Memory | 서버 자원 사용률 | 80% 초과 시 |

**LAW에서 오류율 확인:**
```kusto
AppRequests
| summarize
    total  = count(),
    failed = countif(Success == false)
    by bin(TimeGenerated, 5m)
| extend error_rate = round(todouble(failed) / iif(total == 0, 1, total) * 100, 2)
| order by TimeGenerated desc
```

---

### 📝 Log — "정확히 어떤 데이터와 함께 실패했나?"

특정 이벤트의 상세 정보를 메시지와 구조화 필드로 기록합니다.  
Trace와 Metric이 "이상 징후"를 발견하고 나면, Log로 구체적인 원인 데이터를 확인합니다.

```python
logger.error(
    "Payment failed",
    extra={
        "custom_dimensions": {
            "order_id": "order-9999",
            "user_id": user_id,
            "error_code": "PAYMENT_503",
            "gateway": "KakaoPay"
        }
    }
)
```

---

## 세 가지를 함께 쓰는 방법 (실무 시나리오)

```
1. 📊 Metric 경보 발동
   → "오후 3시부터 오류율이 8%로 급증했습니다!" 알람

2. 📍 Trace로 병목 구간 식별
   → 오후 3시 이후 요청 Trace를 보니 "KakaoPay 외부 결제 Span"이 5초씩 걸림

3. 📝 Log로 정확한 원인 확인
   → AppTraces에서 "PAYMENT_503: KakaoPay 게이트웨이 타임아웃" 에러 메시지 발견

→ 원인: KakaoPay 외부 장애 → 담당팀 즉시 연락 및 백업 게이트웨이 전환
```

---

## 권장 도입 우선순위

| 단계 | 추가 신호 | 이유 |
|---|---|---|
| **운영 초반** | Metric + 기본 로그 | 빠르게 이상 감지 + 원인 파악 |
| **트래픽 증가** | Trace 상관관계 강화 | 서비스 간 병목 구간 파악 |
| **보안 요구 증가** | 감사 로그 스키마 고도화 | 법적/컴플라이언스 요구 대응 |
