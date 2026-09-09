"""USD valuation layer on top of raw balances from app/portfolio.py.

Adds price/usdValue/allocationPercent to native + each token, plus
portfolio-level totalUsdValue and a concentrationRisk flag. Never raises -
a pricing failure for one holding just leaves that holding's price fields
null (see app/pricing.py); it doesn't affect any other holding or fail the
request.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation

from app import pricing
from app.chains import CHAINS
from app.config import settings

CONCENTRATION_THRESHOLD = Decimal("0.5")


def _rpc_url(chain_id: int) -> str:
    if settings.alchemy_api_key:
        return f"https://{CHAINS[chain_id]['alchemy_subdomain']}.g.alchemy.com/v2/{settings.alchemy_api_key}"
    return CHAINS[chain_id]["public_rpc"]


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def add_valuation(portfolio: dict) -> dict:
    """Mutates and returns `portfolio` (the dict shape from fetch_portfolio)
    with pricing, USD values, allocation percentages, and a concentration
    flag added.
    """
    chain_id = portfolio["chainId"]
    rpc_url = _rpc_url(chain_id)
    tokens = portfolio["tokens"]

    # Price native + every token concurrently - each is an independent
    # on-chain call (Chainlink) and/or HTTP call (CoinGecko fallback).
    jobs: dict[str, tuple[str, str | None]] = {"native": ("ETH", None)}
    for i, token in enumerate(tokens):
        jobs[f"token:{i}"] = (token["symbol"], token["contractAddress"])

    with ThreadPoolExecutor(max_workers=max(len(jobs), 1)) as pool:
        futures = {
            key: pool.submit(pricing.get_price_usd, chain_id, symbol, contract, rpc_url)
            for key, (symbol, contract) in jobs.items()
        }
        prices = {key: future.result() for key, future in futures.items()}

    native_balance = _to_decimal(portfolio["nativeBalance"])
    native_price = prices["native"]
    native_value = (
        native_balance * native_price if native_balance is not None and native_price is not None else None
    )

    priced_tokens = []
    token_values: list[Decimal | None] = []
    for i, token in enumerate(tokens):
        price = prices[f"token:{i}"]
        balance = _to_decimal(token["balance"])
        value = balance * price if balance is not None and price is not None else None
        priced_tokens.append(
            {
                **token,
                "priceUsd": str(price) if price is not None else None,
                "usdValue": str(value) if value is not None else None,
            }
        )
        token_values.append(value)

    total = sum((v for v in [native_value, *token_values] if v is not None), Decimal(0))

    def allocation_percent(value: Decimal | None) -> float | None:
        if value is None or total == 0:
            return None
        return float((value / total * 100).quantize(Decimal("0.01")))

    for token, value in zip(priced_tokens, token_values):
        token["allocationPercent"] = allocation_percent(value)

    portfolio["tokens"] = priced_tokens
    portfolio["nativePriceUsd"] = str(native_price) if native_price is not None else None
    portfolio["nativeUsdValue"] = str(native_value) if native_value is not None else None
    portfolio["nativeAllocationPercent"] = allocation_percent(native_value)
    portfolio["totalUsdValue"] = str(total)

    concentration_risk = False
    concentration_token = None
    if total > 0:
        candidates = [("ETH", native_value)] + [(t["symbol"], v) for t, v in zip(priced_tokens, token_values)]
        for symbol, value in candidates:
            if value is not None and value / total > CONCENTRATION_THRESHOLD:
                concentration_risk = True
                concentration_token = symbol
                break

    portfolio["concentrationRisk"] = concentration_risk
    portfolio["concentrationToken"] = concentration_token

    return portfolio
