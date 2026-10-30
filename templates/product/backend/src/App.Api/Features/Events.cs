using System.Security.Claims;
using System.Text.Json;
using App.Api.Features.Generated;
using App.Infrastructure;
using App.Infrastructure.Outbox;
using Microsoft.EntityFrameworkCore;
using Npgsql;

namespace App.Api.Features;

/// <summary>
/// Domain events and notifications for clients: a feed after an id and an SSE stream.
/// A role sees events of the entities it may read and the notifications addressed to it.
/// PostgreSQL wakes the stream through LISTEN/NOTIFY; other providers (tests) are polled.
/// </summary>
public static class EventsEndpoints
{
    private const string Channel = "domain_events";
    private const int Batch = 200;

    public static void Map(RouteGroupBuilder api)
    {
        var group = api.MapGroup("").RequireAuthorization();
        group.MapGet("/events", async (ClaimsPrincipal user, AppDbContext db, long after = 0) =>
            Results.Ok(await Visible(db, user, after)));
        group.MapGet("/notifications", async (ClaimsPrincipal user, AppDbContext db, long after = 0) =>
        {
            var role = user.FindFirstValue("role") ?? "";
            var rows = await db.Set<Notification>().AsNoTracking()
                .Where(x => x.Role == role && x.Id > after).OrderBy(x => x.Id).Take(Batch).ToListAsync();
            return Results.Ok(rows.Select(x => new { id = x.Id, name = x.Name, text = x.Text, channels = x.Channels.Split(',', StringSplitOptions.RemoveEmptyEntries), created_at = x.CreatedAt }));
        });
        group.MapGet("/events/stream", Stream);
    }

    /// <summary>Called on start: PostgreSQL notifies listeners of every new event.</summary>
    public static void EnsureNotifyTrigger(AppDbContext db)
    {
        if (!db.Database.IsNpgsql())
        {
            return;
        }
        db.Database.ExecuteSqlRaw("""
            CREATE OR REPLACE FUNCTION notify_domain_event() RETURNS trigger AS $$
            BEGIN PERFORM pg_notify('domain_events', NEW."Id"::text); RETURN NEW; END; $$ LANGUAGE plpgsql;
            DROP TRIGGER IF EXISTS domain_events_notify ON domain_events;
            CREATE TRIGGER domain_events_notify AFTER INSERT ON domain_events FOR EACH ROW EXECUTE FUNCTION notify_domain_event();
            """);
    }

    private static async Task<List<object>> Visible(AppDbContext db, ClaimsPrincipal user, long after)
    {
        var rows = await db.Set<DomainEvent>().AsNoTracking().Where(x => x.Id > after).OrderBy(x => x.Id).Take(Batch).ToListAsync();
        return rows.Where(x => Access.Allowed(user, $"{x.Entity}.read")).Select(View).ToList();
    }

    private static object View(DomainEvent x) => new
    {
        id = x.Id, type = x.Type, entity = x.Entity, entity_id = x.EntityId,
        payload = JsonDocument.Parse(x.Payload).RootElement, occurred_at = x.OccurredAt,
    };

    private static async Task Stream(HttpContext http, ClaimsPrincipal user, IServiceScopeFactory scopes, CancellationToken ct)
    {
        http.Response.Headers.ContentType = "text/event-stream";
        http.Response.Headers.CacheControl = "no-cache";
        var cursor = long.TryParse(http.Request.Headers["Last-Event-ID"], out var last) ? last
            : long.TryParse(http.Request.Query["after"], out var after) ? after : 0;
        NpgsqlConnection? listener = null;
        try
        {
            using (var scope = scopes.CreateScope())
            {
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                if (db.Database.IsNpgsql())
                {
                    // LISTEN before the first read: an event committed in between is still seen.
                    listener = new NpgsqlConnection(db.Database.GetConnectionString());
                    await listener.OpenAsync(ct);
                    await using var command = new NpgsqlCommand($"LISTEN {Channel}", listener);
                    await command.ExecuteNonQueryAsync(ct);
                }
            }
            await http.Response.WriteAsync(": connected\n\n", ct);
            await http.Response.Body.FlushAsync(ct);
            while (!ct.IsCancellationRequested)
            {
                using (var scope = scopes.CreateScope())
                {
                    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                    var rows = await db.Set<DomainEvent>().AsNoTracking().Where(x => x.Id > cursor).OrderBy(x => x.Id).Take(Batch).ToListAsync(ct);
                    foreach (var row in rows)
                    {
                        cursor = row.Id;
                        if (!Access.Allowed(user, $"{row.Entity}.read"))
                        {
                            continue;
                        }
                        await http.Response.WriteAsync($"id: {row.Id}\nevent: {row.Type}\ndata: {JsonSerializer.Serialize(View(row))}\n\n", ct);
                    }
                }
                await http.Response.WriteAsync(": keepalive\n\n", ct);
                await http.Response.Body.FlushAsync(ct);
                // Notifications are hints; the timeout also catches writes made without NOTIFY.
                if (listener is not null)
                {
                    await listener.WaitAsync(TimeSpan.FromSeconds(15), ct);
                }
                else
                {
                    await Task.Delay(TimeSpan.FromSeconds(1), ct);
                }
            }
        }
        catch (OperationCanceledException)
        {
            // The client went away.
        }
        finally
        {
            if (listener is not null)
            {
                await listener.DisposeAsync();
            }
        }
    }
}
