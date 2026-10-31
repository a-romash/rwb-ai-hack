namespace App.Domain.Generated;

public interface IWeekendTariffPolicyHook
{
    bool Allow(string currentDay, string zoneTariffHasHolidays, string zoneTariffPeriods);
}
