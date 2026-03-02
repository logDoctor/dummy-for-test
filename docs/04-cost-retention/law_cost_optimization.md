# LAW 비용 최적화 가이드

## 목적
로그 품질을 유지하면서 LAW(Log Analytics Workspace)의 월 비용을 줄이는 핵심 전략입니다.

---

## Azure LAW 과금 구조 이해

| 과금 항목 | 설명 | 요금 기준 |
|---|---|---|
| **Data Ingestion** | 데이터가 LAW로 들어올 때 | ~$2.30/GB (종량제 기준) |
| **Data Retention** | 기본 31일 무료, 이후 장기 보관 | ~$0.10/GB/월 (32일~) |
| **Data Archive** | 비대화형 장기 보관 (최대 12년) | ~$0.02/GB/월 |

**핵심:** 비용의 90%는 **Ingestion(수집)**에서 발생합니다. 수집 단계를 줄이는 것이 가장 효과적입니다.

---

## 전략 1: 수집 단계 필터링 (가장 효과적)

### 404 스팸 필터
아무도 없는 경로에 봇이 계속 요청을 보내면 404 로그가 쌓여 불필요한 GB 요금이 나옵니다.  
`fastapi_app.py`의 `DropUnknownRouteProcessor`가 이를 처리합니다:

```python
class DropUnknownRouteProcessor(SpanProcessor):
    def on_end(self, span: trace.Span) -> None:
        if span.attributes and span.attributes.get("http.response.status_code") == 404:
            # Azure로 전송하지 않고 그 자리에서 Span 파기
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)
```

### 헬스체크 필터
쿠버네티스/로드밸런서가 `/health`를 초당 수십 번 찌르면 대용량 불필요 로그가 발생합니다.

```python
class DropHealthCheckProcessor(SpanProcessor):
    def on_end(self, span: trace.Span) -> None:
        path = span.attributes.get("http.target", "")
        if path in ("/health", "/api/health", "/ping"):
            span._context = span.context._replace(trace_flags=trace.TraceFlags.DEFAULT)
```

### DEBUG 로그 운영 OFF
```python
# 운영 환경에서는 WARNING 이상만 수집
logger.setLevel(logging.WARNING)  # INFO/DEBUG는 Azure로 안 보냄
```

---

## 전략 2: 샘플링 (Sampling)

트래픽이 많은 서비스에서 **모든 요청 Trace를 기록하는 것은 비효율**입니다.  
예를 들어 초당 1,000건의 정상 요청 중 10%만 기록해도 운영에 충분합니다.

```python
configure_azure_monitor(
    connection_string=connection_string,
    sampling_ratio=0.1  # 10%만 수집 → 비용 90% 절감
)
```

**샘플링 전략 예시:**

| 로그 유형 | 권장 샘플링 비율 |
|---|---|
| 정상 요청(2xx) | 10% ~ 20% |
| 오류(4xx/5xx) | **100%** (절대 놓치지 않도록) |
| 보안 감사(Audit) | **100%** (법적 요구) |
| 헬스체크 | 0% (완전 제외) |

---

## 전략 3: 보관 단계 분리 (Cold/Hot 분리)

자주 조회하는 데이터만 비싼 LAW에 보관하고, 장기 보관 데이터는 Blob으로 이동합니다.

```
LAW (비싼 냉장고, 빠른 KQL 검색)
├── 31일 기본 무료 보관
├── 자주 쓰는 운영 데이터 (AppRequests, AppExceptions)
└── ↓ Export 파이프라인 (Data Export Rule)

Blob Storage (싼 창고, GB당 $0.02/월)
├── 감사 로그 (1~7년 보관)
├── 규정 준수 데이터 (WORM 정책 적용 가능)
└── 사고 조사 시 LAW로 재복원해서 KQL 분석
```

---

## 전략 4: 테이블/필드 설계 최적화

- **동일한 의미의 필드 중복 제거:** `userId`, `user_id`, `UserId`를 하나로 통일
- **필수 필드만 Custom Dimensions에 추가:** 모든 로그에 불필요한 payload 전체를 넣지 않기
- **고카디널리티 필드 주의:** 랜덤 문자열처럼 값이 무한한 필드는 인덱싱 비용 급증

---

## 운영 체크리스트

- [ ] 월별 ingestion 상위 테이블 3개 파악 (Usage 쿼리 활용)
- [ ] 404/헬스체크 SpanProcessor 필터 적용 여부 확인
- [ ] 샘플링 비율이 환경별로 설정됐는지 확인
- [ ] 보안/감사 로그를 Blob으로 내보내는 Data Export Rule 활성화 여부
- [ ] 보존 기간이 실제 법적 요구(산업별)와 일치하는지 검토
