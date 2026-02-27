using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

// Application Insights 설정 및 Cloud Role Name 통일
builder.Services.AddApplicationInsightsTelemetry();
builder.Services.AddSingleton<ITelemetryInitializer, MyTelemetryInitializer>();

var app = builder.Build();

app.MapGet("/", () => {
    return "Hello World from Normalized .NET!";
});

app.MapGet("/error", () => {
    throw new Exception(".NET Normalized test exception");
});

app.MapGet("/logs", (ILogger<Program> logger) => {
    logger.LogInformation("This is an INFO log from .NET");
    logger.LogWarning("This is a WARNING log from .NET");
    logger.LogError("This is an ERROR log from .NET");
    return "Diverse logs generated!";
});

app.MapGet("/custom-event", (Microsoft.ApplicationInsights.TelemetryClient telemetryClient) => {
    telemetryClient.TrackEvent("UserCheckout_DotNet", new Dictionary<string, string> { { "item", "book" } });
    return "Custom event tracked!";
});

app.MapGet("/dependency", (Microsoft.ApplicationInsights.TelemetryClient telemetryClient) => {
    telemetryClient.TrackDependency("SQL", "MyDatabase", "SELECT * FROM Users", DateTimeOffset.Now, TimeSpan.FromMilliseconds(50), true);
    return "Dependency tracked!";
});

app.Run();

// 공통 속성 및 육하원칙(5W1H)을 주입하는 Initializer 클래스
public class MyTelemetryInitializer : ITelemetryInitializer
{
    public void Initialize(ITelemetry telemetry)
    {
        // 1. 표준 필드 (Advanced Fields)
        telemetry.Context.User.Id = "test-user-dotnet";
        telemetry.Context.Component.Version = "1.0.0";

        // 2. Where (어디서 - Cloud Role Name)
        telemetry.Context.Cloud.RoleName = "dotnet-api";
        
        // 3. Who/What/How 등 공통 속성 주입
        telemetry.Context.GlobalProperties["Environment"] = "Lab";
        telemetry.Context.GlobalProperties["AppVersion"] = "1.0.0";
        
        // 요청(Request) 텔레메트리인 경우 상세 매핑
        if (telemetry is Microsoft.ApplicationInsights.DataContracts.RequestTelemetry request)
        {
            telemetry.Context.GlobalProperties["Where_Path"] = request.Url.AbsolutePath;
            telemetry.Context.GlobalProperties["How_Method"] = request.Method;
        }
    }
}

/* 
// [설치 방법]
// .NET CLI: dotnet add package Microsoft.ApplicationInsights.AspNetCore
// 
// [로그 전송 설정 (appsettings.json)]
// {
//   "ApplicationInsights": {
//     "ConnectionString": "InstrumentationKey=00000000-0000-0000-0000-000000000000"
//   }
// }
*/
