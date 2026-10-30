namespace App.TestKit;

public sealed class PublishedEvents
{
    private readonly List<object> _items = [];

    public IReadOnlyList<object> Items => _items;
}
