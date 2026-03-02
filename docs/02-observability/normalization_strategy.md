# 멀티스택 로그 정규화 전략

## 목적
언어가 달라도 같은 방식으로 검색/대시보드/경보를 만들기 위한 규칙입니다.

---

## 1. 서비스 식별자 통일

모든 스택에서 `OTEL_SERVICE_NAME` 환경변수 또는 동등한 필드를 일관된 네이밍으로 설정합니다.

| 스택 | 설정 방법 | 권장 값 예시 |
|---|---|---|
| Python | `os.environ["OTEL_SERVICE_NAME"] = "python-api"` | `python-api` |
| Node.js | `OTEL_SERVICE_NAME=node-api` (환경변수) | `node-api` |
| .NET | `applicationinsights.json` → `role.name` | `dotnet-api` |
| Java | `applicationinsights.json` → `role.name` | `java-api` |
| Go | `otel.SetTracerProvider(...)` + `resource.WithAttributes` | `go-api` |

**KQL 서비스 필터 예시:**
```kusto
AppRequests
| where AppRoleName in ("python-api", "node-api", "java-api")
| summarize count() by AppRoleName, bin(TimeGenerated, 1h)
```

---

## 2. 공통 필드 계약 (팀 전체 필수 준수)

| 카테고리 | 필드명 | 타입 | 필수 여부 |
|---|---|---|---|
| **필수** | `timestamp` | datetime | ✅ |
| **필수** | `service` / `AppRoleName` | string | ✅ |
| **필수** | `environment` | string | ✅ |
| **필수** | `version` | string | ✅ |
| **필수** | `trace_id` | string | ✅ (자동) |
| **필수** | `severity` | string | ✅ |
| **권장** | `user_id` / `Who` | string | 권장 |
| **권장** | `operation` / `What` | string | 권장 |
| **권장** | `result` | string | 권장 |
| **권장** | `error_code` | string | 오류 시 |

---

## 3. 5W1H 확장 필드 가이드

분석 목적에만 추가하며, 표준 운영 필드와 혼용하지 않습니다.

```python
# Python 예시: 미들웨어에서 자동 주입
span.set_attribute("Who",   request.client.host)   # 누가
span.set_attribute("Where", f"python-api:{path}")  # 어디서
span.set_attribute("How",   request.method)        # 어떻게
# What / Why 는 비즈니스 이벤트에서 수동 추가
```

> 필드명은 **고정** (`Who`, `Where`, `How`, `What`, `Why`, `When`)으로 팀 전체가 동일하게 사용합니다.

---

## 4. 쿼리 표준화 (팀 공통 쿼리 템플릿)

아래 쿼리들을 LAW → "저장된 쿼리(Saved Queries)"로 등록해 팀 전체가 재사용합니다.

```kusto
// [공통-01] 최근 오류 전체 조회
AppTraces
| where SeverityLevel >= 3
| project TimeGenerated, AppRoleName, Message, SeverityLevel
| order by TimeGenerated desc

// [공통-02] 서비스별 평균 응답 시간
AppRequests
| summarize avg_ms = avg(DurationMs) by AppRoleName
| order by avg_ms desc

// [공통-03] 표준 5W1H 요청 로그
AppRequests
| project TimeGenerated,
          Who   = tostring(Properties["Who"]),
          Where = tostring(Properties["Where"]),
          How   = tostring(Properties["How"]),
          AppRoleName, ResultCode, DurationMs
| order by TimeGenerated desc
```

---

## 5. 운영 원칙

| 원칙 | 세부 내용 |
|---|---|
| **스키마 버전 관리** | 팀 간 필드명 변경은 PR로 문서화 후 배포 |
| **고카디널리티 필드 금지** | UUID, 랜덤 해시 등 무한 값 필드를 인덱스 필드로 넣지 않음 |
| **민감정보 마스킹** | 이름, 전화번호, 카드번호 → 마스킹 후 저장 (`홍*동` 형식) |
| **null/빈 값 처리** | 빈 문자열 대신 `"unknown"` 또는 해당 필드 제외 |

---

## 체크리스트

- [ ] 모든 스택의 `service.name` (AppRoleName)이 구분 가능한 이름으로 통일됐는가?
- [ ] 공통 필드 계약서가 팀 위키/문서에 공유됐는가?
- [ ] 공통 KQL 쿼리가 "저장된 쿼리"로 LAW에 등록됐는가?
- [ ] 고카디널리티 필드 남용 여부를 `Usage` 쿼리로 정기 점검하는가?
- [ ] 민감정보 처리 기준이 명확히 정의됐는가?
