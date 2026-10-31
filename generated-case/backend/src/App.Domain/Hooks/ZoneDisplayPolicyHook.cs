using System;

namespace App.Domain.Hooks
{
    public class ZoneDisplayPolicyHook
    {
        public bool Allow(string refZoneExternalZoneId)
        {
            return !string.IsNullOrWhiteSpace(refZoneExternalZoneId);
        }
    }
}