using System.Text.Json;
using System.Text.Json.Serialization;

namespace App.Infrastructure.Outbox;

/// <summary>
/// A domain event in the outbox table domain_events (R17: events through PostgreSQL, no broker).
/// Written in the same transaction as the change; readers follow Id, a PostgreSQL trigger sends
/// NOTIFY domain_events so the SSE stream wakes up at once.
/// </summary>
public sealed class DomainEvent
{
    public long Id { get; set; }
    public string Type { get; set; } = "";
    public string Entity { get; set; } = "";
    public Guid EntityId { get; set; }
    public string Payload { get; set; } = "{}";
    public DateTimeOffset OccurredAt { get; set; }
}

/// <summary>A notification for a role, from app.json notifications; text has record fields filled in.</summary>
public sealed class Notification
{
    public long Id { get; set; }
    public string Role { get; set; } = "";
    public string Name { get; set; } = "";
    public string Text { get; set; } = "";
    public string Channels { get; set; } = "";
    public DateTimeOffset CreatedAt { get; set; }
}

public static class DomainEvents
{
    private static readonly JsonSerializerOptions Payload = CreateOptions();

    /// <summary>Adds the event and the notifications it triggers; the caller's SaveChanges commits them.</summary>
    public static void Raise(AppDbContext db, string type, object record, Guid id, TimeProvider time)
    {
        var entry = new DomainEvent
        {
            Type = type,
            Entity = record.GetType().Name,
            EntityId = id,
            Payload = JsonSerializer.Serialize(record, record.GetType(), Payload),
            OccurredAt = time.GetUtcNow(),
        };
        db.Add(entry);
        foreach (var (role, name, text, channels) in GeneratedNotifications.For(type, record))
        {
            db.Add(new Notification
            {
                Role = role, Name = name, Text = text, Channels = channels,
                CreatedAt = entry.OccurredAt,
            });
        }
    }

    private static JsonSerializerOptions CreateOptions()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web) { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        options.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
        return options;
    }
}
