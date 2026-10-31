using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_09_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-09");

    [Theory, Trait("AC", "AC-09"), MemberData(nameof(Cases))]
    public void AC_09(string key) => HookCases.Run(key);
}
