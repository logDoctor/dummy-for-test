/**
 * ==========================================
 * 1. Configuration & OpenTelemetry Setup
 * ==========================================
 * IMPORTANT: OpenTelemetry initialization MUST happen before requiring 
 * any other modules like Express or HTTP!
 */
const { useAzureMonitor } = require("@azure/monitor-opentelemetry");

let connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING || "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/";
connectionString = connectionString.replace(/^['"]|['"]$/g, '');

// Initialize Azure Monitor OpenTelemetry Distro
useAzureMonitor({
  azureMonitorExporterOptions: {
    connectionString: connectionString
  }
});

/**
 * ==========================================
 * 2. Express Application & 5W1H Standard
 * ==========================================
 */
const { trace, metrics } = require("@opentelemetry/api");
const express = require('express');

const app = express();
const port = 3000;

const tracer = trace.getTracer("node-api-tracer");
const meter = metrics.getMeter("node-api-meter");
const customEventCounter = meter.createCounter("custom_event_counter");

/**
 * 5W1H Endpoint Mapping (표준화된 비즈니스 컨텍스트)
 */
const ENDPOINT_5W1H = {
    "/":              { What: "guide",           Why: "documentation" },
    "/health":        { What: "health-check",    Why: "periodic-monitoring" },
    "/logs":          { What: "log-generation",  Why: "testing" },
    "/custom-event":  { What: "business-event",  Why: "checkout-tracking" },
    "/dependency":    { What: "dependency-call",  Why: "external-service-test" },
    "/error":         { What: "error-test",      Why: "exception-tracking" },
};

function resolve5W1H(path) {
    return ENDPOINT_5W1H[path] || { What: "unknown", Why: "unknown" };
}

/**
 * 3. Middleware: 5W1H Context Injection (통합 표준)
 */
app.use((req, res, next) => {
    const span = trace.getActiveSpan();
    const context5w1h = resolve5W1H(req.path);
    
    if (span) {
        // Who
        span.setAttribute("enduser.id", "test-user-node");
        span.setAttribute("Who", req.ip || "unknown");
        // Where
        span.setAttribute("Where", `node-api:${req.path}`);
        // What (신규)
        span.setAttribute("What", context5w1h.What);
        // Why (신규)
        span.setAttribute("Why", context5w1h.Why);
        // How
        span.setAttribute("How", req.method);
        // 공통
        span.setAttribute("Environment", "Lab");
        span.setAttribute("AppVersion", "1.0.0");
    }
    
    next();
});

/**
 * ==========================================
 * 4. Business Logic (Routes)
 * ==========================================
 */
app.get('/', (req, res) => {
    res.send('Hello World from Node.js with Azure Monitor OpenTelemetry Distro!');
});

app.get('/error', (req, res) => {
    throw new Error("Node.js test exception for OpenTelemetry");
});

app.get('/logs', (req, res) => {
    const span = trace.getActiveSpan();
    
    if (span) {
        span.addEvent("This is an INFO trace from Node.js", { "log.severity": "INFO" });
        span.addEvent("This is a WARNING trace from Node.js", { "log.severity": "WARN" });
        span.addEvent("This is an ERROR trace from Node.js", { "log.severity": "ERROR" });
    } else {
        tracer.startActiveSpan('manual-log-span', (manualSpan) => {
            manualSpan.addEvent("This is an INFO trace from Node.js (OpenTelemetry)");
            manualSpan.end();
        });
    }
    
    res.send('Diverse logs generated via OpenTelemetry!');
});

app.get('/custom-event', (req, res) => {
    const span = trace.getActiveSpan();
    
    if (span) {
        span.addEvent("UserCheckout_Node_OTel", { "item": "book", "category": "fiction" });
    }
    
    customEventCounter.add(1, { "item": "book", "category": "fiction" });
    
    res.send("Custom event tracked via OpenTelemetry Event & Metric!");
});

app.get('/dependency', (req, res) => {
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

/**
 * ==========================================
 * 5. Global Error Handling
 * ==========================================
 */
app.use((err, req, res, next) => {
    console.error(`[Error Handled Gracefully] ${err.message}`);
    res.status(500).send("An intentional error occurred and was logged to Azure Monitor.");
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
