using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_01_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-01");

    [Theory, Trait("AC", "AC-01"), MemberData(nameof(Cases))]
    public void AC_01(string key) => HookCases.Run(key);
}
