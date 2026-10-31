using Xunit;

namespace App.Acceptance.Tests.Generated;

public sealed class AC_08_Tests
{
    public static TheoryData<string> Cases => HookCases.For("AC-08");

    [Theory, Trait("AC", "AC-08"), MemberData(nameof(Cases))]
    public void AC_08(string key) => HookCases.Run(key);
}
