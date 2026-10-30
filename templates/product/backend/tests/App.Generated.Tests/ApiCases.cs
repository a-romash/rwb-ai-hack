using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using App.TestKit;
using Xunit;

namespace App.Generated.Tests;

/// <summary>
/// HTTP checks from cases/api.json, written by the scaffold stage from app.json:
/// role x operation -> 200/201/403, anonymous -> 401, body without a required field -> 400.
/// </summary>
public sealed class ApiCases(AppFactory factory) : IClassFixture<AppFactory>
{
    private static readonly Lazy<Dictionary<string, ApiCase>> All = new(Load);

    public static TheoryData<string> Cases()
    {
        var data = new TheoryData<string>();
        foreach (var id in All.Value.Keys.Order(StringComparer.Ordinal))
        {
            data.Add(id);
        }
        return data;
    }

    [Theory, Trait("Kind", "api"), MemberData(nameof(Cases))]
    public async Task Status(string id)
    {
        var item = All.Value[id];
        using var client = item.Role is null ? factory.CreateClient() : await factory.As(item.Role);
        using var request = new HttpRequestMessage(new HttpMethod(item.Method), item.Path);
        if (item.Body is { ValueKind: not JsonValueKind.Null and not JsonValueKind.Undefined } body)
        {
            request.Content = new StringContent(body.GetRawText(), Encoding.UTF8, "application/json");
        }
        using var response = await client.SendAsync(request, TestContext.Current.CancellationToken);
        Assert.Equal(item.Expected, (int)response.StatusCode);
    }

    private static Dictionary<string, ApiCase> Load()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "cases", "api.json");
        if (!File.Exists(path))
        {
            return [];
        }
        var file = JsonSerializer.Deserialize<ApiFile>(File.ReadAllText(path), Json.Options)!;
        return file.Cases.ToDictionary(item => item.Id, StringComparer.Ordinal);
    }

    private sealed record ApiFile(List<ApiCase> Cases);

    public sealed record ApiCase(string Id, string? Role, string Method, string Path, JsonElement? Body, int Expected);
}
