using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_04_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-04");

    [Theory, Trait("AC", "AC-04"), MemberData(nameof(Cases))]
    public void AC_04(string key) => HookCases.Run(key);
}
