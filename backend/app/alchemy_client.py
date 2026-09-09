"""On-chain reads via Alchemy's JSON-RPC endpoints.

Used when ALCHEMY_API_KEY is set (see app/portfolio.py for the fallback
path). Plain httpx + raw JSON-RPC - no Alchemy SDK needed for the handful
of methods used here.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx

from app.chains import CHAINS


class AlchemyError(Exception):
    """Raised on a non-2xx response or a JSON-RPC error object from Alchemy."""


def _url(chain_id: int, api_key: str) -> str:
    subdomain = CHAINS[chain_id]["alchemy_subdomain"]
    return f"https://{subdomain}.g.alchemy.com/v2/{api_key}"


def _call(url: str, method: str, params: list, request_id: int = 1) -> dict:
    try:
        resp = httpx.post(
            url,
            json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            timeout=15,
        )
    except httpx.HTTPError as e:
        raise AlchemyError(f"Could not reach Alchemy: {e}") from e

    if resp.status_code != 200:
        raise AlchemyError(f"Alchemy returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    if "error" in data:
        raise AlchemyError(f"Alchemy RPC error calling {method}: {data['error']}")
    return data["result"]


def _batch_call(url: str, calls: list[tuple[str, list]]) -> list[dict]:
    body = [
        {"jsonrpc": "2.0", "id": i, "method": method, "params": params}
        for i, (method, params) in enumerate(calls)
    ]
    try:
        resp = httpx.post(url, json=body, timeout=20)
    except httpx.HTTPError as e:
        raise AlchemyError(f"Could not reach Alchemy: {e}") from e

    if resp.status_code != 200:
        raise AlchemyError(f"Alchemy returned HTTP {resp.status_code}: {resp.text}")

    results = resp.json()
    results.sort(key=lambda r: r["id"])
    return results


def get_native_balance_wei(chain_id: int, address: str, api_key: str) -> int:
    url = _url(chain_id, api_key)
    result = _call(url, "eth_getBalance", [address, "latest"])
    return int(result, 16)


def get_token_metadata(chain_id: int, api_key: str, contract_addresses: list[str]) -> dict[str, dict]:
    """symbol/decimals for a list of ERC-20 contracts, in one batched round-trip.

    Returns {contract_address (as given): metadata_dict}; a contract that
    fails to resolve just gets an empty dict, not an exception - callers
    treat missing symbol/decimals as "unknown", not a hard failure.
    """
    if not contract_addresses:
        return {}
    url = _url(chain_id, api_key)
    results = _batch_call(url, [("alchemy_getTokenMetadata", [addr]) for addr in contract_addresses])
    return {addr: (r.get("result") or {}) for addr, r in zip(contract_addresses, results)}


def get_erc20_balances(chain_id: int, address: str, api_key: str) -> list[dict]:
    """Auto-discovered ERC-20 balances for `address` (non-zero only)."""
    url = _url(chain_id, api_key)
    result = _call(url, "alchemy_getTokenBalances", [address, "erc20"])
    nonzero = [b for b in result["tokenBalances"] if int(b["tokenBalance"], 16) != 0]
    if not nonzero:
        return []

    # One batched round-trip for metadata (symbol/decimals) instead of one
    # request per token - Alchemy supports standard JSON-RPC batching.
    metadata = get_token_metadata(chain_id, api_key, [b["contractAddress"] for b in nonzero])

    tokens = []
    for balance in nonzero:
        info = metadata.get(balance["contractAddress"], {})
        decimals = info.get("decimals")
        raw = int(balance["tokenBalance"], 16)
        adjusted = Decimal(raw) / (Decimal(10) ** decimals) if decimals is not None else Decimal(raw)
        tokens.append(
            {
                "symbol": info.get("symbol") or "UNKNOWN",
                "contractAddress": balance["contractAddress"],
                "balance": str(adjusted),
            }
        )
    return tokens


def get_recent_transactions(chain_id: int, address: str, api_key: str, max_count: int = 20) -> list[dict]:
    """Most recent `max_count` native + ERC-20 transfers involving `address`."""
    url = _url(chain_id, api_key)
    common = {
        "category": ["external", "erc20"],
        "order": "desc",
        "maxCount": hex(max_count),
        "withMetadata": True,
    }

    # fromAddress and toAddress require separate calls (no "OR" query) -
    # run them concurrently rather than paying the round-trip latency twice.
    with ThreadPoolExecutor(max_workers=2) as pool:
        outgoing_future = pool.submit(
            _call, url, "alchemy_getAssetTransfers", [{**common, "fromAddress": address}], 1
        )
        incoming_future = pool.submit(
            _call, url, "alchemy_getAssetTransfers", [{**common, "toAddress": address}], 2
        )
        outgoing = outgoing_future.result()
        incoming = incoming_future.result()

    merged = {t["uniqueId"]: t for t in outgoing["transfers"] + incoming["transfers"]}
    transfers = sorted(
        merged.values(), key=lambda t: t["metadata"]["blockTimestamp"], reverse=True
    )[:max_count]

    return [
        {
            "hash": t["hash"],
            "from": t["from"],
            "to": t["to"],
            "value": t["value"],
            "timestamp": t["metadata"]["blockTimestamp"],
        }
        for t in transfers
    ]
