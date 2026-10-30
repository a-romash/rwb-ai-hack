using System.Security.Claims;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using App.Api.Features.Generated;
using App.Infrastructure;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;

// The runtime image has no curl: the container healthcheck runs `dotnet App.Api.dll --healthcheck`.
if (args.Contains("--healthcheck"))
{
    using var probe = new HttpClient { Timeout = TimeSpan.FromSeconds(3) };
    var port = Environment.GetEnvironmentVariable("ASPNETCORE_HTTP_PORTS")?.Split(';')[0] ?? "8080";
    try
    {
        return (await probe.GetAsync($"http://127.0.0.1:{port}/health")).IsSuccessStatusCode ? 0 : 1;
    }
    catch (HttpRequestException)
    {
        return 1;
    }
    catch (TaskCanceledException)
    {
        return 1;
    }
}

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddProblemDetails();
// A malformed body is the client's 400 in every environment, not an exception turned into 500.
builder.Services.Configure<RouteHandlerOptions>(options => options.ThrowOnBadRequest = false);
builder.Services.AddOpenApi();
builder.Services.AddHealthChecks();
builder.Services.AddInfrastructure(builder.Configuration);
// API JSON uses the names of app.json: snake_case fields and enum values; missing required
// fields and nulls in non-nullable members are a 400, not a silently half-filled record.
builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower;
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower));
    options.SerializerOptions.RespectNullableAnnotations = true;
    options.SerializerOptions.RespectRequiredConstructorParameters = true;
});

var jwt = builder.Configuration.GetSection("Jwt");
var signingKey = jwt["SigningKey"] ?? throw new InvalidOperationException("Jwt:SigningKey is required.");
var securityKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(signingKey));

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.MapInboundClaims = false;
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwt["Issuer"],
            ValidAudience = jwt["Audience"],
            IssuerSigningKey = securityKey,
            RoleClaimType = "role",
        };
    });
// Tokens are issued and checked on the same TimeProvider, so a controlled test clock stays consistent.
builder.Services.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
    .Configure<TimeProvider>((options, time) =>
    {
        options.TimeProvider = time;
        options.TokenValidationParameters.LifetimeValidator = (notBefore, expires, _, _) =>
        {
            var now = time.GetUtcNow().UtcDateTime;
            return (notBefore is null || notBefore <= now.AddMinutes(5)) && (expires is null || expires > now.AddMinutes(-5));
        };
    });
builder.Services.AddAuthorization();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    // Prototype stand: the schema follows the generated model; migrations come with the first release.
    scope.ServiceProvider.GetRequiredService<AppDbContext>().Database.EnsureCreated();
}

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseAuthentication();
app.UseAuthorization();
app.MapOpenApi();
app.MapHealthChecks("/health");

var api = app.MapGroup("/api");

// Demo sign-in by role from app.json roles; the stand has no identity provider.
api.MapPost("/auth/login", (LoginRequest request, TimeProvider time) =>
{
    if (!Access.Roles.Contains(request.Role))
    {
        return Results.Unauthorized();
    }
    var token = new JsonWebTokenHandler().CreateToken(new SecurityTokenDescriptor
    {
        Issuer = jwt["Issuer"],
        Audience = jwt["Audience"],
        Claims = new Dictionary<string, object> { ["role"] = request.Role, ["sub"] = request.Role },
        IssuedAt = time.GetUtcNow().UtcDateTime,
        NotBefore = time.GetUtcNow().UtcDateTime,
        Expires = time.GetUtcNow().AddHours(8).UtcDateTime,
        SigningCredentials = new SigningCredentials(securityKey, SecurityAlgorithms.HmacSha256),
    });
    return Results.Ok(new { token, role = request.Role });
});
api.MapGet("/auth/me", (ClaimsPrincipal user) => Results.Ok(new { role = user.FindFirstValue("role") }))
    .RequireAuthorization();

GeneratedEndpoints.Map(api);

app.Run();
return 0;

public sealed record LoginRequest(string Role);

public partial class Program
{
}
