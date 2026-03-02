# Azure 모니터링 지연/저장 Q&A

## Q1. 로그는 실시간으로 바로 보이나요?

**A. 계층마다 다릅니다.**

| 계층 | 반영 속도 | 접근 방법 |
|---|---|---|
| Live Metrics | **1~2초** | Application Insights → Live Metrics |
| LAW KQL 검색 | **1~3분** | LAW → Logs → KQL 실행 |
| Blob Export | **15분~1시간** | Storage Account → Blob Container |

실시간 장애 대응은 Live Metrics를, 원인 분석은 KQL을, 장기 감사는 Blob을 씁니다.

---

## Q2. Blob으로 내보내기를 설정하면 로그가 생길 때마다 기존 파일을 덮어쓰나요?

**A. 아닙니다. 시간 파티션 기반으로 새 파일을 계속 생성합니다.**

Azure가 자동으로 생성하는 폴더 구조:
```
am-AuditLogs_CL/
  y=2026/m=03/d=01/h=15/m=00/
    PT1H.json     ← 해당 시간대 데이터 (Append Only)
    PT1H_1.json   ← 용량 초과 시 자동 분할
```
- 기존 파일은 절대 수정되지 않습니다
- 이 특성이 WORM(위변조 방지) 정책과 결합되어 법적 감사 증거로 사용됩니다

---

## Q3. 앱에서 로그를 1초에 1,000개 찍으면 1,000번 네트워크 통신이 발생하나요?

**A. 아닙니다. SDK 내부 배치(Batch) 전송으로 성능 영향을 최소화합니다.**

```
[앱 내부]
로그 발생 → SDK 내부 버퍼에 모아두기
→ 15초 or 500개 초과 시 → 한 번의 HTTP POST로 묶어서 Azure로 전송

[Azure 수신]
→ LAW에 인덱싱 (1~3분 후 KQL 검색 가능)
→ Data Export Rule이 켜져 있으면 → 1시간 단위로 Blob에 덤프
```

---

## Q4. LAW와 Blob은 구체적으로 어떻게 다른가요?

| 항목 | LAW (Log Analytics Workspace) | Blob Storage |
|---|---|---|
| **비용** | ~$2.30/GB (ingestion) | ~$0.02/GB/월 |
| **검색 속도** | KQL로 수초 내 결과 | 직접 검색 불가 (파일 다운로드 후 분석) |
| **최대 보관** | 기본 31일 (최대 12년, 비쌈) | 무제한 |
| **주 용도** | 실시간 운영 분석 | 장기 감사 보관, 아카이브 |
| **조회 방법** | KQL 쿼리 | 파일 다운로드 or LAW Restore |

---

## Q5. LAW에서 Blob으로 1시간씩 기다리는 동안 추가 요금이 드나요?

**A. 아닙니다. 이미 수집(Ingestion) 시점에 요금을 냈고, 31일 안에 있으면 보관 비용은 무료입니다.**

- **Ingestion 요금:** 데이터가 LAW 문턱을 넘을 때 GB당 한 번만 냄
- **Retention 요금:** 기본 31일은 무료 → 1시간 대기는 이 안에 포함
- **Export 처리 비용:** Data Export 기능 자체는 약 $0.10/GB (매우 저렴, Ingestion의 1/23)

---

## Q6. "기여자(Contributor)" 권한이 너무 높지 않나요?

**A. 맞습니다. "구독 전체 기여자"는 절대 요청하면 안 됩니다.**

핵심은 **범위(Scope) 제한**입니다:
- ❌ `구독(Subscription) 전체` → 모든 VM/DB 제어 가능 → 기업 고객 거절
- ✅ `LAW 리소스 단위` → 로그 설정만 제어 가능 → 보안 심사 통과

최고의 방법은 삭제 권한이 없는 **Custom Role JSON**을 고객에게 주며 직접 생성하게 하는 것입니다.
