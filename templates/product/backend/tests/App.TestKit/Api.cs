namespace App.TestKit;

public sealed class Api
{
    public string? Role { get; private set; }

    public Api As(string role)
    {
        Role = role;
        return this;
    }
}
