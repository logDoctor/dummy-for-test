const express = require('express');
const appInsights = require('applicationinsights');

// Azure Monitor 연결 문자열 설정
// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING 또는 아래 직접 입력
const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING || "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/";

// Application Insights 초기화
// .start()를 호출하면 HTTP 요청, 예외, 종속성 추적 등이 활성화됩니다.
appInsights.setup(connectionString)
    .setAutoDependencyCorrelation(true)
    .setAutoCollectRequests(true)
    .setAutoCollectPerformance(true, true)
    .setAutoCollectExceptions(true)
    .setAutoCollectDependencies(true)
    .setAutoCollectConsole(true)
    .setUseDiskRetryCaching(true)
    .setSendLiveMetrics(true)
    .setDistributedTracingMode(appInsights.DistributedTracingModes.AI_AND_W3C)
    .start();

// 클라이언트 객체를 통해 수동 텔레메트리 전송 가능
const client = appInsights.defaultClient;

const app = express();
const port = 3000;

app.get('/', (req, res) => {
    client.trackEvent({ name: "HelloWorldEvent", properties: { platform: "NodeJS" } });
    res.send('Hello World from Express with App Insights!');
});

app.get('/error', (req, res) => {
    throw new Error("Node.js test exception for App Insights");
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
