"""USD pricing for native + ERC-20 holdings.

Primary source: on-chain Chainlink price feeds (AggregatorV3Interface),
read via a plain eth_call - accurate, no rate limits, no external API.
Fallback: CoinGecko's free API, for tokens with no known Chainlink feed on
this chain. If both fail, the caller gets None back rather than an
exception - pricing failures must never take down the whole /portfolio
response.

Feed/contract addresses were verified on-chain (decimals()==8, sane
latestRoundData()) against real mainnet/sepolia state before being
hardcoded here - see the project's dev notes.
"""

import logging
from decimal import Decimal

import httpx

logger = logging.getLogger("orblo.pricing")

_DECIMALS_SELECTOR = "0x313ce567"  # decimals()
_LATEST_ROUND_DATA_SELECTOR = "0xfeaf968c"  # latestRoundData()

# Chainlink <asset>/USD feed addresses, keyed by chain id then symbol.
# WETH is priced off the ETH/USD feed - 1 WETH always redeems for 1 ETH.
CHAINLINK_FEEDS: dict[int, dict[str, str]] = {
    1: {
        "ETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "WETH": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        "USDC": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
        "USDT": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
        "DAI": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",
    },
    11155111: {
        "ETH": "0x694AA1769357215DE4FAC081bf1f309aDC325306",
    },
}

# CoinGecko fallback: platform slug (for ERC-20 contract lookups) and the
# native-coin id, per chain. CoinGecko doesn't track Sepolia at all - its
# tokens have no real market price, so the fallback is mainnet-only.
_COINGECKO_PLATFORM = {1: "ethereum"}
_COINGECKO_NATIVE_ID = {1: "ethereum"}


def _eth_call(rpc_url: str, to: str, data: str) -> str:
    resp = httpx.post(
        rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise RuntimeError(result["error"])
    return result["result"]


def _chainlink_price(chain_id: int, symbol: str, rpc_url: str) -> Decimal | None:
    feed = CHAINLINK_FEEDS.get(chain_id, {}).get(symbol.upper())
    if not feed:
        return None
    try:
        decimals = int(_eth_call(rpc_url, feed, _DECIMALS_SELECTOR), 16)
        round_data = _eth_call(rpc_url, feed, _LATEST_ROUND_DATA_SELECTOR)[2:]
        # latestRoundData() returns 5 words: roundId, answer, startedAt,
        # updatedAt, answeredInRound - answer is the 2nd 32-byte word.
        answer = int(round_data[64:128], 16)
        if answer >= 2**255:  # two's complement, in case a feed ever went negative
            answer -= 2**256
        return Decimal(answer) / (Decimal(10) ** decimals)
    except Exception as e:  # noqa: BLE001 - fall through to CoinGecko / None
        logger.warning("Chainlink feed read failed for %s on chain %s: %s", symbol, chain_id, e)
        return None


def _coingecko_price(chain_id: int, contract_address: str | None) -> Decimal | None:
    try:
        if contract_address:
            platform = _COINGECKO_PLATFORM.get(chain_id)
            if not platform:
                return None
            resp = httpx.get(
                f"https://api.coingecko.com/api/v3/simple/token_price/{platform}",
                params={"contract_addresses": contract_address, "vs_currencies": "usd"},
                timeout=10,
            )
            resp.raise_for_status()
            entry = resp.json().get(contract_address.lower())
        else:
            coin_id = _COINGECKO_NATIVE_ID.get(chain_id)
            if not coin_id:
                return None
            resp = httpx.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd"},
                timeout=10,
            )
            resp.raise_for_status()
            entry = resp.json().get(coin_id)

        if entry and "usd" in entry:
            return Decimal(str(entry["usd"]))
        return None
    except Exception as e:  # noqa: BLE001 - caller treats None as "couldn't price it"
        logger.warning("CoinGecko price lookup failed for chain=%s contract=%s: %s", chain_id, contract_address, e)
        return None


def get_price_usd(chain_id: int, symbol: str, contract_address: str | None, rpc_url: str) -> Decimal | None:
    """USD price for one holding. Chainlink first, CoinGecko fallback, else None.

    `contract_address` is None for the native asset.
    """
    price = _chainlink_price(chain_id, symbol, rpc_url)
    if price is not None:
        return price
    return _coingecko_price(chain_id, contract_address)
