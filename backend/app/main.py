import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.alchemy_client import AlchemyError
from app.chains import CHAINS
from app.database import engine, get_db
from app.eth_utils import is_valid_address
from app.portfolio import fetch_portfolio, save_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("orblo.main")

app = FastAPI(title="Orblo API", version="0.1.0")

# Allow the Vite dev server to call the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables():
    # Import registers PortfolioSnapshot on Base.metadata before create_all.
    from app import models  # noqa: F401
    from app.database import Base

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:  # noqa: BLE001 - don't crash startup if Postgres isn't up yet
        logger.warning("could not create tables (is Postgres running / DATABASE_URL correct?): %s", e)


@app.get("/health")
def health():
    """Basic liveness check - does not touch the database."""
    return {"status": "ok"}


@app.get("/portfolio")
def get_portfolio(
    address: str = Query(..., description="Wallet address, e.g. 0x..."),
    chain_id: int = Query(1, description="Chain ID - 1 (mainnet) or 11155111 (sepolia)"),
    db: Session = Depends(get_db),
):
    """Fetch native balance, ERC-20 balances, and the 20 most recent
    transactions for a wallet, then persist the snapshot to Postgres.

    Uses Alchemy if ALCHEMY_API_KEY is set, otherwise a public-RPC fallback
    with reduced functionality (see app/rpc_fallback.py).
    """
    if not is_valid_address(address):
        raise HTTPException(status_code=400, detail=f"{address!r} is not a valid EVM address")
    if chain_id not in CHAINS:
        supported = ", ".join(str(c) for c in CHAINS)
        raise HTTPException(status_code=400, detail=f"Unsupported chain_id {chain_id} - expected one of: {supported}")

    try:
        result = fetch_portfolio(chain_id, address)
    except AlchemyError as e:
        raise HTTPException(status_code=502, detail=f"Alchemy request failed: {e}") from e
    except Exception as e:  # noqa: BLE001 - surface public-RPC failures the same way
        raise HTTPException(status_code=502, detail=f"On-chain read failed: {e}") from e

    logger.info(
        "portfolio fetched address=%s chain_id=%s source=%s tokens=%d transactions=%d",
        address,
        chain_id,
        result["source"],
        len(result["tokens"]),
        len(result["recentTransactions"]),
    )

    save_snapshot(db, wallet_address=address, chain_id=chain_id, raw_json=result)

    return result
