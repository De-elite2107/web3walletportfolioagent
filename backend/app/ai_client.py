"""OpenAI-compatible client for the AI gateway (ANTHROPIC_BASE_URL).

Same routing shape as scripts/test_ai_routing.py: an OpenAI SDK client
pointed at ANTHROPIC_BASE_URL with ANTHROPIC_AUTH_TOKEN as the bearer token.
"""

from functools import lru_cache

from openai import OpenAI

from app.config import settings


def _normalized_base_url() -> str:
    base_url = settings.anthropic_base_url.rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


@lru_cache(maxsize=1)
def get_ai_client() -> OpenAI:
    # The SDK's default timeout is 10 minutes - far too long for a demo path
    # where one slow LLM call shouldn't hang the whole request.
    return OpenAI(base_url=_normalized_base_url(), api_key=settings.anthropic_auth_token, timeout=30.0)
