namespace App.Domain.Hooks;

public sealed class ZoneTransitionDeciderHook : App.Domain.Generated.IZoneTransitionDeciderHook
{
    public string Decide(string initialState, string vehicleCurrentLocation, string zoneGeometry, TimeSpan zoneDetectionRadius)
    {
        return initialState;
    }
}
