"""Where the model lives: one place that reads the LLM endpoint, key, model and provider from env.

LLM_BASE_URL   OpenAI-compatible endpoint, default OpenRouter (https://openrouter.ai/api/v1);
               a local vLLM is e.g. http://vllm:8000/v1
LLM_API_KEY    key for the endpoint; OPENROUTER_API_KEY and OPENAI_API_KEY are accepted as fallbacks
LLM_MODEL      model id, default qwen/qwen3.8-27b
LLM_PROVIDER   OpenRouter provider to pin (no fallbacks), default DeepInfra; empty = do not pin.
               Ignored for endpoints other than OpenRouter.
Values are read on every call, so a .env loaded later (harness.agent.load_dotenv) still applies.
"""
import os
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "qwen/qwen3.8-27b"
DEFAULT_PROVIDER = "DeepInfra"
KEY_NAMES = ("LLM_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")


def base_url() -> str:
    return (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def api_key(url: str | None = None) -> str:
    target = url or base_url()
    names = KEY_NAMES if is_openrouter(target) else ('LLM_API_KEY', 'OPENAI_API_KEY')
    if is_openrouter(target) and not is_openrouter(base_url()):
        names = ('OPENROUTER_API_KEY',)
    return next((os.environ[name] for name in names if os.environ.get(name)), "")


def model() -> str:
    return os.getenv("LLM_MODEL") or DEFAULT_MODEL


def is_openrouter(url: str | None = None) -> bool:
    return urlsplit(url or base_url()).hostname == 'openrouter.ai'


def provider(url: str | None = None) -> str | None:
    """Provider to pin on OpenRouter; None for other endpoints or when LLM_PROVIDER is empty."""
    if not is_openrouter(url):
        return None
    value = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER)
    return value or None


def key_required(url: str | None = None) -> bool:
    """A hosted endpoint needs a key; a local server may run without one."""
    return is_openrouter(url)
