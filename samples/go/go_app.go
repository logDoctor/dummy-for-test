package main

import (
	"fmt"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/microsoft/ApplicationInsights-Go/appinsights"
)

// ==========================================
// 1. Configuration & OpenTelemetry Setup
// ==========================================
func initTelemetryClient() appinsights.TelemetryClient {
	connectionString := os.Getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
	if connectionString == "" {
		connectionString = "InstrumentationKey=your-key-here;IngestionEndpoint=https://your-endpoint.com/;LiveEndpoint=https://your-live-endpoint.com/"
	}

	telemetryConfig := appinsights.NewTelemetryConfiguration(connectionString)
	client := appinsights.NewTelemetryClientFromConfig(telemetryConfig)

	// Standard fields and common properties injection
	client.Context().Tags["ai.cloud.role"] = "go-api"
	client.Context().Tags["ai.user.authUserId"] = "test-user-go"
	client.Context().Tags["ai.application.ver"] = "1.0.0"

	client.Context().CommonProperties["Environment"] = "Lab"
	client.Context().CommonProperties["AppVersion"] = "1.0.0"

	return client
}

// ==========================================
// 2. Middleware: 5W1H Context Injection
// ==========================================
// TelemetryMiddleware intercepts requests to measure duration and inject 5W1H context
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

		// Inject 5W1H Context
		request.Properties["Who"] = c.ClientIP()
		request.Properties["Where"] = "go-api"
		request.Properties["How"] = c.Request.Method

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
		// Exception Telemetry Tracking
		client.TrackException(fmt.Errorf("Go test error for App Insights"))
		c.JSON(500, gin.H{"error": "Internal Server Error"})
	})

	r.GET("/logs", func(c *gin.Context) {
		// Trace Logging
		client.TrackTrace("This is an INFO log from Go", appinsights.Information)
		client.TrackTrace("This is a WARNING log from Go", appinsights.Warning)
		client.TrackTrace("This is an ERROR log from Go", appinsights.Error)

		c.JSON(200, gin.H{"message": "Diverse logs generated!"})
	})

	r.GET("/custom-event", func(c *gin.Context) {
		// Custom Event with properties and metrics
		event := appinsights.NewEventTelemetry("UserCheckout_Go")
		event.Properties["item"] = "book"
		event.Metrics["price"] = 15.99
		client.Track(event)

		c.JSON(200, gin.H{"message": "Custom event tracked!"})
	})

	r.GET("/dependency", func(c *gin.Context) {
		// Manual Dependency Tracking (e.g., SQL Query)
		dependency := appinsights.NewRemoteDependencyTelemetry("SQL", "tcp", "MyDatabase", "SELECT * FROM Users")
		dependency.Duration = 50 * time.Millisecond
		dependency.Success = true
		client.Track(dependency)

		c.JSON(200, gin.H{"message": "Dependency tracked!"})
	})

	// Start server
	r.Run(":8080")
}

/*
// [Installation Guide]
// go get github.com/microsoft/ApplicationInsights-Go/appinsights
// go get github.com/gin-gonic/gin
*/
