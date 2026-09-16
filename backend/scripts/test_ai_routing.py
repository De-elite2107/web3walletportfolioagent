"""Verify that AI requests correctly route through the configured AI gateway.

Makes a single test chat-completion call using the OpenAI-compatible client
(the `openai` package), pointed at LLM_BASE_URL with LLM_AUTH_TOKEN sent as
the bearer token. This is a plain OpenAI-SDK call, not the Anthropic SDK -
no Anthropic account is involved at all. The gateway at LLM_BASE_URL
(currently Orbio, api.orbio.so) exposes an OpenAI-compatible
`/chat/completions` endpoint, and this script's only job is to confirm that
endpoint is reachable with these credentials before anything else in the
backend is built on top of it.

Usage:
    cd backend
    python scripts/test_ai_routing.py
    TEST_MODEL="anthropic/claude-opus-5" python scripts/test_ai_routing.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
AUTH_TOKEN = os.getenv("LLM_AUTH_TOKEN", "")
# Confirmed working against Orbio (api.orbio.so) - override with TEST_MODEL
# if you point LLM_BASE_URL at a different gateway/model.
MODEL = os.getenv("TEST_MODEL", "anthropic/claude-sonnet-4.5")


def main() -> int:
    if not BASE_URL:
        print("LLM_BASE_URL is not set in .env - nothing to test against.")
        return 1
    if not AUTH_TOKEN:
        print(
            "LLM_AUTH_TOKEN is not set in .env - fill it in with your "
            "gateway key before running this script."
        )
        return 1

    # Some gateways (e.g. OpenRouter) put their OpenAI-compatible surface
    # under /v1 (.../api/v1/chat/completions); others (e.g. Orbio) already
    # include /v1 in LLM_BASE_URL itself. The OpenAI SDK appends
    # "/chat/completions" to base_url, so normalize here rather than assuming
    # either shape.
    base_url = BASE_URL if BASE_URL.endswith("/v1") else f"{BASE_URL}/v1"

    client = OpenAI(base_url=base_url, api_key=AUTH_TOKEN)

    print(f"Base URL : {base_url}")
    print(f"Model    : {MODEL}")
    print("Sending a single test completion call...\n")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
            max_tokens=16,
        )
    except APIStatusError as e:
        print(f"Request failed: HTTP {e.status_code}")
        print(e.response.text)
        if e.status_code in (400, 401):
            print(
                f"\nIf this is a 'model not found' or auth error, double-check "
                f"{MODEL!r} is valid for this gateway and that LLM_BASE_URL "
                "/ LLM_AUTH_TOKEN in .env match the provider you intend to "
                "hit - re-run with TEST_MODEL=<slug> to try a different model."
            )
        return 1
    except Exception as e:  # noqa: BLE001 - this is a standalone diagnostic script
        print(f"Request failed: {e!r}")
        return 1

    print("Response:")
    print(response.model_dump_json(indent=2))
    print(f"\nRouting OK - got a reply from model '{response.model}' via {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
