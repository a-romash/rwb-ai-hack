using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_07_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-07");

    [Theory, Trait("AC", "AC-07"), MemberData(nameof(Cases))]
    public void AC_07(string key) => HookCases.Run(key);
}
