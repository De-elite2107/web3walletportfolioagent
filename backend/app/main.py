import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.ai_client import get_ai_client
from app.model_tiers import current_tier

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("orblo.portfolio")

app = FastAPI(title="Orblo API", version="0.1.0")

# Allow the Vite dev server to call the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Basic liveness check - does not touch the database."""
    return {"status": "ok"}


@app.get("/portfolio")
def get_portfolio(address: str | None = None):
    """Portfolio + security analysis endpoint.

    On-chain balance/position fetching (viem/Alchemy) isn't wired in yet, so
    this calls the AI gateway with a placeholder prompt to prove the
    tier -> model wiring end to end. The model used comes from MODEL_TIER in
    .env (draft/production/premium, see models.yaml) - swap tiers there
    without touching this code.
    """
    try:
        tier = current_tier()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    client = get_ai_client()
    response = client.chat.completions.create(
        model=tier.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a wallet security analysis assistant. Given a "
                    "wallet address with no on-chain data available yet, "
                    "reply with one short sentence noting that analysis is "
                    "pending real portfolio data."
                ),
            },
            {"role": "user", "content": f"Wallet address: {address or '(none provided)'}"},
        ],
        max_tokens=64,
    )
    analysis = response.choices[0].message.content

    logger.info(
        "portfolio analysis request tier=%s model=%s address=%s prompt_tokens=%s completion_tokens=%s",
        tier.name,
        tier.model,
        address,
        response.usage.prompt_tokens if response.usage else None,
        response.usage.completion_tokens if response.usage else None,
    )

    return {
        "address": address,
        "tokens": [],
        "nfts": [],
        "risk_flags": [],
        "analysis": analysis,
        "model_tier": tier.name,
        "model": tier.model,
        "note": "on-chain data not yet wired in - analysis text is a placeholder call",
    }
