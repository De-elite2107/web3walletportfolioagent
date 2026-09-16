"""OpenAI-compatible client for the LLM gateway (LLM_BASE_URL).

No Anthropic account or Anthropic SDK involved - this is a plain OpenAI SDK
client pointed at whatever OpenAI-compatible gateway LLM_BASE_URL names
(this project was developed against Orbio), with LLM_AUTH_TOKEN as the
bearer token. Same routing shape as scripts/test_ai_routing.py.
"""

from functools import lru_cache

from openai import OpenAI

from app.config import settings


def _normalized_base_url() -> str:
    base_url = settings.llm_base_url.rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


@lru_cache(maxsize=1)
def get_ai_client() -> OpenAI:
    # The SDK's default timeout is 10 minutes - far too long for a demo path
    # where one slow LLM call shouldn't hang the whole request.
    return OpenAI(base_url=_normalized_base_url(), api_key=settings.llm_auth_token, timeout=30.0)
