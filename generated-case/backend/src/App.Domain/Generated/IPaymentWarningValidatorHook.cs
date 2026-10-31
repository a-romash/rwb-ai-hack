namespace App.Domain.Generated;

public interface IPaymentWarningValidatorHook
{
    bool Validate(TimeSpan paymentWarningLeadTime, string sessionEndsAt);
}
