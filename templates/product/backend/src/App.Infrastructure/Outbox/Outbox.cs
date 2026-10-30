namespace App.Infrastructure.Outbox;

public sealed class Outbox
{
    public Task FlushAsync() => Task.CompletedTask;
}
