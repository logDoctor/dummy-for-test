// OpenTelemetry 초기화가 Express 등 다른 모듈을 'require'하기 전에 반드시 가장 먼저 실행되어야 합니다!
const { useAzureMonitor } = require("@azure/monitor-opentelemetry");

// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING 이 존재하면 자동으로 매핑됩니다.
useAzureMonitor();

// OpenTelemetry 표준 API 추출
const { trace, metrics } = require("@opentelemetry/api");

const express = require('express');

const app = express();
const port = 3000;

// 표준 수동 계측을 위한 Tracer 및 Meter 생성
const tracer = trace.getTracer("node-api-tracer");
const meter = metrics.getMeter("node-api-meter");

let customEventCounter = meter.createCounter("custom_event_counter");

// 3. Middleware: HTTP 요청 등은 OpenTelemetry 프레임워크가 자동으로 계측합니다.
app.use((req, res, next) => {
    // 추가 작업이 필요할 경우 여기에 작성합니다.
    next();
});

app.get('/', (req, res) => {
    res.send('Hello World from Node.js with Azure Monitor OpenTelemetry Distro!');
});

app.get('/error', (req, res) => {
    throw new Error("Node.js test exception for OpenTelemetry");
});

app.get('/logs', (req, res) => {
    // OpenTelemetry에서는 로그(Trace)를 현재 Span의 Event로 기록할 수 있습니다.
    const span = trace.getActiveSpan();
    if (span) {
        span.addEvent("This is an INFO trace from Node.js (OpenTelemetry)", { "log.severity": "INFO" });
        span.addEvent("This is a WARNING trace from Node.js (OpenTelemetry)", { "log.severity": "WARN" });
        span.addEvent("This is an ERROR trace from Node.js (OpenTelemetry)", { "log.severity": "ERROR" });
    } else {
        tracer.startActiveSpan('manual-log-span', (manualSpan) => {
            manualSpan.addEvent("This is an INFO trace from Node.js (OpenTelemetry)");
            manualSpan.end();
        });
    }
    res.send('Diverse logs generated via OpenTelemetry!');
});

app.get('/custom-event', (req, res) => {
    // OpenTelemetry에서는 커스텀 이벤트를 Span Event나 Metric을 통해 관리합니다.
    const span = trace.getActiveSpan();
    if (span) {
        span.addEvent("UserCheckout_Node_OTel", { "item": "book", "category": "fiction" });
    }
    
    // 비즈니스 지표(Metric) 누적
    customEventCounter.add(1, { "item": "book", "category": "fiction" });
    res.send("Custom event tracked via OpenTelemetry Event & Metric!");
});

app.get('/dependency', (req, res) => {
    // 외부로 실제 HTTP 요청을 보내면 OpenTelemetry가 자동으로 Dependency 텔레메트리를 생성하지만,
    // 수동으로 종속성 이력을 남기고 싶다면 명시적으로 Span을 열어 속성을 부여합니다.
    tracer.startActiveSpan('GET /users (Manual Dependency)', (span) => {
        span.setAttribute("http.url", "http://external-api.com");
        span.setAttribute("http.method", "GET");
        span.setAttribute("http.status_code", 200);
        
        setTimeout(() => {
            span.end();
            res.send("Dependency tracked manually via OpenTelemetry Span!");
        }, 120);
    });
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
