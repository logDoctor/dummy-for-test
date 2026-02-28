using OpenTelemetry.Metrics;
using OpenTelemetry.Trace;
using Azure.Monitor.OpenTelemetry.AspNetCore;
using System.Diagnostics;

// ==========================================
// 1. Configuration & OpenTelemetry Setup
// ==========================================
var builder = WebApplication.CreateBuilder(args);

// The Azure Monitor OpenTelemetry Distro automatically picks up the 
// APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.
// It sets up traces, metrics, and logs automatically.
builder.Services.AddOpenTelemetry().UseAzureMonitor();

var app = builder.Build();

// Standard explicit Manual Tracer (ActivitySource) for custom tracking
var activitySource = new ActivitySource("DotNetOTelSample");

// ==========================================
// 2. Global Error Handling Middleware
// ==========================================
// Catches exceptions gracefully and logs them before OpenTelemetry captures them.
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
// 3. Middleware: 5W1H Context Injection
// ==========================================
// Intercepts requests and adds contextual dimensions to the automatically 
// generated OpenTelemetry HTTP Request Activity (Span).
app.Use(async (context, next) =>
{
    var activity = Activity.Current;

    if (activity != null)
    {
        // Inject 5W1H standard fields
        activity.AddTag("Who", context.Connection.RemoteIpAddress?.ToString() ?? "unknown");
        activity.AddTag("Where", $"dotnet-api{context.Request.Path}");
        activity.AddTag("How", context.Request.Method);
        activity.AddTag("Environment", "Lab");
        activity.AddTag("AppVersion", "1.0.0");

        // Standard user property for Application Insights mapping
        activity.AddTag("enduser.id", "test-user-dotnet");
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
    // Exceptions are automatically captured by the framework
    throw new Exception(".NET OpenTelemetry test exception");
});

app.MapGet("/logs", (ILogger<Program> logger) => 
{
    // .NET ILogger logs are automatically collected by OpenTelemetry
    logger.LogInformation("This is an INFO log from .NET");
    logger.LogWarning("This is a WARNING log from .NET");
    logger.LogError("This is an ERROR log from .NET");
    
    return "Diverse logs generated via ILogger!";
});

app.MapGet("/custom-event", () => 
{
    // Custom events are recorded as Activity Events in OpenTelemetry
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
    // Outbound HTTP calls via HttpClient are automatically tracked as Dependencies
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
