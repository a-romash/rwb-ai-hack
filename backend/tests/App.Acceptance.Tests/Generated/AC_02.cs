using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_02_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-02");

    [Theory, Trait("AC", "AC-02"), MemberData(nameof(Cases))]
    public void AC_02(string key) => HookCases.Run(key);
}
