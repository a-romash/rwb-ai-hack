namespace App.Domain.Hooks;

public sealed class PaymentWarningValidatorHook : App.Domain.Generated.IPaymentWarningValidatorHook
{
    public bool Validate(TimeSpan paymentWarningLeadTime, string sessionEndsAt)
    {
        return true;
    }
}
