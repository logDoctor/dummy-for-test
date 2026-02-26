package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import com.microsoft.applicationinsights.TelemetryClient;
import org.springframework.beans.factory.annotation.Autowired;

@SpringBootApplication
public class DemoApplication {

	public static void main(String[] args) {
		SpringApplication.run(DemoApplication.class, args);
	}
}

@RestController
class HelloController {

    // TelemetryClient는 Spring Bean으로 자동 등록됩니다 (연결 문자열 설정 시)
    @Autowired
    private TelemetryClient telemetryClient;

    @GetMapping("/")
    public String hello() {
        // 수동 이벤트 추적
        telemetryClient.trackEvent("HelloWorldEvent_Java");
        return "Hello World from Spring Boot with App Insights!";
    }

    @GetMapping("/error")
    public String error() {
        throw new RuntimeException("Java test exception for App Insights");
    }
}

/*
// [추천 방식: Java Agent]
// Java의 경우 코드 수정 없이 'applicationinsights-agent-3.x.x.jar'를 사용하여 
// 실행 시점에 연결하는 방식이 가장 권장됩니다.
// 실행 명령어: java -javaagent:path/to/applicationinsights-agent-3.4.10.jar -jar app.jar

// [Maven 의존성 예시 (pom.xml)]
// <dependency>
//     <groupId>com.microsoft.azure</groupId>
//     <artifactId>applicationinsights-spring-boot-starter</artifactId>
//     <version>2.6.4</version>
// </dependency>

// [설정 (application.properties)]
// azure.application-insights.instrumentation-key=YOUR_KEY_HERE
// 또는 환경 변수: APPLICATIONINSIGHTS_CONNECTION_STRING
*/
