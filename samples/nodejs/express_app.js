const express = require('express');
const appInsights = require('applicationinsights');

// Azure Monitor 연결 문자열 설정
// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING 또는 아래 직접 입력
const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING || "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/";

// Application Insights 초기화
appInsights.setup(connectionString)
    .setAutoDependencyCorrelation(true)
    .setAutoCollectRequests(true)
    .setAutoCollectPerformance(true, true)
    .setAutoCollectExceptions(true)
    .setAutoCollectDependencies(true)
    .setAutoCollectConsole(true)
    .start();

// 1. 표준 필드 (Advanced Fields) 명시적 지정
const client = appInsights.defaultClient;
client.context.tags[client.context.keys.cloudRole] = "node-api";
client.context.tags[client.context.keys.userAuthUserId] = "test-user-node";
client.context.tags[client.context.keys.applicationVersion] = "1.0.0";

client.commonProperties = {
    "Environment": "Lab",
    "AppVersion": "1.0.0"
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
    client.trackEvent({ name: "UserCheckout_Node", properties: { item: "book", category: "fiction" } });
    res.send("Custom event tracked!");
});

app.get('/dependency', (req, res) => {
    client.trackDependency({
        target: "http://external-api.com",
        name: "GET /users",
        data: "SELECT * FROM Users",
        duration: 120,
        resultCode: 200,
        success: true,
        dependencyTypeName: "HTTP"
    });
    res.send("Dependency tracked!");
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
