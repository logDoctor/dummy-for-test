# 로그 표준화 도입 이유

## 목적
다중 언어 서비스(Python, .NET, Java, Node.js, Go)를 하나의 운영 관점으로 묶는 기준을 설명합니다.

---

## 문제: 표준화 없을 때 벌어지는 일

| 스택 | 사용자 ID 필드명 | 로그 형식 |
|---|---|---|
| Python | `user_id` | JSON (구조화) |
| .NET | `UserId` | 텍스트 덤프 |
| Java | `userId` | JSON |
| Node.js | `uid` | JSON |
| Go | `userID` | 텍스트 |

같은 개념인데 **필드명이 5개**나 됩니다.  
이 상태로 KQL 쿼리를 쓰면:
```kusto
// 서비스마다 조건이 달라져서 재사용 불가능
AppTraces
| where Properties["user_id"] == "123"   // Python
     or Properties["UserId"] == "123"    // .NET
     or Properties["uid"] == "123"       // Node.js
```

---

## 표준화 전략

### 1. 공통 필드 스키마 (모든 스택 공통)

| 필드 | 설명 | 예시 |
|---|---|---|
| `service` (= `Where`) | 서비스 이름 | `python-api`, `node-api` |
| `environment` | 배포 환경 | `production`, `staging` |
| `version` | 앱 버전 | `1.2.3` |
| `user_id` (= `Who`) | 요청자 식별자 | `user-1234` |
| `trace_id` | 요청 단위 식별자 | 자동 생성 (OTel) |
| `operation_name` | 작업 이름 | `payment.process`, `login` |

### 2. 5W1H 확장 필드 (분석용 커스텀)

| 필드 | 의미 |
|---|---|
| `Who` | 요청자 IP 또는 user_id |
| `What` | 수행한 작업명 |
| `When` | 자동 기록 (`TimeGenerated`) |
| `Where` | 서비스 + 경로 |
| `Why` | 오류 원인/비즈니스 이유 |
| `How` | HTTP 메서드 / 수단 |

> 5W1H는 표준 운영 필드와 별도로 `custom_dimensions`에 추가합니다.  
> 운영 표준 필드와 분석용 필드를 **혼용하지 않습니다.**

### 3. 중앙 수집 + 통합 쿼리

표준화된 필드를 쓰면 이 쿼리 하나로 모든 스택을 조회합니다:
```kusto
AppTraces
| where Properties["Where"] startswith "python-api"
      or Properties["Where"] startswith "node-api"
| where Properties["Who"] != ""
| project TimeGenerated, AppRoleName,
          Who = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          Message
| order by TimeGenerated desc
```

---

## 기대 효과

| 항목 | 표준화 전 | 표준화 후 |
|---|---|---|
| 장애 분석 시간 | 2~4시간 (서비스마다 다른 쿼리) | 15분 (단일 KQL) |
| 신규 서비스 온보딩 | 로그 패턴 새로 설계 | 공통 미들웨어/필터 붙이면 끝 |
| 감사 대응 | 서비스별 따로 수집 | 통합 Audit 테이블 한 번에 조회 |

---

## 적용 우선순위

1. **필드명 통일** (가장 먼저, 팀 전체 동의 필요)
2. **Trace Context 전파** (서비스 간 Trace ID 연결)
3. **고비용 로그 통제** (샘플링, DEBUG OFF, 필터)
