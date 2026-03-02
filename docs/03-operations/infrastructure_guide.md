# 인프라 구성 가이드

## 목적
Azure 기반 관측 환경을 처음 구성할 때 필요한 리소스, 역할, 배포 순서를 정리합니다.

---

## 핵심 Azure 리소스

| 리소스 | 역할 | 비고 |
|---|---|---|
| **Virtual Machine (VM)** | 애플리케이션 실행 환경 | 또는 Container App, App Service |
| **Application Insights** | APM / 모니터링 시각화 대시보드 | LAW와 연결 필수 |
| **Log Analytics Workspace (LAW)** | 로그 저장 + KQL 검색 엔진 | 모든 텔레메트리의 중앙 창고 |
| **Storage Account (Blob)** | 장기 아카이브 저장소 | 선택 사항 (감사 로그 장기 보관 시 필요) |

---

## 권장 아키텍처 (데이터 흐름)

```
[앱 서버 (Python / Node.js / Java / Go)]
    │ OTel SDK → Batch 전송 (15초 or 500건)
    ↓
[Azure Monitor Endpoint]
    │ 자동 분류
    ├── AppRequests      ← HTTP 요청/응답
    ├── AppExceptions    ← 예외/오류
    ├── AppTraces        ← 로그 메시지
    └── AppDependencies  ← 외부 호출/DB 쿼리
    ↓
[Log Analytics Workspace (LAW)]
    │ KQL로 빠른 분석 (1~3분 딜레이)
    │ 기본 31일 무료 보관
    ↓ (Data Export Rule 켜면 자동)
[Azure Blob Storage - Archive Tier]
    └── 무제한 장기 보관 ($0.02/GB/월)
```

---

## 배포 순서 (deploy_az_vm.sh 참고)

1. **리소스 그룹 생성**
   ```bash
   az group create --name rg-logdoctor-test --location koreacentral
   ```

2. **Log Analytics Workspace 생성**
   ```bash
   az monitor log-analytics workspace create \
     --resource-group rg-logdoctor-test \
     --workspace-name law-logdoctor-test
   ```

3. **Application Insights 생성 (LAW 연결)**
   ```bash
   az monitor app-insights component create \
     --app ai-logdoctor-test \
     --resource-group rg-logdoctor-test \
     --workspace law-logdoctor-test
   ```

4. **Connection String 환경변수 세팅**
   ```bash
   export APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=...;IngestionEndpoint=..."
   ```

5. **애플리케이션 실행**
   ```bash
   python fastapi_app.py
   ```

---

## 보안/권한 설계

| 원칙 | 적용 방법 |
|---|---|
| **최소 권한** | 실행 리소스에는 Managed Identity 사용 (Key 대신) |
| **역할 분리** | 운영자는 `Log Analytics Contributor`, 읽기는 `Reader` |
| **Connection String 보호** | 코드에 하드코딩 금지 → 환경변수 or Key Vault |
| **네트워크 격리** | LAW Ingestion 엔드포인트(443)만 아웃바운드 허용 |

---

## 운영 체크리스트

- [ ] 서비스별 `OTEL_SERVICE_NAME`이 구분 가능하게 설정됐는가?
- [ ] `APPLICATIONINSIGHTS_CONNECTION_STRING`이 환경변수로 주입됐는가?
- [ ] 표준 필드(환경/버전/사용자/트레이스)가 미들웨어에서 자동 주입되는가?
- [ ] 장애 대응용 대시보드 / 경보 규칙(Alert Rule)이 설정됐는가?
- [ ] 방화벽 아웃바운드 443 포트가 Azure Monitor 엔드포인트로 열려있는가?
