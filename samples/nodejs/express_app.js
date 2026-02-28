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
 * 2. Express Application & Telemetry Config
 * ==========================================
 */
const { trace, metrics } = require("@opentelemetry/api");
const express = require('express');

const app = express();
const port = 3000;

// Standard explicit Manual Tracer and Meter
const tracer = trace.getTracer("node-api-tracer");
const meter = metrics.getMeter("node-api-meter");
const customEventCounter = meter.createCounter("custom_event_counter");

/**
 * 3. Middleware: 5W1H Context Injection
 * This middleware intercepts requests and adds contextual dimensions 
 * to the automatically generated OpenTelemetry HTTP Request Span.
 */
app.use((req, res, next) => {
    const span = trace.getActiveSpan();
    
    if (span) {
        // Inject 5W1H standard fields into the current HTTP Request Span
        span.setAttribute("Who", req.ip || "unknown");
        span.setAttribute("Where", `node-api${req.path}`);
        span.setAttribute("How", req.method);
        span.setAttribute("Environment", "Lab");
        span.setAttribute("AppVersion", "1.0.0");
        
        // Standard user properties for Application Insights mapping
        span.setAttribute("enduser.id", "test-user-node");
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
    // Exceptions thrown here are automatically tracked by the OpenTelemetry Distro
    throw new Error("Node.js test exception for OpenTelemetry");
});

app.get('/logs', (req, res) => {
    // In OpenTelemetry, manual logs are recorded as Events on the active Span
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
    // Custom events can be tracked via Span Events or explicit Metrics
    const span = trace.getActiveSpan();
    
    if (span) {
        span.addEvent("UserCheckout_Node_OTel", { "item": "book", "category": "fiction" });
    }
    
    // Accumulate a Business Metric
    customEventCounter.add(1, { "item": "book", "category": "fiction" });
    
    res.send("Custom event tracked via OpenTelemetry Event & Metric!");
});

app.get('/dependency', (req, res) => {
    // External HTTP calls (fetch, axios) are automatically tracked.
    // For manual dependency tracking, you can create a specific Span.
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
// Express catches the error, prevents app crash, and logs gracefully.
// OpenTelemetry automatically captures the error stack and reports it as an Exception.
app.use((err, req, res, next) => {
    console.error(`[Error Handled Gracefully] ${err.message}`);
    res.status(500).send("An intentional error occurred and was logged to Azure Monitor.");
});

app.listen(port, () => {
    console.log(`Node.js app listening at http://localhost:${port}`);
});
