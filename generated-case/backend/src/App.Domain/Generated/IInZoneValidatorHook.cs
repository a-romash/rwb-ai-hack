namespace App.Domain.Generated;

public interface IInZoneValidatorHook
{
    bool Validate(string vehicleCurrentLocation, string zoneGeometry, TimeSpan zoneDetectionRadius);
}
