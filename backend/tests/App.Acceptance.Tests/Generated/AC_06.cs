using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_06_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-06");

    [Theory, Trait("AC", "AC-06"), MemberData(nameof(Cases))]
    public void AC_06(string key) => HookCases.Run(key);
}
