package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;
import org.springframework.stereotype.Component;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import java.io.IOException;
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
// 5W1H Endpoint Mapping (표준화된 비즈니스 컨텍스트)
// ==========================================
class Endpoint5W1H {
    static final Map<String, String[]> MAPPING = Map.of(
        "/",              new String[]{"guide",           "documentation"},
        "/health",        new String[]{"health-check",    "periodic-monitoring"},
        "/logs",          new String[]{"log-generation",  "testing"},
        "/custom-event",  new String[]{"business-event",  "checkout-tracking"},
        "/dependency",    new String[]{"dependency-call",  "external-service-test"},
        "/error",         new String[]{"error-test",      "exception-tracking"}
    );

    static String[] resolve(String path) {
        return MAPPING.getOrDefault(path, new String[]{"unknown", "unknown"});
    }
}

// ==========================================
// 2. Telemetry Filter (Middleware): 5W1H Context Injection (통합 표준)
// ==========================================
/**
 * Application Insights Java 3.x Agent automatically extracts SLF4J's MDC
 * (Mapped Diagnostic Context) properties and records them as Custom Dimensions.
 * This filter intercepts incoming HTTP requests and injects 5W1H standard fields.
 */
@Component
class TelemetryFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String[] context5w1h = Endpoint5W1H.resolve(httpRequest.getRequestURI());

        // Who
        MDC.put("Who", httpRequest.getRemoteAddr() != null ? httpRequest.getRemoteAddr() : "unknown");
        // Where (통일: {서비스명}:{경로})
        MDC.put("Where", "java-api:" + httpRequest.getRequestURI());
        // What (신규)
        MDC.put("What", context5w1h[0]);
        // Why (신규)
        MDC.put("Why", context5w1h[1]);
        // How
        MDC.put("How", httpRequest.getMethod());
        // 공통 (Env → Environment 수정)
        MDC.put("Environment", "Lab");
        MDC.put("AppVersion", "1.0.0");

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}

// ==========================================
// 3. Business Logic (Controllers)
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
