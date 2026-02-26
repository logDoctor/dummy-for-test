package main

import (
	"fmt"
	"net/http"
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
	// 가속 설정을 통해 데이터를 더 빠르게 보낼 수도 있습니다.
	telemetryConfig.MaxBatchSize = 10
	telemetryConfig.MaxBatchInterval = 2 * time.Second
	
	client := appinsights.NewTelemetryClientFromConfig(telemetryConfig)

	r := gin.Default()

	// Gin 미들웨어로 요청 추적 작성 예시
	r.Use(func(c *gin.Context) {
		start := time.Now()
		c.Next()
		
		// 요청 종료 후 App Insights에 기록
		duration := time.Since(start)
		request := appinsights.NewRequestTelemetry(c.Request.Method, c.Request.URL.Path, duration, fmt.Sprintf("%d", c.Writer.Status()))
		request.Timestamp = start
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
