# Multi-Stack Log Normalization Strategy

서로 다른 언어(Python, .NET, Java, Node.js, Go)에서 나오는 로그를 하나처럼 통일성 있게 관리하는 최선의 방법들을 정리했습니다.

---

## 1. Cloud Role Name (서비스 식별자) 통일
가장 먼저 해야 할 일은 각 어플리케이션이 누구인지 명확히 밝히는 것입니다. Azure Portal의 '애플리케이션 맵'이나 필터링에서 한눈에 구분할 수 있게 해줍니다.

| 언어 | 설정 방법 | 추천 설정값 (예시) |
| :--- | :--- | :--- |
| **Python** | `OTEL_SERVICE_NAME` 환경 변수 사용 | `python-api` |
| **.NET** | `TelemetryInitializer`에서 `cloud_RoleName` 할당 | `dotnet-api` |
| **Java** | `applicationinsights.json`의 `role` 속성 | `java-api` |
| **Node.js** | `client.context.tags`의 `cloudRole` 키에 할당 | `node-api` |
| **Go** | `BaseTelemetry.Tags`의 `ai.cloud.role` 키에 할당 | `go-api` |

---

## 2. 5W1H 로그 설계 (육하원칙)
로그를 분석할 때 가장 중요한 것은 "무슨 일이 벌어졌는지"를 육하원칙에 따라 기록하는 것입니다. Azure Monitor 필드와 다음과 같이 매핑할 수 있습니다.

| 원칙 | 설명 | Application Insights 필드 |
| :--- | :--- | :--- |
| **Who (누가)** | 서비스 사용자, 클라이언트 IP | `user_Id`, `client_IP`, `UserName` |
| **When (언제)** | 로그 발생 시간 | `timestamp` (자동 기록) |
| **Where (어디서)** | 서비스명, 서버 IP, API 경로 | `cloud_RoleName`, `URL`, `Method` |
| **What (무엇을)** | 구체적인 행위 (로그 메시지) | `message`, `customDimensions.Action` |
| **Why (왜)** | 성공/실패 여부, 에러 이유 | `success`, `resultCode`, `customDimensions.Reason` |
| **How (어떻게)** | 처리 방식, 상세 데이터 | `customDimensions.ActionDetails` |

---

## 3. 고급 표준 필드 매핑 (Advanced Fields)
상태창의 빈칸을 줄이기 위해 Azure Monitor의 표준 필드를 다음과 같이 활용합니다.

| 필드명 | 설명 | 구현 방법 |
| :--- | :--- | :--- |
| **`user_Id`** | 사용자 식별자 | `Context.User.Id` (모든 언어 공통 적용) |
| **`application_Version`** | 앱 배포 버전 | `Context.Component.Version` |
| **`cloud_RoleInstance`** | 서버 호스트명 | `Context.Cloud.RoleInstance` (보통 자동 수집되나 명시적 지정 가능) |
| **`session_Id`** | 세션 식별 아이디 | `Context.Session.Id` |

---

## 4. Telemetry Initializer (공통 속성 주입)
모든 로그에 **"우리 팀만 아는 공통 속성"**을 강제로 끼워 넣는 기능입니다. 

*   **추천 공통 속성**: 
    - `Environment`: (Dev, Staging, Prod)
    - `AppVersion`: (v1.0.1)
    - `Global_Trace_Id`: (마이크로서비스 간 추적용)
*   **효과**: `requests | where customDimensions.Environment == "Prod"` 처럼 모든 언어의 로그를 하나의 조건으로 검색할 수 있습니다.

---

## 3. 로그 스키마 표준화 (JSON)
코드상에서 `print()`나 `console.log()` 대신, 모든 언어에서 **동일한 구조의 JSON**으로 로그를 남기는 규칙을 정합니다.

```json
{
  "errorCode": "ERR-001",
  "userId": "user_123",
  "action": "login_attempt",
  "severity": "High"
}
```
이렇게 남기면 Application Insights의 `customDimensions.errorCode` 컬럼으로 통일되어 나타납니다.

---

## 4. KQL 가상 뷰 (Bridge Table)
언어별 SDK가 컬럼 이름을 다르게 부를 때(`MachineName` vs `host`), Log Analytics에서 쿼리로 이를 하나로 합치는 기법입니다.

```kusto
// 여러 컬럼을 'ServerName'이라는 하나의 이름으로 합치기
requests
| extend ServerName = coalesce(
    tostring(customDimensions.MachineName), 
    tostring(customDimensions.host), 
    cloud_RoleInstance
)
| project timestamp, ServerName, name, success
```

---

## 💡 결론: 어떻게 시작할까요?
가장 가성비 좋은 시작은 **1번(Cloud Role Name)**과 **2번(공통 속성 주입)**을 코드 레벨에서 맞추는 것입니다. 

지금 실행 중인 5개 서버에 대해 이 "통일화 작업"을 반영해 보고 싶으신가요? 말씀해 주시면 각 언어별로 `cloud_RoleName`을 명확히 심는 코드로 업데이트해 드릴 수 있습니다.
