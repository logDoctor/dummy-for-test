using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;
using Azure.Monitor.OpenTelemetry.AspNetCore;
using System.Diagnostics;

// ==========================================
// 1. Configuration & OpenTelemetry Setup
// ==========================================

// Service Name for OpenTelemetry (used as 'Role Name' in Azure Monitor)
Environment.SetEnvironmentVariable("OTEL_SERVICE_NAME", Environment.GetEnvironmentVariable("OTEL_SERVICE_NAME") ?? "dotnet-api");

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenTelemetry().UseAzureMonitor();

var app = builder.Build();

var activitySource = new ActivitySource("DotNetOTelSample");

// ==========================================
// 2. Global Error Handling Middleware
// ==========================================
app.Use(async (context, next) =>
{
    try
    {
        await next();
    }
    catch (Exception ex)
    {
        var logger = context.RequestServices.GetRequiredService<ILogger<Program>>();
        logger.LogError(ex, "[Error Handled Gracefully] {Message}", ex.Message);
        
        context.Response.StatusCode = 500;
        await context.Response.WriteAsync("An intentional error occurred and was logged to Azure Monitor.");
    }
});

// ==========================================
// 4. Business Logic (Routes)
// ==========================================

app.MapGet("/", () => 
{
    return "Hello World from .NET Core with Azure Monitor OpenTelemetry Distro!";
});

app.MapGet("/error", () => 
{
    throw new Exception(".NET OpenTelemetry test exception");
});

app.MapGet("/logs", (ILogger<Program> logger) => 
{
    logger.LogInformation("This is an INFO log from .NET");
    logger.LogWarning("This is a WARNING log from .NET");
    logger.LogError("This is an ERROR log from .NET");
    
    return "Diverse logs generated via ILogger!";
});

app.MapGet("/custom-event", () => 
{
    using var activity = activitySource.StartActivity("UserCheckout_DotNet_OTel");
    
    activity?.AddEvent(new ActivityEvent("CheckoutStarted", tags: new ActivityTagsCollection 
    { 
        { "item", "book" }, 
        { "category", "fiction" } 
    }));
    
    return "Custom event tracked via Activity Event!";
});

app.MapGet("/dependency", async () => 
{
    using var httpClient = new HttpClient();
    
    try 
    {
        var result = await httpClient.GetStringAsync("https://httpbin.org/get");
        return $"Dependency simulated! {result.Substring(0, Math.Min(result.Length, 20))}...";
    }
    catch (Exception ex)
    {
        return $"Dependency failed: {ex.Message}";
    }
});

app.MapGet("/secret-data", (ILogger<Program> logger) => 
{
    var userId = $"user-{new Random().Next(1000, 10000)}";
    var documentId = new Random().Next(1, 100);

    using var activity = activitySource.StartActivity("Audit_Action: SecretDocumentRead");
    
    activity?.SetTag("Security.Actor", userId);
    activity?.SetTag("Security.Action", "File_Download");
    activity?.SetTag("Security.Target", $"confidential_{documentId}.pdf");

    // Logging the audit event
    using (logger.BeginScope(new Dictionary<string, object>
    {
        ["Audit_Action"] = "VIEW_DOCUMENT",
        ["Target_Document_ID"] = documentId,
        ["Actor_User_ID"] = userId,
        ["Is_Success"] = true,
        ["Severity"] = "Critical"
    }))
    {
        logger.LogInformation("Audit success: user({UserId}) viewed document({DocumentId})", userId, documentId);
    }
    
    activity?.SetTag("Security.Result", "Success");

    return new 
    {
        message = "Secret document view logged successfully",
        user_id = userId,
        document_id = documentId
    };
});

app.MapGet("/normalized-log", (ILogger<Program> logger, string scenario = "good") => 
{
    using var activity = activitySource.StartActivity("Log_Normalization_Demo");

    if (scenario == "good")
    {
        // Example 1: INFO
        using (logger.BeginScope(new Dictionary<string, object>
        {
            ["order_id"] = "order-789",
            ["payment_method"] = "card",
            ["amount"] = 29000,
            ["result"] = "SUCCESS",
            ["duration_ms"] = 320
        }))
        {
            logger.LogInformation("주문 처리 완료: order_id=order-789, payment=success");
        }

        // Example 2: WARNING
        using (logger.BeginScope(new Dictionary<string, object>
        {
            ["target"] = "payment-api.com",
            ["duration_ms"] = 4800,
            ["threshold_ms"] = 3000,
            ["result"] = "SLOW"
        }))
        {
            logger.LogWarning("외부 결제 API 응답 지연: target=payment-api.com, duration_ms=4800");
        }

        // Example 3: ERROR
        using (logger.BeginScope(new Dictionary<string, object>
        {
            ["user_id"] = "jo***@company.com", // Masked
            ["error_code"] = "AUTH_INVALID_PASSWORD",
            ["attempt_count"] = 3,
            ["result"] = "FAILED"
        }))
        {
            logger.LogError("사용자 인증 실패: user=jo***@company.com, reason=invalid_password");
        }

        return new { scenario = "good", message = "Log Doctor 정규화 표준을 준수한 로그가 기록되었습니다." };
    }
    else
    {
        // Bad scenario
        logger.LogInformation("Processing...");

        using (logger.BeginScope(new Dictionary<string, object>
        {
            ["raw_info"] = "john@company.com:abc123" // Sensitive info exposed
        }))
        {
            logger.LogError("Login failed for john@company.com password=abc123");
        }

        logger.LogDebug("DB query params: SELECT * FROM users WHERE id=@id, params=('user-456',)");

        return new { scenario = "bad", message = "정규화 표준 위반 로그가 기록되었습니다." };
    }
});

app.Run();
