using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_05_Scenario_Tests
{
    public static TheoryData<string> Cases => ScenarioCases.For("AC-05");

    [Theory, Trait("AC", "AC-05"), MemberData(nameof(Cases))]
    public Task AC_05_Scenario(string key) => ScenarioCases.Run(key);
}
