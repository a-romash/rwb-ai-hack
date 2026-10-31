using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;

namespace App.TestKit;

/// <summary>JSON as written in app.json and the test cases: snake_case fields and enum values.</summary>
public static class Json
{
    public static readonly JsonSerializerOptions Options = Create();

    private static JsonSerializerOptions Create()
    {
        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web)
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            // Hook cases give only the fields the rule reads; [JsonRequired] is an API rule.
            TypeInfoResolver = new DefaultJsonTypeInfoResolver
            {
                Modifiers = { info => { foreach (var property in info.Properties) property.IsRequired = false; } },
            },
        };
        options.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
        return options;
    }
}
