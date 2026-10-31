using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_06_Scenario_Tests
{
    public static TheoryData<string> Cases => ScenarioCases.For("AC-06");

    [Theory, Trait("AC", "AC-06"), MemberData(nameof(Cases))]
    public Task AC_06_Scenario(string key) => ScenarioCases.Run(key);
}
