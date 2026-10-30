using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using App.TestKit;
using Xunit;

namespace App.Acceptance.Tests;

/// <summary>
/// Runs API scenarios from cases/scenarios/*.json, written by the tests stage from app.json:
/// steps as roles against a fresh in-memory API, each checks the status code and fields of the answer.
/// "{id}" in a path or body is the id saved by an earlier step.
/// </summary>
public static class ScenarioCases
{
    private static readonly Lazy<Dictionary<string, Scenario>> All = new(Load);

    public static TheoryData<string> For(string ac)
    {
        var data = new TheoryData<string>();
        foreach (var (key, scenario) in All.Value.OrderBy(pair => pair.Key, StringComparer.Ordinal))
        {
            if (scenario.Ac == ac)
            {
                data.Add(key);
            }
        }
        return data;
    }

    public static async Task Run(string key)
    {
        var scenario = All.Value[key];
        await using var factory = new AppFactory();
        var clients = new Dictionary<string, HttpClient>(StringComparer.Ordinal);
        var saved = new Dictionary<string, string>(StringComparer.Ordinal);
        try
        {
            for (var index = 0; index < scenario.Steps.Count; index++)
            {
                var step = scenario.Steps[index];
                if (!clients.TryGetValue(step.As, out var client))
                {
                    client = clients[step.As] = await factory.As(step.As);
                }
                using var request = new HttpRequestMessage(new HttpMethod(step.Method), Fill(step.Path, saved));
                if (step.Body is { ValueKind: not JsonValueKind.Null and not JsonValueKind.Undefined } body)
                {
                    request.Content = new StringContent(Fill(body.GetRawText(), saved), Encoding.UTF8, "application/json");
                }
                using var response = await client.SendAsync(request, TestContext.Current.CancellationToken);
                var text = await response.Content.ReadAsStringAsync(TestContext.Current.CancellationToken);
                var where = $"step {index + 1} {step.Method} {step.Path} as {step.As}";
                Assert.True(step.Expect.Status == (int)response.StatusCode,
                    $"Assert.Equal() Failure: {where}: expected {step.Expect.Status}, actual {(int)response.StatusCode} {text}");
                if (step.Expect.Json is not null || step.Save is not null)
                {
                    using var document = JsonDocument.Parse(text);
                    foreach (var (field, expected) in step.Expect.Json ?? [])
                    {
                        Assert.True(document.RootElement.TryGetProperty(field, out var actual), $"{where}: no field {field}");
                        Assert.Equal(expected.ToString(), actual.ToString());
                    }
                    if (step.Save is not null)
                    {
                        saved[step.Save] = document.RootElement.GetProperty(step.Save).ToString();
                    }
                }
            }
        }
        finally
        {
            foreach (var client in clients.Values)
            {
                client.Dispose();
            }
        }
    }

    private static string Fill(string text, Dictionary<string, string> saved)
    {
        foreach (var (name, value) in saved)
        {
            text = text.Replace("{" + name + "}", value, StringComparison.Ordinal);
        }
        return text;
    }

    private static Dictionary<string, Scenario> Load()
    {
        var result = new Dictionary<string, Scenario>(StringComparer.Ordinal);
        var folder = Path.Combine(AppContext.BaseDirectory, "cases", "scenarios");
        if (!Directory.Exists(folder))
        {
            return result;
        }
        foreach (var path in Directory.GetFiles(folder, "*.json").Order(StringComparer.Ordinal))
        {
            var file = JsonSerializer.Deserialize<ScenarioFile>(File.ReadAllText(path), Json.Options)
                ?? throw new InvalidOperationException($"Empty scenario file {path}");
            foreach (var scenario in file.Scenarios)
            {
                result.Add(scenario.Id, scenario with { Ac = file.Ac });
            }
        }
        return result;
    }

    public sealed record ScenarioFile(string Ac, List<Scenario> Scenarios);

    public sealed record Scenario(string Id, string Ac, List<Step> Steps);

    public sealed record Step(string As, string Method, string Path, JsonElement? Body, Expectation Expect, string? Save);

    public sealed record Expectation(int Status, Dictionary<string, JsonElement>? Json);
}
