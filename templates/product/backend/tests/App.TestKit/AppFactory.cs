using System.Net.Http.Headers;
using System.Net.Http.Json;
using App.Infrastructure;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace App.TestKit;

/// <summary>The API in memory: controlled clock and an in-memory database per factory.</summary>
public class AppFactory : WebApplicationFactory<Program>
{
    private readonly string _database = Guid.NewGuid().ToString();

    public TestClock Clock { get; } = new();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureTestServices(services =>
        {
            services.AddSingleton<TimeProvider>(Clock);
            services.RemoveAll<DbContextOptions<AppDbContext>>();
            services.RemoveAll(typeof(IDbContextOptionsConfiguration<AppDbContext>));
            services.AddDbContext<AppDbContext>(options => options.UseInMemoryDatabase(_database));
        });
    }

    /// <summary>HTTP client signed in as the role through the demo login of the API.</summary>
    public async Task<HttpClient> As(string role)
    {
        var client = CreateClient();
        var response = await client.PostAsJsonAsync("/api/auth/login", new { role });
        response.EnsureSuccessStatusCode();
        var body = await response.Content.ReadFromJsonAsync<Dictionary<string, string>>();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", body!["token"]);
        return client;
    }
}
