using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_05_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-05");

    [Theory, Trait("AC", "AC-05"), MemberData(nameof(Cases))]
    public void AC_05(string key) => HookCases.Run(key);
}
