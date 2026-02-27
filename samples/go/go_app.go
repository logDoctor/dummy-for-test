package main

import (
	"fmt"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/microsoft/ApplicationInsights-Go/appinsights"
)

func main() {
	// Azure Monitor 연결 문자열 설정
	connectionString := os.Getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
	if connectionString == "" {
		connectionString = "InstrumentationKey=your-key-here"
	}

	// Application Insights 클라이언트 설정
	telemetryConfig := appinsights.NewTelemetryConfiguration(connectionString)
	client := appinsights.NewTelemetryClientFromConfig(telemetryConfig)

	// 1. 표준 필드 및 공통 속성 주입
	client.Context().Tags["ai.cloud.role"] = "go-api"
	client.Context().Tags["ai.user.authUserId"] = "test-user-go"
	client.Context().Tags["ai.application.ver"] = "1.0.0"

	client.Context().CommonProperties["Environment"] = "Lab"
	client.Context().CommonProperties["AppVersion"] = "1.0.0"

	r := gin.Default()

	// Gin 미들웨어로 육하원칙(Who/Where/How/Why) 자동 주입
	r.Use(func(c *gin.Context) {
		start := time.Now()
		c.Next()

		duration := time.Since(start)
		request := appinsights.NewRequestTelemetry(c.Request.Method, c.Request.URL.Path, duration, fmt.Sprintf("%d", c.Writer.Status()))
		request.Timestamp = start

		// Who
		request.Properties["Who"] = c.ClientIP()
		// Where
		request.Properties["Where"] = "go-api"
		// How
		request.Properties["How"] = c.Request.Method

		client.Track(request)
	})

	r.GET("/", func(c *gin.Context) {
		client.TrackEvent("HelloWorld_Go")
		c.JSON(200, gin.H{
			"message": "Hello World from Gin with App Insights!",
		})
	})

	r.GET("/error", func(c *gin.Context) {
		// 예외 추적 기록
		client.TrackException(fmt.Errorf("Go test error for App Insights"))
		c.JSON(500, gin.H{
			"error": "Internal Server Error",
		})
	})

	r.GET("/logs", func(c *gin.Context) {
		client.TrackTrace("This is an INFO log from Go", appinsights.Information)
		client.TrackTrace("This is a WARNING log from Go", appinsights.Warning)
		client.TrackTrace("This is an ERROR log from Go", appinsights.Error)
		c.JSON(200, gin.H{"message": "Diverse logs generated!"})
	})

	r.GET("/custom-event", func(c *gin.Context) {
		event := appinsights.NewEventTelemetry("UserCheckout_Go")
		event.Properties["item"] = "book"
		event.Metrics["price"] = 15.99
		client.Track(event)
		c.JSON(200, gin.H{"message": "Custom event tracked!"})
	})

	r.GET("/dependency", func(c *gin.Context) {
		dependency := appinsights.NewRemoteDependencyTelemetry("SQL", "tcp", "MyDatabase", "SELECT * FROM Users")
		dependency.Duration = 50 * time.Millisecond
		dependency.Success = true
		client.Track(dependency)
		c.JSON(200, gin.H{"message": "Dependency tracked!"})
	})

	r.Run(":8080")
}

/*
// [설치 방법]
// go get github.com/microsoft/ApplicationInsights-Go/appinsights
// go get github.com/gin-gonic/gin
*/
