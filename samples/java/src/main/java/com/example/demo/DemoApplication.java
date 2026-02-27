package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.client.RestTemplate;
import org.springframework.stereotype.Component;
import org.slf4j.MDC;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import java.io.IOException;

@Component
class TelemetryFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        // Application Insights Java 3.x Agent는 SLF4J의 MDC(Mapped Diagnostic Context)
        // 속성을
        // 자동으로 추출하여 원격 분석(Telemetry)의 커스텀 차원(Custom Dimensions)으로 기록합니다.
        MDC.put("Env", "Lab");
        MDC.put("AppVersion", "1.0.0");
        MDC.put("Who", "UserK");
        MDC.put("WhereInfo", "Java-SprintBoot-Agent");

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}

@RestController
class HelloController {

    private static final Logger logger = LoggerFactory.getLogger(HelloController.class);

    @GetMapping("/")
    public String hello() {
        // Java Agent가 이 로그를 가로채어 5W1H 속성을 자동으로 붙여 전송합니다.
        logger.info("Hello from Spring Boot with Advanced Standard Logs!");
        return "Hello World from Spring Boot (Advanced 5W1H OK)!";
    }

    @GetMapping("/error")
    public String error() {
        // 예외 기록도 표준 방식으로 처리하면 Agent가 자동으로 'Exception' 텔레메트리로 캡처합니다.
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
        // 커스텀 이벤트 역시 로그로 남길 수 있습니다. Application Insights Agent는 로거 설정을 통해 자동으로 이들을
        // 수집합니다.
        logger.info("Event_UserCheckout: item=book, category=fiction");
        return "Custom event logged!";
    }

    @GetMapping("/dependency")
    public String dependency() {
        // RestTemplate을 이용한 외부 HTTP 호출.
        // Java Agent가 자동으로 이 호출을 'Dependency' 텔레메트리로 캡처합니다.
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
 * // [추천 방식: Java Agent]
 * // Java의 경우 코드 수정 없이 'applicationinsights-agent-3.x.x.jar'를 사용하여
 * // 실행 시점에 연결하는 방식이 가장 권장됩니다.
 * // 실행 명령어: java -javaagent:path/to/applicationinsights-agent-3.4.10.jar -jar
 * app.jar
 * 
 * // [Maven 의존성 예시 (pom.xml)]
 * // <dependency>
 * // <groupId>com.microsoft.azure</groupId>
 * // <artifactId>applicationinsights-spring-boot-starter</artifactId>
 * // <version>2.6.4</version>
 * // </dependency>
 * 
 * // [설정 (application.properties)]
 * // azure.application-insights.instrumentation-key=YOUR_KEY_HERE
 * // 또는 환경 변수: APPLICATIONINSIGHTS_CONNECTION_STRING
 */
