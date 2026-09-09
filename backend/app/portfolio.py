"""Portfolio data fetching: Alchemy when ALCHEMY_API_KEY is set, else the
public-RPC fallback (app/rpc_fallback.py) - plus snapshot persistence.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import alchemy_client, rpc_fallback
from app.config import settings
from app.models import PortfolioSnapshot
from app.valuation import add_valuation

logger = logging.getLogger("orblo.portfolio")

WEI_PER_ETHER = Decimal(10) ** 18


def fetch_portfolio(chain_id: int, address: str) -> dict:
    """Fetch native balance, ERC-20 balances, and recent transactions.

    Uses Alchemy if ALCHEMY_API_KEY is configured, otherwise the public-RPC
    fallback (see app/rpc_fallback.py for its limitations).
    """
    if settings.alchemy_api_key:
        key = settings.alchemy_api_key
        calls = {
            "native_wei": lambda: alchemy_client.get_native_balance_wei(chain_id, address, key),
            "tokens": lambda: alchemy_client.get_erc20_balances(chain_id, address, key),
            "recent_transactions": lambda: alchemy_client.get_recent_transactions(
                chain_id, address, key, max_count=20
            ),
        }
        source = "alchemy"
    else:
        calls = {
            "native_wei": lambda: rpc_fallback.get_native_balance_wei(chain_id, address),
            "tokens": lambda: rpc_fallback.get_erc20_balances(chain_id, address),
            "recent_transactions": lambda: rpc_fallback.get_recent_transactions(chain_id, address, max_count=20),
        }
        source = "public_rpc"

    # These three calls don't depend on each other - run them concurrently
    # instead of paying their combined latency in sequence.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(fn) for name, fn in calls.items()}
        results = {name: future.result() for name, future in futures.items()}

    native_wei = results["native_wei"]
    tokens = results["tokens"]
    recent_transactions = results["recent_transactions"]

    result = {
        "address": address,
        "chainId": chain_id,
        "nativeBalance": str(Decimal(native_wei) / WEI_PER_ETHER),
        "tokens": tokens,
        "recentTransactions": recent_transactions,
        "source": source,
    }

    return add_valuation(result)


def get_latest_snapshot(db: Session, wallet_address: str, chain_id: int) -> dict | None:
    """Most recently persisted snapshot's raw_json for a wallet, or None if
    there isn't one yet (e.g. /portfolio was never called for it, or the
    earlier persistence attempt failed soft - see save_snapshot).
    """
    row = (
        db.query(PortfolioSnapshot)
        .filter(PortfolioSnapshot.wallet_address == wallet_address, PortfolioSnapshot.chain_id == chain_id)
        .order_by(PortfolioSnapshot.fetched_at.desc())
        .first()
    )
    return row.raw_json if row else None


def save_snapshot(db: Session, wallet_address: str, chain_id: int, raw_json: dict) -> None:
    """Persist a fetched snapshot. Fails soft: logs and returns on any DB
    error (e.g. Postgres not running yet) rather than failing the request -
    the caller already has data to return to the client.
    """
    total_usd_value = raw_json.get("totalUsdValue")
    try:
        db.add(
            PortfolioSnapshot(
                wallet_address=wallet_address,
                chain_id=chain_id,
                total_usd_value=Decimal(total_usd_value) if total_usd_value is not None else None,
                raw_json=raw_json,
            )
        )
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning(
            "failed to persist portfolio snapshot for %s on chain %s: %s", wallet_address, chain_id, e
        )
