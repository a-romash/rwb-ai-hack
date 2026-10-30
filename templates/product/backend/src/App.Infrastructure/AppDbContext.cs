using Microsoft.EntityFrameworkCore;

namespace App.Infrastructure;

/// <summary>Entity sets live in Generated/AppDbContext.Model.cs, written by the scaffold stage.</summary>
public sealed partial class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        ConfigureGenerated(modelBuilder);
        // PostgreSQL stores timestamptz in UTC only.
        foreach (var entity in modelBuilder.Model.GetEntityTypes())
        {
            foreach (var property in entity.GetProperties())
            {
                if (property.ClrType == typeof(DateTimeOffset) || property.ClrType == typeof(DateTimeOffset?))
                {
                    property.SetValueConverter(new Microsoft.EntityFrameworkCore.Storage.ValueConversion.ValueConverter<DateTimeOffset, DateTimeOffset>(
                        value => value.ToUniversalTime(), value => value));
                }
            }
        }
    }

    partial void ConfigureGenerated(ModelBuilder modelBuilder);
}
