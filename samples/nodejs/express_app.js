/**
 * ==========================================
 * 1. Configuration & OpenTelemetry Setup
 * ==========================================
 * IMPORTANT: OpenTelemetry initialization MUST happen before requiring 
 * any other modules like Express or HTTP!
 */
const { useAzureMonitor } = require("@azure/monitor-opentelemetry");

// Service Name for OpenTelemetry (used as 'Role Name' in Azure Monitor)
process.env.OTEL_SERVICE_NAME = process.env.OTEL_SERVICE_NAME || "node-api";

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
 * 2. Express Application Registration
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

app.get('/secret-data', (req, res) => {
    tracer.startActiveSpan('Audit_Action: SecretDocumentRead', (span) => {
        const userId = `user-${Math.floor(Math.random() * 9000) + 1000}`;
        const documentId = Math.floor(Math.random() * 100) + 1;
        
        span.setAttribute("Security.Actor", userId);
        span.setAttribute("Security.Action", "File_Download");
        span.setAttribute("Security.Target", `confidential_${documentId}.pdf`);
        
        setTimeout(() => {
            // Also add a log event to represent the audit log
            span.addEvent(`Audit success: user(${userId}) viewed document(${documentId})`, {
                "log.severity": "INFO",
                "custom_dimensions.Audit_Action": "VIEW_DOCUMENT",
                "custom_dimensions.Target_Document_ID": documentId,
                "custom_dimensions.Actor_User_ID": userId,
                "custom_dimensions.Is_Success": true,
                "custom_dimensions.Severity": "Critical"
            });
            span.setAttribute("Security.Result", "Success");
            span.end();
            res.json({
                message: "Secret document view logged successfully",
                user_id: userId,
                document_id: documentId
            });
        }, Math.floor(Math.random() * 400) + 100);
    });
});

app.get('/normalized-log', (req, res) => {
    const scenario = req.query.scenario || 'good';
    const span = trace.getActiveSpan() || tracer.startSpan('Log_Normalization_Demo');
    
    if (scenario === 'good') {
        span.addEvent("주문 처리 완료: order_id=order-789, payment=success", {
            "log.severity": "INFO",
            "custom_dimensions.order_id": "order-789",
            "custom_dimensions.payment_method": "card",
            "custom_dimensions.amount": 29000,
            "custom_dimensions.result": "SUCCESS",
            "custom_dimensions.duration_ms": 320
        });
        
        span.addEvent("외부 결제 API 응답 지연: target=payment-api.com, duration_ms=4800", {
            "log.severity": "WARN",
            "custom_dimensions.target": "payment-api.com",
            "custom_dimensions.duration_ms": 4800,
            "custom_dimensions.threshold_ms": 3000,
            "custom_dimensions.result": "SLOW"
        });
        
        span.addEvent("사용자 인증 실패: user=jo***@company.com, reason=invalid_password", {
            "log.severity": "ERROR",
            "custom_dimensions.user_id": "jo***@company.com", // 마스킹 됨
            "custom_dimensions.error_code": "AUTH_INVALID_PASSWORD",
            "custom_dimensions.attempt_count": 3,
            "custom_dimensions.result": "FAILED"
        });
        
        res.json({ scenario: "good", message: "정규화 기준을 준수한 로그가 기록되었습니다." });
    } else {
        span.addEvent("Processing...", { "log.severity": "INFO" });
        span.addEvent("Login failed for john@company.com password=abc123", {
            "log.severity": "ERROR",
            "custom_dimensions.raw_info": "john@company.com:abc123" // 민감정보 노출
        });
        span.addEvent("DB query params: SELECT * FROM users WHERE id=?, params=('user-456',)", {
            "log.severity": "DEBUG" // DEBUG 로그 노출
        });
        
        res.json({ scenario: "bad", message: "정규화 위반 예시 로그가 기록되었습니다." });
    }
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
