package main

import (
	"fmt"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/microsoft/ApplicationInsights-Go/appinsights"
)

// ==========================================

// ==========================================
// 1. Configuration & Telemetry Setup
// ==========================================
func initTelemetryClient() appinsights.TelemetryClient {
	connectionString := os.Getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
	if connectionString == "" {
		connectionString = "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/"
	}

	telemetryConfig := appinsights.NewTelemetryConfiguration(connectionString)
	client := appinsights.NewTelemetryClientFromConfig(telemetryConfig)

	// Standard fields
	client.Context().Tags["ai.cloud.role"] = "go-api"
	client.Context().Tags["ai.user.authUserId"] = "test-user-go"
	client.Context().Tags["ai.application.ver"] = "1.0.0"

	client.Context().CommonProperties["Environment"] = "Lab"
	client.Context().CommonProperties["AppVersion"] = "1.0.0"

	return client
}

// ==========================================
// 2. Middleware: Telemetry Setup
// ==========================================
func TelemetryMiddleware(client appinsights.TelemetryClient) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()

		// Process the request
		c.Next()

		// Calculate duration
		duration := time.Since(start)

		// Create Request Telemetry
		request := appinsights.NewRequestTelemetry(
			c.Request.Method,
			c.Request.URL.Path,
			duration,
			fmt.Sprintf("%d", c.Writer.Status()),
		)
		request.Timestamp = start

		// Send to Application Insights
		client.Track(request)
	}
}

// ==========================================
// 3. Application Setup & Routes
// ==========================================
func main() {
	client := initTelemetryClient()

	// Ensure all telemetry is sent before application exits
	defer appinsights.TrackPanic(client, false)
	defer client.Channel().Close()

	r := gin.Default()

	// Apply Telemetry Middleware
	r.Use(TelemetryMiddleware(client))

	// Routes
	r.GET("/", func(c *gin.Context) {
		client.TrackEvent("HelloWorld_Go")
		c.JSON(200, gin.H{"message": "Hello World from Gin with App Insights!"})
	})

	r.GET("/error", func(c *gin.Context) {
		client.TrackException(fmt.Errorf("Go test error for App Insights"))
		c.JSON(500, gin.H{"error": "Internal Server Error"})
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

	r.GET("/secret-data", func(c *gin.Context) {
		userID := fmt.Sprintf("user-%d", time.Now().UnixNano()%9000+1000)
		documentID := time.Now().UnixNano()%100 + 1

		// Create trace for audit action
		trace := appinsights.NewTraceTelemetry(fmt.Sprintf("Audit success: user(%s) viewed document(%d)", userID, documentID), appinsights.Information)
		trace.Properties["custom_dimensions.Audit_Action"] = "VIEW_DOCUMENT"
		trace.Properties["custom_dimensions.Target_Document_ID"] = fmt.Sprintf("%d", documentID)
		trace.Properties["custom_dimensions.Actor_User_ID"] = userID
		trace.Properties["custom_dimensions.Is_Success"] = "true"
		trace.Properties["custom_dimensions.Severity"] = "Critical"

		trace.Properties["Security.Actor"] = userID
		trace.Properties["Security.Action"] = "File_Download"
		trace.Properties["Security.Target"] = fmt.Sprintf("confidential_%d.pdf", documentID)
		trace.Properties["Security.Result"] = "Success"

		client.Track(trace)

		c.JSON(200, gin.H{
			"message":     "Secret document view logged successfully",
			"user_id":     userID,
			"document_id": documentID,
		})
	})

	r.GET("/normalized-log", func(c *gin.Context) {
		scenario := c.Query("scenario")
		if scenario == "" {
			scenario = "good"
		}

		if scenario == "good" {
			// Example 1: INFO
			infoLog := appinsights.NewTraceTelemetry("주문 처리 완료: order_id=order-789, payment=success", appinsights.Information)
			infoLog.Properties["custom_dimensions.order_id"] = "order-789"
			infoLog.Properties["custom_dimensions.payment_method"] = "card"
			infoLog.Properties["custom_dimensions.amount"] = "29000"
			infoLog.Properties["custom_dimensions.result"] = "SUCCESS"
			infoLog.Properties["custom_dimensions.duration_ms"] = "320"
			client.Track(infoLog)

			// Example 2: WARNING
			warnLog := appinsights.NewTraceTelemetry("외부 결제 API 응답 지연: target=payment-api.com, duration_ms=4800", appinsights.Warning)
			warnLog.Properties["custom_dimensions.target"] = "payment-api.com"
			warnLog.Properties["custom_dimensions.duration_ms"] = "4800"
			warnLog.Properties["custom_dimensions.threshold_ms"] = "3000"
			warnLog.Properties["custom_dimensions.result"] = "SLOW"
			client.Track(warnLog)

			// Example 3: ERROR
			errorLog := appinsights.NewTraceTelemetry("사용자 인증 실패: user=jo***@company.com, reason=invalid_password", appinsights.Error)
			errorLog.Properties["custom_dimensions.user_id"] = "jo***@company.com" // Masked
			errorLog.Properties["custom_dimensions.error_code"] = "AUTH_INVALID_PASSWORD"
			errorLog.Properties["custom_dimensions.attempt_count"] = "3"
			errorLog.Properties["custom_dimensions.result"] = "FAILED"
			client.Track(errorLog)

			c.JSON(200, gin.H{
				"scenario": "good",
				"message":  "Log Doctor 정규화 표준을 준수한 로그가 기록되었습니다.",
			})
		} else {
			// Bad scenario (violations)
			client.TrackTrace("Processing...", appinsights.Information)

			badErrorLog := appinsights.NewTraceTelemetry("Login failed for john@company.com password=abc123", appinsights.Error)
			badErrorLog.Properties["custom_dimensions.raw_info"] = "john@company.com:abc123" // Sensitive info exposed
			client.Track(badErrorLog)

			badDebugLog := appinsights.NewTraceTelemetry("DB query params: SELECT * FROM users WHERE id=?, params=('user-456',)", appinsights.Verbose) // Debug level exposed
			client.Track(badDebugLog)

			c.JSON(200, gin.H{
				"scenario": "bad",
				"message":  "정규화 표준 위반 로그가 기록되었습니다.",
			})
		}
	})

	// Start server
	r.Run(":8080")
}

/*
// [Installation Guide]
// go get github.com/microsoft/ApplicationInsights-Go/appinsights
// go get github.com/gin-gonic/gin
*/
