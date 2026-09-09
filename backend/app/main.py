from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    """Placeholder portfolio endpoint.

    Will eventually fetch on-chain balances/positions for `address` (via
    viem/Alchemy on-chain reads) and run them through the security analysis
    agent. For now it returns a stub shape the frontend can build against.
    """
    return {
        "address": address,
        "tokens": [],
        "nfts": [],
        "risk_flags": [],
        "note": "placeholder endpoint - not yet implemented",
    }
