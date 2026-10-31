using System;

namespace App.Domain.Hooks
{
    public class ExternalPaymentTrackingPolicyHook
    {
        public bool Allow(string sessionState)
        {
            return true;
        }
    }
}