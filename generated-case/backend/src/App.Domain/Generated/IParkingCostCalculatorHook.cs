namespace App.Domain.Generated;

public interface IParkingCostCalculatorHook
{
    decimal Evaluate(TimeSpan durationValue, string vehicleVehicleType, string zoneTariffPeriods);
}
