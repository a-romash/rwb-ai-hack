namespace App.TestKit;

public sealed class TestClock : TimeProvider
{
    private DateTimeOffset _utcNow = DateTimeOffset.UnixEpoch;

    public void Set(DateTimeOffset utcNow) => _utcNow = utcNow;

    public void Advance(TimeSpan by) => _utcNow += by;

    public override DateTimeOffset GetUtcNow() => _utcNow;
}
