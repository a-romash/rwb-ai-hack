namespace App.Domain.Generated;

public interface IZoneTransitionDeciderHook
{
    string Decide(string initialState, string vehicleCurrentLocation, string zoneGeometry, TimeSpan zoneDetectionRadius);
}
