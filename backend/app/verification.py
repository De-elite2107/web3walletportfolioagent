"""Contract-verification lookup for the security scan: is a spender
contract's source code published?

Etherscan (getsourcecode) is the primary source - broader coverage of
older/obscure contracts. Sourcify (no API key, confirmed working against
both a real verified contract and a non-contract address during
development) is the fallback when no Etherscan key is set, or when
Etherscan's call fails/rate-limits.
"""

import logging

import httpx

logger = logging.getLogger("orblo.verification")

_UNVERIFIED_ABI_MARKER = "Contract source code not verified"


def _etherscan_verified(chain_id: int, address: str, api_key: str) -> bool | None:
    try:
        resp = httpx.get(
            "https://api.etherscan.io/v2/api",
            params={
                "chainid": chain_id,
                "module": "contract",
                "action": "getsourcecode",
                "address": address,
                "apikey": api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            # e.g. rate-limited or a transient API error - let the caller
            # fall back to Sourcify rather than reporting a false negative.
            logger.warning("Etherscan getsourcecode non-OK for %s: %s", address, data.get("message"))
            return None
        result = data["result"][0]
        return bool(result.get("SourceCode")) and result.get("ABI") != _UNVERIFIED_ABI_MARKER
    except Exception as e:  # noqa: BLE001
        logger.warning("Etherscan verification check failed for %s: %s", address, e)
        return None


def _sourcify_verified(chain_id: int, address: str) -> bool | None:
    try:
        resp = httpx.get(f"https://sourcify.dev/server/v2/contract/{chain_id}/{address}", timeout=10)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return resp.json().get("match") is not None
    except Exception as e:  # noqa: BLE001
        logger.warning("Sourcify verification check failed for %s: %s", address, e)
        return None


def is_verified(chain_id: int, address: str, etherscan_api_key: str) -> bool | None:
    """True/False if determinable; None if both sources were inconclusive."""
    if etherscan_api_key:
        result = _etherscan_verified(chain_id, address, etherscan_api_key)
        if result is not None:
            return result
    return _sourcify_verified(chain_id, address)
