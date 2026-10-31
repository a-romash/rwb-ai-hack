using System;

namespace App.Domain.Hooks
{
    public class WeekendTariffPolicyHook
    {
        public bool Allow(string currentDay, string zoneTariffHasHolidays, string zoneTariffPeriods)
        {
            if (string.IsNullOrWhiteSpace(zoneTariffPeriods))
                return false;

            if (string.IsNullOrWhiteSpace(currentDay))
                return false;

            // BR-04: Выходные и праздничные дни не учитываются отдельно.
            // Если в тарифе нет разбивки по дням недели,
            // применяется базовый тариф без надбавок и освобождений.
            // Политика не дифференцирует дни недели — тариф действует одинаково.
            return true;
        }
    }
}