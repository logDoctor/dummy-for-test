# VM and Multi-Language App Insights Experiment Walkthrough

We have successfully set up an Azure VM hosting three web servers in different languages, all reporting telemetry to a single Application Insights resource.

## Resources Created
- **Resource Group**: `log-doctor-experiment-rg`
- **Application Insights**: `log-doctor-ai` (In Korean Central)
- **VM**: `experiment-vm` (`20.200.217.118`)

## Application Endpoints

All services are running as `systemd` services and are configured to restart automatically.

| Stack | Port | Verification Command | Status |
| :--- | :--- | :--- | :--- |
| **Python (FastAPI)** | `8001` | `curl http://20.200.217.118:8001/` | ✅ OK |
| **.NET 8** | `8002` | `curl http://20.200.217.118:8002/` | ✅ OK |
| **Java (Simple)** | `8003` | `curl http://20.200.217.118:8003/` | ✅ OK |
| **Node.js (Express)** | `8004` | `curl http://20.200.217.118:8004/` | ✅ OK |
| **Go (Gin)** | `8005` | `curl http://20.200.217.118:8005/` | ✅ OK |

> [!TIP]
> Each application also has an `/error` endpoint (e.g., `http://20.200.217.118:8001/error`) to test exception tracking in Application Insights.

## Implementation Details
- **Python**: Uses `azure-monitor-opentelemetry` with manual span tracking.
- **.NET**: Uses `Microsoft.ApplicationInsights.AspNetCore` for automatic telemetry.
- **Java**: Uses the `applicationinsights-agent-3.4.10.jar` (recommended SDK for Java).
- **Node.js**: Uses `applicationinsights` npm package with full auto-collection enabled.
- **Go**: Uses `github.com/microsoft/ApplicationInsights-Go/appinsights` with Gin middleware.
- **Security**: The VM uses manual connection string injection in `/etc/environment` for immediate experiment stability.

## How to Verify in Azure Portal
1. Go to the **Application Insights** resource `log-doctor-ai`.
2. Click on **Live Metrics** - you should see incoming requests here if you run the `curl` commands.
3. Use **Transaction Search** to see the logs from different sources. You can filter by `Cloud role name` or other properties to distinguish between the three apps.
4. Check the **Application Map** to see how the telemetry is visualized.

## ✅ 단계 4: 고급 표준화 (고급 필드 매진) [NEW]
이제 단순히 5W1H뿐만 아니라, Azure Portal의 빈칸을 채우기 위한 **표준 필드 매핑**까지 완료되었습니다.

### 1. 적용된 고급 필드
| 필드명 | 적용 값 | 설명 |
| :--- | :--- | :--- |
| **`user_Id`** | `test-user-[언어명]` | 사용자별 로그 추적 가능 (빈칸 해결) |
| **`application_Version`** | `1.0.0` | 앱 버전별 분석 가능 (빈칸 해결) |
| **`cloud_RoleInstance`** | `experiment-vm` | 서버 장비명 자동 수집 (빈칸 해결) |

### 2. 최종 서비스 상태 (VM: 20.200.217.118)
```bash
azureuser@experiment-vm:~$ sudo systemctl is-active python_app dotnet_app java_app nodejs_app go_app
active
active
active
active
active
```

---

## 🎯 결론
이 실험을 통해 **Python, .NET, Java, Node.js, Go**라는 서로 다른 언어 환경에서도 **Azure Application Insights**를 매개체로 하여 **완벽히 동일한 로그 규격(5W1H + 표준 필드)**을 구축할 수 있음을 증명했습니다.

---

## 🚀 최종 실행 보고서 (Live Run Report)
사용자님의 요청으로 5개 스택 전체에 대해 최종 실행 테스트를 완료했습니다.

```bash
# 전체 서비스 응답 결과 (2026-02-27)
Testing Python (8001): {"message":"Advanced Telemetry OK"}
Testing .NET   (8002): Hello from .NET 8 (v2.22 SDK) with Advanced 5W1H!
Testing Java   (8003): Hello from Java with Advanced 5W1H!
Testing Node   (8004): Hello from Node.js with Advanced 5W1H!
Testing Go     (8005): {"message":"Hello from Go Advanced 5W1H!"}
```

이 모든 응답은 현재 실시간으로 **Azure Application Insights**로 전송되고 있으며, `user_Id`, `application_Version`, `cloud_RoleInstance` 필드가 빈칸 없이 꽉 채워진 상태로 수집되고 있습니다.

## Clean Up
To delete all resources created for this experiment:
```bash
az group delete --name log-doctor-experiment-rg --yes --no-wait
```
