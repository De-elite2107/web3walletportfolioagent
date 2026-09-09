"""Verify that AI requests correctly route through OpenRouter.

Makes a single test chat-completion call using the OpenAI-compatible client
(the `openai` package), pointed at ANTHROPIC_BASE_URL with
ANTHROPIC_AUTH_TOKEN sent as the bearer token. This is a plain OpenAI-SDK
call, not the Anthropic SDK - OpenRouter exposes an OpenAI-compatible
`/v1/chat/completions` endpoint, and this script's only job is to confirm
that endpoint is reachable with these credentials before anything else in
the backend is built on top of it.

Usage:
    cd backend
    python scripts/test_ai_routing.py
    TEST_MODEL="openai/gpt-4o-mini" python scripts/test_ai_routing.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
# OpenRouter's model catalog changes over time - override with any slug from
# https://openrouter.ai/models if this default has been retired.
MODEL = os.getenv("TEST_MODEL", "anthropic/claude-sonnet-4.5")


def main() -> int:
    if not BASE_URL:
        print("ANTHROPIC_BASE_URL is not set in .env - nothing to test against.")
        return 1
    if not AUTH_TOKEN:
        print(
            "ANTHROPIC_AUTH_TOKEN is not set in .env - fill it in with your "
            "OpenRouter key before running this script."
        )
        return 1

    # OpenRouter's actual API surface lives under /v1 (e.g.
    # https://openrouter.ai/api/v1/chat/completions). The OpenAI SDK appends
    # "/chat/completions" to base_url itself, so normalize here rather than
    # requiring ANTHROPIC_BASE_URL to already include the /v1 suffix.
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
        if e.status_code == 400:
            print(
                f"\nIf this is a 'model not found' error, {MODEL!r} may have "
                "been retired - check https://openrouter.ai/models for a "
                "current slug and re-run with TEST_MODEL=<slug>."
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
