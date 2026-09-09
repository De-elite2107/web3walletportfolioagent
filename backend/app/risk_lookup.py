"""Best-effort known-exploit/scam cross-check for flagged spender contracts.

Live web search (Tavily) finds candidate results; the existing AI gateway
(same client as app/analysis.py) then judges whether any result actually,
concretely ties the address to an incident - plain substring/keyword
matching on search snippets is too noisy (almost every result is just a
block-explorer or token-listing page mentioning the address). This never
reports "safe" - only "no known reports found" (which is not the same
claim) or a specific finding with its source.
"""

import logging

import httpx

from app.ai_client import get_ai_client
from app.config import settings

logger = logging.getLogger("orblo.risk_lookup")

NO_REPORTS_NOTE = (
    "No known exploit/scam reports found in a quick search - this does not confirm the contract "
    "is safe, only that nothing turned up."
)
NOT_CONFIGURED_NOTE = "Web search not configured (no TAVILY_API_KEY) - unable to check for public exploit/scam reports."
SEARCH_FAILED_NOTE = "Web search failed - unable to check for public exploit/scam reports right now."

_RELEVANCE_SYSTEM_PROMPT = (
    "You review web search snippets to check for reports of an exploit, hack, rug pull, or scam "
    "specifically tied to one contract address. Only report a finding if a snippet concretely and "
    "specifically ties that exact address to such an incident - a block explorer page, a token "
    "listing, or a generic security article that doesn't name this address is not a finding. "
    "If nothing concrete is found, reply with exactly: 'No known reports found.' Otherwise, reply "
    "in one or two sentences naming what was found and citing the URL. Never say a contract is "
    "'safe' or 'clean' - absence of a report is not proof of safety, only absence of a report."
)


def _search(query: str) -> list[dict]:
    resp = httpx.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
        json={"query": query, "max_results": 3},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def check_known_risk(address: str) -> str:
    if not settings.tavily_api_key:
        return NOT_CONFIGURED_NOTE

    try:
        results = _search(f"{address} exploit") + _search(f"{address} scam")
    except Exception as e:  # noqa: BLE001
        logger.warning("Risk lookup search failed for %s: %s", address, e)
        return SEARCH_FAILED_NOTE

    if not results:
        return NO_REPORTS_NOTE

    snippets = "\n\n".join(
        f"- {r.get('title', '')} ({r.get('url', '')}): {(r.get('content') or '')[:300]}" for r in results[:6]
    )

    try:
        client = get_ai_client()
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": _RELEVANCE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Contract address: {address}\n\nSearch results:\n{snippets}"},
            ],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Risk lookup relevance check failed for %s: %s", address, e)
        return NO_REPORTS_NOTE
