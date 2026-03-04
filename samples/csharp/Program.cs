using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;
using Azure.Monitor.OpenTelemetry.AspNetCore;
using System.Diagnostics;

// ==========================================
// 1. Configuration & OpenTelemetry Setup
// ==========================================
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddOpenTelemetry().UseAzureMonitor();

var app = builder.Build();

var activitySource = new ActivitySource("DotNetOTelSample");

// ==========================================
// 5W1H Endpoint Mapping (표준화된 비즈니스 컨텍스트)
// ==========================================
var endpoint5W1H = new Dictionary<string, (string What, string Why)>
{
    { "/", ("guide", "documentation") },
    { "/health", ("health-check", "periodic-monitoring") },
    { "/logs", ("log-generation", "testing") },
    { "/custom-event", ("business-event", "checkout-tracking") },
    { "/dependency", ("dependency-call", "external-service-test") },
    { "/error", ("error-test", "exception-tracking") },
};

(string What, string Why) Resolve5W1H(string path)
{
    return endpoint5W1H.TryGetValue(path, out var result) ? result : ("unknown", "unknown");
}

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
// 3. Middleware: 5W1H Context Injection (통합 표준)
// ==========================================
app.Use(async (context, next) =>
{
    var activity = Activity.Current;

    if (activity != null)
    {
        var (what, why) = Resolve5W1H(context.Request.Path);

        // Who
        activity.AddTag("enduser.id", "test-user-dotnet");
        activity.AddTag("Who", context.Connection.RemoteIpAddress?.ToString() ?? "unknown");
        // Where
        activity.AddTag("Where", $"dotnet-api:{context.Request.Path}");
        // What (신규)
        activity.AddTag("What", what);
        // Why (신규)
        activity.AddTag("Why", why);
        // How
        activity.AddTag("How", context.Request.Method);
        // 공통
        activity.AddTag("Environment", "Lab");
        activity.AddTag("AppVersion", "1.0.0");
    }

    await next();
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

app.Run();
