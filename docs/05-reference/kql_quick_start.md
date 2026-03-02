# KQL 퀵 스타트

## 목적
LAW에서 자주 쓰는 기본 쿼리를 빠르게 실행하기 위한 레퍼런스입니다.

---

## 시작
1. Azure Portal → Log Analytics Workspace → **Logs**
2. 시간 범위를 **최근 30분** 또는 **24시간**으로 설정
3. 아래 쿼리 복붙 후 **Run** 클릭

---

## 기본 조회

### 최근 요청 목록
```kusto
AppRequests
| order by TimeGenerated desc
| project TimeGenerated, Name, Url, ResultCode, DurationMs, Success
| take 20
```

### 최근 예외 목록
```kusto
AppExceptions
| order by TimeGenerated desc
| project TimeGenerated, ProblemId, OuterMessage, AppRoleName
| take 20
```

### 최근 트레이스 로그
```kusto
AppTraces
| order by TimeGenerated desc
| project TimeGenerated, Message, SeverityLevel, AppRoleName
| take 50
```

---

## 성능 분석

### 오류율 (5분 단위)
```kusto
AppRequests
| summarize
    total  = count(),
    failed = countif(Success == false)
    by bin(TimeGenerated, 5m)
| extend error_rate = round(todouble(failed) / iif(total == 0, 1, total) * 100, 2)
| order by TimeGenerated desc
```

### 서비스별 응답 시간 (p50 / p95)
```kusto
AppRequests
| summarize
    p50 = percentile(DurationMs, 50),
    p95 = percentile(DurationMs, 95)
    by AppRoleName
| order by p95 desc
```

### 엔드포인트별 호출 수 및 평균 응답 시간
```kusto
AppRequests
| summarize
    call_count = count(),
    avg_ms     = round(avg(DurationMs), 1)
    by Name
| order by call_count desc
```

---

## Custom Properties 조회

### 5W1H 컨텍스트 포함 요청 조회
```kusto
AppRequests
| where isnotempty(Properties["Who"])
| project TimeGenerated, Name,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          How = tostring(Properties["How"]),
          Environment = tostring(Properties["Environment"])
| order by TimeGenerated desc
| take 20
```

### 보안 감사 로그 (AppTraces 기준)
```kusto
AppTraces
| where Message contains "Audit success"
| project TimeGenerated, Message,
          Action = tostring(Properties["custom_dimensions"]["Audit_Action"]),
          UserId = tostring(Properties["custom_dimensions"]["Actor_User_ID"]),
          DocId  = tostring(Properties["custom_dimensions"]["Target_Document_ID"])
| order by TimeGenerated desc
```

### 보안 감사 Span (소요 시간 포함)
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

## 비용 파악 쿼리

### 테이블별 하루 ingestion 용량 (최근 7일 평균)
```kusto
Usage
| where TimeGenerated > ago(7d)
| summarize avg_gb = round(sum(Quantity) / 1024 / 7, 3) by DataType
| order by avg_gb desc
```

---

## KQL 팁

| 팁 | 설명 |
|---|---|
| 시간 범위 먼저 줄이기 | `where TimeGenerated > ago(30m)` 습관화 |
| `project`로 컬럼 제한 | 필요한 컬럼만 선택해서 응답 속도 개선 |
| `take N` 으로 샘플 확인 | 전체 스캔 전 데이터 구조 파악 |
| 공통 쿼리 저장 | "Save" → 팀 공유 쿼리팩으로 저장해 재사용 |
| `tostring(Properties["key"])` | `Properties` 컬럼은 dynamic 타입 → 반드시 형변환 |
