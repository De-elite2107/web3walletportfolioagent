# Orblo

Wallet portfolio + security analysis agent. Monorepo with a React/Vite/TypeScript
frontend and a FastAPI backend.

```
.
├── frontend/   React + Vite + TypeScript, Wagmi + RainbowKit, viem
├── backend/    FastAPI + SQLAlchemy (PostgreSQL)
├── .env        real environment variables (gitignored, not committed)
└── .env.example  template for the variables backend/scripts expect
```

## 1. Environment

Copy `.env.example` to `.env` at the repo root and fill in the values:

```
ANTHROPIC_BASE_URL=https://api.orbio.so/api/v1
ANTHROPIC_AUTH_TOKEN=      # your Orbio key, used as the bearer token
ANTHROPIC_API_KEY=         # leave empty unless told otherwise
ALCHEMY_API_KEY=           # for on-chain reads
DATABASE_URL=              # e.g. postgresql://postgres:postgres@localhost:5432/orblo
MODEL_TIER=draft           # draft | production | premium - see backend/models.yaml
```

`.env` is gitignored - never commit real secrets.

## 2. Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# start Postgres however you prefer, then create the DB, e.g.:
#   createdb orblo

uvicorn app.main:app --reload --port 8000
```

- `GET /health` - liveness check, doesn't touch the database.
- `GET /portfolio?address=0x...` - calls the AI gateway with a placeholder
  prompt (real on-chain reads + analysis logic aren't wired in yet) and
  returns a stub shape the frontend can build against. Which model answers
  is controlled by `MODEL_TIER`.

### Model tiers

`backend/models.yaml` maps three tiers to gateway model ids; `/portfolio`
reads whichever tier `MODEL_TIER` in `.env` selects (default `draft`) and
logs `tier=... model=...` plus token counts for every request, so spend is
traceable per tier from the uvicorn log:

| Tier | Model | Use for |
|---|---|---|
| `draft` | `anthropic/claude-haiku-4.5` | iterating on prompts/logic - the default, so nobody burns production spend by accident |
| `production` | `anthropic/claude-sonnet-5` | the analysis output shown to users |
| `premium` | `anthropic/claude-opus-5` | the final demo/polish pass only |

Switch tiers by editing `MODEL_TIER` in `.env` - no code changes needed. An
unrecognized tier name fails the request loudly (500 with the valid list)
rather than silently falling back to a different tier.

### Verify AI routing (Orbio)

Before building on top of the AI agent, confirm the gateway key actually
routes:

```bash
cd backend
source .venv/bin/activate
python scripts/test_ai_routing.py
```

This makes one chat-completion call with the OpenAI-compatible client,
pointed at `ANTHROPIC_BASE_URL` with `ANTHROPIC_AUTH_TOKEN` as the bearer
token, and prints the raw response. To try a different model, override it:
`TEST_MODEL="<slug>" python scripts/test_ai_routing.py`.

## 3. Frontend (React + Vite + Wagmi + RainbowKit)

```bash
cd frontend
npm install
cp .env.example .env   # add a WalletConnect project ID (cloud.walletconnect.com)
npm run dev
```

Opens on http://localhost:5173 with a wallet-connect button (RainbowKit) wired
to Wagmi. `src/viemClient.ts` sets up a viem public client for on-chain reads.

## Notes

- The backend's CORS config allows `http://localhost:5173` (the default Vite
  dev port) to call the API locally.
- `ANTHROPIC_API_KEY` takes precedence over `ANTHROPIC_AUTH_TOKEN` in
  Anthropic's own SDKs - this project intentionally keeps it empty and uses
  `ANTHROPIC_AUTH_TOKEN` for AI gateway routing.
