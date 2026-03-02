# 배포/검증 워크스루

## 목적
샘플 시스템을 배포한 뒤 "정상 동작"을 빠르게 확인하는 절차입니다.

---

## 1. 로컬 실행

```bash
cd samples/python
pip install -r requirements.txt
python fastapi_app.py
```

Swagger UI 확인: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 2. 로컬 동작 검증 (curl)

```bash
# 기본 헬스체크
curl http://localhost:8000/api/health
# → {"status":"ok"}

# 다양한 로그 레벨 생성
curl http://localhost:8000/api/logs
# → {"message":"Diverse logs generated"}

# 커스텀 비즈니스 이벤트
curl http://localhost:8000/api/custom-event
# → {"message":"Custom event span created"}

# DB 의존성 시뮬레이션
curl http://localhost:8000/api/dependency
# → {"message":"Dependency simulated"}

# 보안 감사 이벤트 (랜덤 user_id 생성)
curl http://localhost:8000/api/secret-data
# → {"message":"...","user_id":"user-2161","document_id":44}

# 예외 테스트
curl http://localhost:8000/api/error
# → {"message":"An intentional error occurred..."}
```

---

## 3. Azure 텔레메트리 확인 (1~3분 대기 후)

Azure Portal → **Log Analytics Workspace** → **Logs** 에서 아래 쿼리 실행:

### 요청이 들어오는가?
```kusto
AppRequests
| order by TimeGenerated desc
| take 10
```

### 여러 로그 레벨이 찍히는가?
```kusto
AppTraces
| where AppRoleName == "python-api"
| order by TimeGenerated desc
| project TimeGenerated, SeverityLevel, Message
| take 20
```

### 예외가 캡처됐는가?
```kusto
AppExceptions
| order by TimeGenerated desc
| project TimeGenerated, ProblemId, OuterMessage
| take 5
```

### 보안 감사 로그가 Custom Properties에 담겼는가?
```kusto
AppTraces
| where Message contains "Audit success"
| project TimeGenerated,
          UserId = tostring(Properties["custom_dimensions"]["Actor_User_ID"]),
          DocId  = tostring(Properties["custom_dimensions"]["Target_Document_ID"]),
          Action = tostring(Properties["custom_dimensions"]["Audit_Action"])
| order by TimeGenerated desc
```

---

## 4. Azure VM에 배포된 경우

```bash
# 원격 서버 테스트 (IP는 본인 VM IP로 교체)
curl http://<VM_PUBLIC_IP>:8000/api/health
curl http://<VM_PUBLIC_IP>:8000/api/secret-data
curl http://<VM_PUBLIC_IP>:8000/api/error
```

VM 배포는 `deploy_az_vm.sh` 스크립트를 참조하세요.

---

## 5. 장애 시 1차 점검 체크리스트

| 증상 | 점검 항목 |
|---|---|
| LAW에 데이터가 안 보임 | `APPLICATIONINSIGHTS_CONNECTION_STRING` 환경변수 확인 |
| 앱 시작 오류 | `configure_azure_monitor()`가 `FastAPIInstrumentor` 전에 호출됐는지 확인 |
| 404는 나오는데 데이터 없음 | `DropUnknownRouteProcessor`가 404를 필터링 중 (정상 동작) |
| 1~3분 기다려도 안 보임 | App Insights → Live Metrics 화면에서 실시간 수신 여부 먼저 확인 |
| 방화벽/Azure 전송 차단 | VM/컨테이너의 아웃바운드 443 포트 개방 여부 확인 |
