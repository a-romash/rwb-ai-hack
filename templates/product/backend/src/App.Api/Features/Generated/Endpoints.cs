// Overwritten by the scaffold stage with endpoints for the entities and commands of app.json.
namespace App.Api.Features.Generated;

public static class Access
{
    public static readonly IReadOnlySet<string> Roles = new HashSet<string>();

    public static bool Allowed(System.Security.Claims.ClaimsPrincipal user, string operation) => false;
}

public static class GeneratedEndpoints
{
    public static void Map(RouteGroupBuilder api)
    {
    }
}
