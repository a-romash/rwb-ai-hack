using Microsoft.EntityFrameworkCore;

namespace App.Infrastructure;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
}
