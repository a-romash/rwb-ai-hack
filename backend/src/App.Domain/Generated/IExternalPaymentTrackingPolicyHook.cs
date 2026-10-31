namespace App.Domain.Generated;

public interface IExternalPaymentTrackingPolicyHook
{
    bool Allow(string sessionState);
}
