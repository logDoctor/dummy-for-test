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
// 2. Telemetry Filter (Middleware)
// ==========================================
/**
 * Application Insights Java 3.x Agent automatically extracts SLF4J's MDC
 * (Mapped Diagnostic Context) properties and records them as Custom Dimensions.
 * This filter intercepts incoming HTTP requests and injects 5W1H standard
 * fields.
 */
@Component
class TelemetryFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;

        // Inject 5W1H and common fields into MDC
        MDC.put("Env", "Lab");
        MDC.put("AppVersion", "1.0.0");
        MDC.put("Who", httpRequest.getRemoteAddr() != null ? httpRequest.getRemoteAddr() : "unknown");
        MDC.put("How", httpRequest.getMethod());
        MDC.put("Where", "java-api:" + httpRequest.getRequestURI());

        try {
            // Proceed with the Spring Boot application logic
            chain.doFilter(request, response);
        } finally {
            // Always clear MDC after the request to prevent data leaking into reused
            // threads
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
        // The Java Agent intercepts this log and automatically attaches the MDC
        // properties
        logger.info("Hello from Spring Boot with Advanced Standard Logs!");
        return "Hello World from Spring Boot (Advanced 5W1H OK)!";
    }

    @GetMapping("/error")
    public String error() {
        // Handled or unhandled exceptions are automatically captured as 'Exception'
        // telemetry
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
        // Custom events can simply be logged following a specific pattern,
        // or tracked directly if using the Application Insights SDK.
        logger.info("Event_UserCheckout: item=book, category=fiction");
        return "Custom event logged!";
    }

    @GetMapping("/dependency")
    public String dependency() {
        // External HTTP calls using RestTemplate, WebClient, etc., are
        // automatically captured as 'Dependency' telemetry by the Java Agent.
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
 * // The most recommended approach for Java is to attach the
 * // 'applicationinsights-agent-3.x.x.jar' at runtime without any code changes.
 * // Execution command: java
 * -javaagent:path/to/applicationinsights-agent-3.4.10.jar -jar app.jar
 * 
 * // [Configuration (application.properties)]
 * // azure.application-insights.connection-string=YOUR_CONNECTION_STRING_HERE
 * // Or via environment variable: APPLICATIONINSIGHTS_CONNECTION_STRING
 */
