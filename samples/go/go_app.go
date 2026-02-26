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

	r.Run(":8080")
}

/*
// [설치 방법]
// go get github.com/microsoft/ApplicationInsights-Go/appinsights
// go get github.com/gin-gonic/gin
*/
