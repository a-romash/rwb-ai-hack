using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_03_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-03");

    [Theory, Trait("AC", "AC-03"), MemberData(nameof(Cases))]
    public void AC_03(string key) => HookCases.Run(key);
}
