namespace App.Domain.Hooks;

public sealed class InZoneValidatorHook : App.Domain.Generated.IInZoneValidatorHook
{
    public bool Validate(string vehicleCurrentLocation, string zoneGeometry, TimeSpan zoneDetectionRadius)
    {
        return true;
    }
}
