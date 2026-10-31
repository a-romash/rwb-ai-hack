namespace App.Domain.Generated;

public interface ISessionActivationPolicyHook
{
    bool Allow(string sessionState, string sessionStatus);
}
