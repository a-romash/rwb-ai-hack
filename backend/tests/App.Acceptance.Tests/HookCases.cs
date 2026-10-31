using System.Reflection;
using System.Text.Json;
using App.TestKit;
using Xunit;

namespace App.Acceptance.Tests;

/// <summary>
/// Runs hook cases from cases/hooks/*.json: one JSON file per hook, written by the tests stage.
/// Hook parameters named like a field of App.Domain.Params get the rule parameter, the rest come
/// from the case inputs. Expected values come from the acceptance criteria, never from the hook.
/// </summary>
public static class HookCases
{
    private static readonly Lazy<Dictionary<string, (HookFile File, HookCase Case)>> All = new(Load);

    public static TheoryData<string> For(string ac)
    {
        var data = new TheoryData<string>();
        foreach (var (key, item) in All.Value.OrderBy(pair => pair.Key, StringComparer.Ordinal))
        {
            if (item.Case.Ac == ac)
            {
                data.Add(key);
            }
        }
        return data;
    }

    public static void Run(string key)
    {
        var (file, item) = All.Value[key];
        var type = typeof(App.Domain.Params).Assembly.GetType($"App.Domain.Hooks.{file.Hook}Hook")
            ?? throw new InvalidOperationException($"Hook class {file.Hook}Hook not found");
        var method = type.GetMethod(file.Method) ?? throw new InvalidOperationException($"{file.Hook}.{file.Method} not found");
        var arguments = method.GetParameters().Select(parameter => Argument(parameter, item)).ToArray();
        object? actual;
        try
        {
            actual = method.Invoke(Activator.CreateInstance(type), arguments);
        }
        catch (TargetInvocationException exception) when (exception.InnerException is not null)
        {
            throw exception.InnerException;
        }
        var expected = item.Expected.Deserialize(method.ReturnType, Json.Options);
        Assert.Equal(expected, actual);
    }

    private static object? Argument(ParameterInfo parameter, HookCase item)
    {
        if (item.Inputs.TryGetValue(parameter.Name!, out var value))
        {
            return value.Deserialize(parameter.ParameterType, Json.Options);
        }
        var field = typeof(App.Domain.Params).GetField(parameter.Name!);
        if (field is not null)
        {
            return field.GetValue(null);
        }
        throw new InvalidOperationException($"Case {item.Id}: no input for parameter {parameter.Name}");
    }

    private static Dictionary<string, (HookFile, HookCase)> Load()
    {
        var result = new Dictionary<string, (HookFile, HookCase)>(StringComparer.Ordinal);
        var folder = Path.Combine(AppContext.BaseDirectory, "cases", "hooks");
        if (!Directory.Exists(folder))
        {
            return result;
        }
        foreach (var path in Directory.GetFiles(folder, "*.json").Order(StringComparer.Ordinal))
        {
            var file = JsonSerializer.Deserialize<HookFile>(File.ReadAllText(path), Json.Options)
                ?? throw new InvalidOperationException($"Empty case file {path}");
            foreach (var item in file.Cases)
            {
                result.Add($"{file.Hook}:{item.Id}", (file, item));
            }
        }
        return result;
    }

    public sealed record HookFile(string Hook, string Method, List<HookCase> Cases);

    public sealed record HookCase(string Id, string Ac, Dictionary<string, JsonElement> Inputs, JsonElement Expected);
}
