using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace App.Domain.Hooks
{
    public class ParkingCostCalculatorHook
    {
        private static readonly JsonSerializerOptions _options = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };

        public decimal Evaluate(TimeSpan durationValue, string vehicleVehicleType, string zoneTariffPeriods)
        {
            if (string.IsNullOrWhiteSpace(zoneTariffPeriods))
                return 0m;

            var periods = JsonSerializer.Deserialize<List<TariffPeriod>>(zoneTariffPeriods, _options);
            if (periods == null || !periods.Any())
                return 0m;

            var totalHours = (decimal)durationValue.TotalHours;
            var cost = 0m;

            foreach (var period in periods)
            {
                if (period.PricePerHour > 0)
                {
                    cost += period.PricePerHour * totalHours;
                    break;
                }
            }

            return cost;
        }

        private class TariffPeriod
        {
            public string Start { get; set; }
            public string End { get; set; }
            public decimal PricePerHour { get; set; }
        }
    }
}