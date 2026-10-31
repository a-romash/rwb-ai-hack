using System.Reflection;
using NetArchTest.Rules;
using Xunit;

namespace App.Architecture.Tests;

public class DomainDependencyTests
{
    [Fact]
    public void Domain_does_not_depend_on_infrastructure_or_api()
    {
        var domain = Assembly.Load("App.Domain");
        var result = Types.InAssembly(domain)
            .ShouldNot()
            .HaveDependencyOnAny("App.Infrastructure", "App.Api")
            .GetResult();

        Assert.True(result.IsSuccessful);
    }
}
