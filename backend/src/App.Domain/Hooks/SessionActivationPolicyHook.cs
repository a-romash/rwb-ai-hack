using System;

namespace App.Domain.Hooks
{
    public class SessionActivationPolicyHook
    {
        public bool Allow(string sessionState, string sessionStatus)
        {
            if (string.IsNullOrEmpty(sessionState) || string.IsNullOrEmpty(sessionStatus))
                return false;

            if (sessionState.Equals("active", StringComparison.OrdinalIgnoreCase))
            {
                return sessionStatus.Equals("confirmed", StringComparison.OrdinalIgnoreCase);
            }

            if (sessionState.Equals("created", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }

            if (sessionState.Equals("completed", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }

            return false;
        }
    }
}