using Azure.Monitor.OpenTelemetry.AspNetCore;
using OpenTelemetry;
using OpenTelemetry.Trace;
using System.Diagnostics;

var builder = WebApplication.CreateBuilder(args);

// Azure Monitor OpenTelemetry Distro 설정
// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING 이 있으면 자동으로 사용됩니다.
{
    // 연결 문자열 명시적 제공 (환경 변수가 없을 경우 대비)
    var connectionString = builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"];
    if (!string.IsNullOrEmpty(connectionString))
    {
        options.ConnectionString = connectionString.Trim('\'', '"');
    }
});

var app = builder.Build();

// 가상의 Tracer 설정 (수동 Span 생성용)
var activitySource = new ActivitySource("DotNetOTelSample");

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
    // .NET ILogger 로그는 OpenTelemetry에 의해 자동으로 수집됩니다.
    logger.LogInformation("This is an INFO log from .NET (OpenTelemetry)");
    logger.LogWarning("This is a WARNING log from .NET (OpenTelemetry)");
    logger.LogError("This is an ERROR log from .NET (OpenTelemetry)");
    return "Diverse logs generated via ILogger!";
});

app.MapGet("/custom-event", () => 
{
    // OpenTelemetry에서는 커스텀 이벤트를 Activity Event로 기록합니다.
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
    // HttpClient를 통한 외부 호출은 자동으로 Dependency로 수집됩니다.
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

// 전역 에러 핸들러
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

app.Run();
