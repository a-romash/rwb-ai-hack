namespace App.Domain.Hooks;

public sealed class PaymentServiceUrlPolicyHook : App.Domain.Generated.IPaymentServiceUrlPolicyHook
{
    public bool Allow()
    {
        return true;
    }
}
