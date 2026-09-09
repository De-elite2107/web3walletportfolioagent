"""Public-RPC fallback for on-chain reads, used when ALCHEMY_API_KEY is blank.

Limitations vs. the Alchemy path (app/alchemy_client.py):
- Token balances are only checked for the fixed KNOWN_TOKENS list per chain
  (plain JSON-RPC has no way to discover *which* tokens a wallet holds).
- Recent transactions always come back empty - plain JSON-RPC has no
  address-activity index; listing "transactions for an address" without one
  means scanning the chain block by block, which isn't practical here.
"""

import httpx

from app.chains import CHAINS, KNOWN_TOKENS


def _call(url: str, method: str, params: list):
    resp = httpx.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error calling {method}: {data['error']}")
    return data["result"]


def _encode_balance_of(address: str) -> str:
    # balanceOf(address) - selector 0x70a08231, address left-padded to 32 bytes.
    return "0x70a08231" + address[2:].lower().rjust(64, "0")


def get_native_balance_wei(chain_id: int, address: str) -> int:
    url = CHAINS[chain_id]["public_rpc"]
    result = _call(url, "eth_getBalance", [address, "latest"])
    return int(result, 16)


def get_erc20_balances(chain_id: int, address: str) -> list[dict]:
    url = CHAINS[chain_id]["public_rpc"]
    tokens = []
    for token in KNOWN_TOKENS.get(chain_id, []):
        result = _call(url, "eth_call", [{"to": token["address"], "data": _encode_balance_of(address)}, "latest"])
        raw = int(result, 16)
        if raw == 0:
            continue
        tokens.append(
            {
                "symbol": token["symbol"],
                "contractAddress": token["address"],
                "balance": str(raw / (10 ** token["decimals"])),
            }
        )
    return tokens


def get_recent_transactions(chain_id: int, address: str, max_count: int = 20) -> list[dict]:
    return []
