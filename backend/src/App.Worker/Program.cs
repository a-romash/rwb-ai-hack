using App.Infrastructure;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);
builder.Services.AddInfrastructure(builder.Configuration);
builder.Services.AddHostedService<Worker>();
builder.Build().Run();

/// <summary>Applies timer transitions from app.json (Generated/Timers.cs) every 30 seconds.</summary>
sealed class Worker(IServiceScopeFactory scopes, TimeProvider time, ILogger<Worker> log) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30), time);
        do
        {
            try
            {
                using var scope = scopes.CreateScope();
                var moved = await GeneratedTimers.RunAsync(scope.ServiceProvider.GetRequiredService<AppDbContext>(), time, stoppingToken);
                if (moved > 0) log.LogInformation("Timer transitions applied: {Count}", moved);
            }
            catch (Exception error) when (error is not OperationCanceledException)
            {
                // The API creates the schema on start; until then the pass fails and is retried on the next tick.
                log.LogWarning(error, "Timer pass failed");
            }
        }
        while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
