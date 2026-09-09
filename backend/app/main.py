import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.alchemy_client import AlchemyError
from app.analysis import chat_about_portfolio, summarize_portfolio
from app.chains import CHAINS
from app.config import settings
from app.database import engine, get_db
from app.eth_utils import is_valid_address
from app.portfolio import fetch_portfolio, get_latest_snapshot, save_snapshot
from app.schemas import AnalyzeRequest, ChatRequest
from app.security_scan import run_security_scan, save_scan

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


def _validate(address: str, chain_id: int) -> None:
    if not is_valid_address(address):
        raise HTTPException(status_code=400, detail=f"{address!r} is not a valid EVM address")
    if chain_id not in CHAINS:
        supported = ", ".join(str(c) for c in CHAINS)
        raise HTTPException(status_code=400, detail=f"Unsupported chain_id {chain_id} - expected one of: {supported}")


def _fetch_and_persist(db: Session, chain_id: int, address: str) -> dict:
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
    _validate(address, chain_id)
    return _fetch_and_persist(db, chain_id, address)


@app.post("/portfolio/analyze")
def analyze_portfolio(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """LLM summary of a wallet's latest portfolio snapshot.

    Reuses the most recently persisted snapshot for this wallet/chain rather
    than re-fetching on-chain data; if none exists yet (e.g. /portfolio was
    never called for it), fetches and persists one first.
    """
    _validate(req.address, req.chainId)

    portfolio = get_latest_snapshot(db, req.address, req.chainId)
    if portfolio is None:
        portfolio = _fetch_and_persist(db, req.chainId, req.address)

    try:
        summary = summarize_portfolio(portfolio)
    except Exception as e:  # noqa: BLE001 - don't let an LLM/network hiccup 500 opaquely
        raise HTTPException(status_code=502, detail=f"LLM analysis failed: {e}") from e

    logger.info("portfolio analyzed address=%s chain_id=%s model=%s", req.address, req.chainId, settings.model_name)

    return {"summary": summary, "portfolio": portfolio}


@app.post("/portfolio/chat")
def chat_portfolio(req: ChatRequest):
    """Follow-up chat about a wallet, grounded in the portfolio snapshot the
    client already has (from /portfolio or /portfolio/analyze) - no DB
    lookup, so the reply is always grounded in exactly what's on screen.
    """
    if not is_valid_address(req.address):
        raise HTTPException(status_code=400, detail=f"{req.address!r} is not a valid EVM address")

    try:
        reply = chat_about_portfolio(
            req.portfolio, [{"role": h.role, "content": h.content} for h in req.history], req.message
        )
    except Exception as e:  # noqa: BLE001 - don't let an LLM/network hiccup 500 opaquely
        raise HTTPException(status_code=502, detail=f"LLM chat failed: {e}") from e

    return {"reply": reply}


@app.get("/portfolio/security-scan")
def security_scan(
    address: str = Query(..., description="Wallet address, e.g. 0x..."),
    chain_id: int = Query(1, description="Chain ID - 1 (mainnet) or 11155111 (sepolia)"),
    db: Session = Depends(get_db),
):
    """Token-approval exposure scan: which contracts currently hold spending
    approval over this wallet's tokens, how much, and how risky that looks
    (unlimited amount + unverified spender = highest severity). Covers only
    the most recent ~10,000 blocks - see app/security_scan.py.
    """
    _validate(address, chain_id)

    try:
        result = run_security_scan(chain_id, address)
    except Exception as e:  # noqa: BLE001 - don't 500 opaquely on an RPC/API hiccup
        raise HTTPException(status_code=502, detail=f"Security scan failed: {e}") from e

    logger.info(
        "security scan address=%s chain_id=%s approvals=%d",
        address,
        chain_id,
        len(result["approvals"]),
    )

    save_scan(db, wallet_address=address, chain_id=chain_id, raw_json=result)

    return result
