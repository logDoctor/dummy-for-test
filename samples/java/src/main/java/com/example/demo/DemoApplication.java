package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

import java.util.Map;

// ==========================================
// 1. Application Entry Point
// ==========================================
@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}

// ==========================================
// 2. Business Logic (Controllers)
// ==========================================
@RestController
class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    @GetMapping("/")
    public String hello() {
        logger.info("Hello from Spring Boot with Advanced Standard Logs!");
        return "Hello World from Spring Boot (5W1H Standard OK)!";
    }

    @GetMapping("/error")
    public String error() {
        logger.error("Intentional error triggered for monitoring");
        throw new RuntimeException("Java Agent test exception");
    }

    @GetMapping("/logs")
    public String logs() {
        logger.info("This is an INFO log from Java");
        logger.warn("This is a WARNING log from Java");
        logger.error("This is an ERROR log from Java");
        return "Diverse logs generated!";
    }

    @GetMapping("/custom-event")
    public String customEvent() {
        logger.info("Event_UserCheckout: item=book, category=fiction");
        return "Custom event logged!";
    }

    @GetMapping("/dependency")
    public String dependency() {
        RestTemplate restTemplate = new RestTemplate();
        try {
            String result = restTemplate.getForObject("https://httpbin.org/get", String.class);
            logger.info("External dependency called successfully.");
            return "Dependency simulated! " + result.substring(0, Math.min(result.length(), 20)) + "...";
        } catch (Exception e) {
            logger.error("Dependency call failed", e);
            return "Dependency failed";
        }
    }

    @GetMapping("/secret-data")
    public Map<String, Object> secretData() {
        String userId = "user-" + (int) (Math.random() * 9000 + 1000);
        int documentId = (int) (Math.random() * 100) + 1;

        MDC.put("Audit_Action", "VIEW_DOCUMENT");
        MDC.put("Target_Document_ID", String.valueOf(documentId));
        MDC.put("Actor_User_ID", userId);
        MDC.put("Is_Success", "true");
        MDC.put("Severity", "Critical");

        MDC.put("Security.Actor", userId);
        MDC.put("Security.Action", "File_Download");
        MDC.put("Security.Target", "confidential_" + documentId + ".pdf");
        MDC.put("Security.Result", "Success");

        logger.info("Audit success: user({}) viewed document({})", userId, documentId);

        // Remove from MDC after logging
        MDC.remove("Audit_Action");
        MDC.remove("Target_Document_ID");
        MDC.remove("Actor_User_ID");
        MDC.remove("Is_Success");
        MDC.remove("Severity");
        MDC.remove("Security.Actor");
        MDC.remove("Security.Action");
        MDC.remove("Security.Target");
        MDC.remove("Security.Result");

        return Map.of(
                "message", "Secret document view logged successfully",
                "user_id", userId,
                "document_id", documentId);
    }

    @GetMapping("/normalized-log")
    public Map<String, Object> normalizedLog(String scenario) {
        if (scenario == null || scenario.isEmpty()) {
            scenario = "good";
        }

        if ("good".equals(scenario)) {
            // Example 1: INFO
            MDC.put("order_id", "order-789");
            MDC.put("payment_method", "card");
            MDC.put("amount", "29000");
            MDC.put("result", "SUCCESS");
            MDC.put("duration_ms", "320");
            logger.info("주문 처리 완료: order_id=order-789, payment=success");

            // Example 2: WARNING
            MDC.put("target", "payment-api.com");
            MDC.put("duration_ms", "4800");
            MDC.put("threshold_ms", "3000");
            MDC.put("result", "SLOW");
            MDC.remove("order_id");
            MDC.remove("payment_method");
            MDC.remove("amount");
            logger.warn("외부 결제 API 응답 지연: target=payment-api.com, duration_ms=4800");

            // Example 3: ERROR
            MDC.clear(); // Clear previous specific contexts
            MDC.put("user_id", "jo***@company.com"); // Masked
            MDC.put("error_code", "AUTH_INVALID_PASSWORD");
            MDC.put("attempt_count", "3");
            MDC.put("result", "FAILED");
            logger.error("사용자 인증 실패: user=jo***@company.com, reason=invalid_password");

            MDC.clear(); // Clean up

            return Map.of(
                    "scenario", "good",
                    "message", "Log Doctor 정규화 표준을 준수한 로그가 기록되었습니다.");
        } else {
            // Bad scenario (violations)
            logger.info("Processing...");

            MDC.put("raw_info", "john@company.com:abc123"); // Sensitive info exposed
            logger.error("Login failed for john@company.com password=abc123");
            MDC.remove("raw_info");

            logger.debug("DB query params: SELECT * FROM users WHERE id=?, params=('user-456',)");

            return Map.of(
                    "scenario", "bad",
                    "message", "정규화 표준 위반 로그가 기록되었습니다.");
        }
    }
}

/*
 * ==========================================
 * Agent Installation Guide
 * ==========================================
 * // [Recommended Approach: Java Agent]
 * // java -javaagent:path/to/applicationinsights-agent-3.4.10.jar -jar app.jar
 * 
 * // [Configuration (application.properties)]
 * // azure.application-insights.connection-string=YOUR_CONNECTION_STRING_HERE
 * // Or via environment variable: APPLICATIONINSIGHTS_CONNECTION_STRING
 */
