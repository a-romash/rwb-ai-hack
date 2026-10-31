using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_09_Scenario_Tests
{
    public static TheoryData<string> Cases => ScenarioCases.For("AC-09");

    [Theory, Trait("AC", "AC-09"), MemberData(nameof(Cases))]
    public Task AC_09_Scenario(string key) => ScenarioCases.Run(key);
}
