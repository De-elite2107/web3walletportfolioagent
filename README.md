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
- `GET /portfolio?address=0x...` - placeholder; returns a stub shape the
  frontend can build against until on-chain reads + security analysis are
  wired in.

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
