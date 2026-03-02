# 보존 및 내보내기 전략

## 목적
검색 성능과 장기 보관 요구를 동시에 만족하는 저장 전략을 정리합니다.

---

## 핵심 원리: 속도 vs 비용 트레이드오프

Azure 모니터링 인프라는 목적에 따라 3단계로 계층화됩니다.

| 계층 | 저장소 | 조회 속도 | 비용 | 용도 |
|---|---|---|---|---|
| **Live (실시간)** | App Insights Live Metrics | 1~2초 | 가장 높음 | 장애 즉시 감지, 빨간불 확인 |
| **Hot (단기 분석)** | Log Analytics Workspace (KQL) | 1~3분 | 중간 | 사후 원인 분석, 5W1H 진단 |
| **Cold (장기 보관)** | Azure Blob Storage | 15분~1시간 딜레이 | 매우 낮음 ($0.02/GB/월) | 감사 보존, 법적 증거, AI 학습 |

---

## 권장 전략 상세

### 전략 A. 일반 운영 데이터 (AppRequests, AppTraces, AppExceptions)
- **LAW 보존:** 기본 31일 (무료)
- **Blob 내보내기:** 선택 (불필요하면 하지 않아도 됨)
- **샘플링:** 정상 요청 10~20%만 수집

### 전략 B. 보안 감사 데이터 (Audit Logs)
- **별도 커스텀 테이블 분리:** `AuditLogs_CL` 테이블 생성 (ARM API 또는 Azure Portal)
- **LAW 보존:** 60일 ~ 90일 (분석 기간)
- **Blob 내보내기:** 반드시 활성화 → 장기 보관본 유지
- **WORM 정책:** 불변 저장소로 위변조 방지 적용 권장
- **샘플링:** 100% (법적 요구)

### 전략 C. 무한 보관 (사고 조사, 규정 준수)
```
LAW(30~60일) → Data Export Rule → Blob Storage Archive Tier (무제한)
```
- Blob에 떨어지는 파일 구조 (자동 생성):
```
am-AuditLogs_CL/
  y=2026/m=03/d=01/h=13/m=00/
    PT1H.json       ← 1시간치 덩어리
    PT1H_1.json     ← 용량 초과 시 자동 분할
```

---

## 무한 보관 복원 절차 (사고 발생 시)

3년 뒤 감사가 들어왔을 때:
1. Blob에서 해당 기간 `PT1H.json` 파일을 LAW로 **Restore** 요청
2. LAW에서 익숙한 KQL로 분석
3. 분석 완료 후 Restore된 임시 데이터 삭제 (비용 최소화)

---

## RBAC 권한 요구사항

Log Doctor처럼 외부 플랫폼이 고객 환경을 자동화할 때 필요한 권한:

| 작업 | 필요 권한 | 범위(Scope) |
|---|---|---|
| 커스텀 테이블 생성 / 보존 기간 변경 | `Log Analytics Contributor` | LAW 리소스 단위 |
| Data Export Rule 설정 | `Monitoring Contributor` | 리소스 그룹 단위 |
| Blob Storage 생성 / 데이터 쓰기 | `Storage Account Contributor` | 스토리지 계정 단위 |
| KQL 조회만 (읽기 전용) | `Log Analytics Reader` | LAW 리소스 단위 |

> ⚠️ "구독 전체 기여자(Subscription Contributor)"는 절대 요구하지 않습니다.  
> 최소 권한 원칙(Principle of Least Privilege)에 맞게 **LAW 리소스 단위로 스코프를 좁혀** 권한을 요청해야 기업 고객의 보안 심사를 통과할 수 있습니다.

---

## 체크리스트

- [ ] 데이터 분류 기준이 정의됐는가? (일반 / 민감 / 감사)
- [ ] 보존 기간과 삭제 정책이 산업 규정(금융: 5년, 의료: 10년 등)과 일치하는가?
- [ ] 감사 로그 Data Export Rule이 활성화됐는가?
- [ ] Blob Export 실패 시 알람이 있는가?
- [ ] WORM(불변 저장소) 정책이 감사 로그에 적용됐는가?
- [ ] 재복원(Restore) 절차가 문서화됐는가?
