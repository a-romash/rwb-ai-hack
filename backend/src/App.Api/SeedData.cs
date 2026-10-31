using System.Text.Json;
using App.Infrastructure;

namespace App.Api;

/// <summary>Demo rows from app.json seed (seed.json, written by the scaffold stage) for a fresh stand.</summary>
public static class SeedData
{
    /// <param name="compute">Fills computed fields (due dates and the like) as the API does on create.</param>
    public static void Load(AppDbContext db, string path, JsonSerializerOptions options, ILogger logger, Action<object>? compute = null)
    {
        if (!File.Exists(path))
        {
            return;
        }
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        foreach (var entity in document.RootElement.EnumerateObject())
        {
            var type = db.Model.GetEntityTypes().FirstOrDefault(t => t.ClrType.Name == entity.Name)?.ClrType;
            if (type is null)
            {
                logger.LogWarning("Seed: no entity {Entity}", entity.Name);
                continue;
            }
            foreach (var row in entity.Value.EnumerateArray())
            {
                try
                {
                    var item = row.Deserialize(type, options)!;
                    compute?.Invoke(item);
                    db.Add(item);
                }
                catch (JsonException exc)
                {
                    // One bad demo row must not keep the stand from starting.
                    logger.LogWarning("Seed: skipped a {Entity} row: {Error}", entity.Name, exc.Message);
                }
            }
        }
        db.SaveChanges();
    }
}
