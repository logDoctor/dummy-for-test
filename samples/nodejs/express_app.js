const express = require('express');
const appInsights = require('applicationinsights');

// Azure Monitor 연결 문자열 설정
// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING 또는 아래 직접 입력
const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING || "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/";

// Application Insights 초기화 (Node.js SDK 3.x)
appInsights.setup(connectionString)
    .setAutoDependencyCorrelation(true)
    .setAutoCollectRequests(true)
    .setAutoCollectPerformance(true, true)
    .setAutoCollectExceptions(true)
    .setAutoCollectDependencies(true)
    .setAutoCollectConsole(true)
    .start();

// 1. 표준 필드 (Advanced Fields) 명시적 지정
// Node 3.x에서는 defaultClient 설정 방식이 달라졌습니다.
const client = appInsights.defaultClient;

// Node.js 3.x (OpenTelemetry 기반) 에서는 공통 속성을 이렇게 설정합니다.
client.commonProperties = {
    "Environment": "Lab",
    "AppVersion": "1.0.0",
    "cloud_RoleName": "node-api"
};

const app = express();
const port = 3000;

// 3. Middleware: 육하원칙(Who/Where/How) 자동 주입
app.use((req, res, next) => {
    // 현재 요청의 텔레메트리에 속성 추가
    const telemetry = appInsights.defaultClient;
    telemetry.trackNodeHttpRequest({ request: req, response: res }); // 기본 추적
    
    // 추가 5W1H 속성
    // Note: Node.js SDK는 context.tags를 통해 RoleName 등을 관리합니다.
    next();
});

app.get('/', (req, res) => {
    res.send('Hello World from Node.js with 5W1H Telemetry!');
});

app.get('/error', (req, res) => {
    throw new Error("Node.js test exception for App Insights");
});

app.get('/logs', (req, res) => {
    client.trackTrace({ message: "This is an INFO trace from Node.js", severity: appInsights.Contracts.SeverityLevel.Information });
    client.trackTrace({ message: "This is a WARNING trace from Node.js", severity: appInsights.Contracts.SeverityLevel.Warning });
    client.trackTrace({ message: "This is an ERROR trace from Node.js", severity: appInsights.Contracts.SeverityLevel.Error });
    res.send('Diverse logs generated!');
});

app.get('/custom-event', (req, res) => {
    // trackEvent는 name 속성이 필요
    client.trackEvent({ name: "UserCheckout_Node", properties: { item: "book", category: "fiction" } });
    res.send("Custom event tracked!");
});

app.get('/dependency', (req, res) => {
    // trackDependency
    client.trackDependency({
        target: "http://external-api.com",
        name: "GET /users",
        data: "SELECT * FROM Users",
        duration: 120,
        resultCode: "200",
        success: true,
        dependencyTypeName: "HTTP" // 최신 SDK v3 에서는 dependencyTypeName이 HTTP/SQL 등으로 쓰임
    });
    res.send("Dependency tracked!");
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
