package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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
