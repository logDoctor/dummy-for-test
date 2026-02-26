using Microsoft.ApplicationInsights.Extensibility;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;

var builder = WebApplication.CreateBuilder(args);

// 1. Application Insights 서비스 추가
// appsettings.json의 "ApplicationInsights:ConnectionString" 또는 
// 환경 변수 APPLICATIONINSIGHTS_CONNECTION_STRING을 자동으로 참조합니다.
builder.Services.AddApplicationInsightsTelemetry();

var app = builder.Build();

app.MapGet("/", (TelemetryClient telemetryClient) => 
{
    // 수동 이벤트 추적 예시
    telemetryClient.TrackEvent("HelloWorldEvent_CSharp");
    return "Hello World from ASP.NET Core with App Insights!";
});

app.MapGet("/error", () => 
{
    throw new Exception("C# test exception for App Insights");
});

app.Run();

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
