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

# Postgres: this machine's system-wide instance on port 5432 belongs to
# other, unrelated projects (no credentials for it) - this project runs its
# own dedicated container instead:
#   docker run -d --name orblo-postgres -e POSTGRES_USER=postgres \
#     -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=orblo -p 5433:5432 postgres:16-alpine
# DATABASE_URL in .env already points at it (localhost:5433). Tables are
# created automatically on startup once it can connect.

uvicorn app.main:app --reload --port 8000
```

- `GET /health` - liveness check, doesn't touch the database.
- `GET /portfolio?address=0x...&chain_id=1` - fetches native balance, ERC-20
  balances, prices everything in USD, and the 20 most recent transactions
  for a wallet, persists the snapshot to Postgres, and returns:
  ```json
  {
    "address": "0x...",
    "chainId": 1,
    "nativeBalance": "6.7121...",
    "nativePriceUsd": "2495.3602",
    "nativeUsdValue": "16749.23...",
    "nativeAllocationPercent": 80.8,
    "tokens": [
      {
        "symbol": "USDC", "contractAddress": "0x...", "balance": "37.19",
        "priceUsd": "0.9998", "usdValue": "37.18", "allocationPercent": 0.18
      }
    ],
    "recentTransactions": [{"hash": "0x...", "from": "0x...", "to": "0x...", "value": 1.5, "timestamp": "2026-..."}],
    "totalUsdValue": "20729.27...",
    "concentrationRisk": true,
    "concentrationToken": "ETH",
    "source": "alchemy"
  }
  ```
  `chain_id` defaults to 1 (mainnet); 11155111 (sepolia) is also supported.
  No LLM analysis or chat interface yet - that's a later step.

  **Data source:** uses Alchemy (`alchemy_getTokenBalances` /
  `alchemy_getTokenMetadata` / `alchemy_getAssetTransfers`) when
  `ALCHEMY_API_KEY` is set (`source: "alchemy"`). Without a key, it falls
  back to a public RPC (`source: "public_rpc"`) with two limitations: only
  a fixed list of well-known mainnet tokens is checked (USDC/USDT/DAI/WETH -
  see `backend/app/chains.py`, no fallback list for Sepolia), and
  `recentTransactions` always comes back empty, since plain JSON-RPC has no
  address-activity index to query.

  **Pricing (`app/pricing.py`, `app/valuation.py`):** Chainlink price feeds
  first - read on-chain via `eth_call` against `AggregatorV3Interface`
  (`decimals()` + `latestRoundData()`), no ABI library needed for just those
  two selectors. Feed addresses are hardcoded per chain/symbol and were
  verified on-chain (sane `decimals()`/price) before being committed - see
  `CHAINLINK_FEEDS` in `app/pricing.py`. Tokens without a mapped feed fall
  back to CoinGecko's free API (mainnet only - CoinGecko doesn't track
  Sepolia). If both fail (no feed *and* no CoinGecko listing, or CoinGecko
  rate-limits you - it will, on a wallet holding many long-tail tokens),
  that holding's `priceUsd`/`usdValue`/`allocationPercent` come back `null`
  rather than failing the request. `totalUsdValue` and allocation percentages
  only account for holdings that *did* price successfully.
  `concentrationRisk` is `true` (with `concentrationToken` naming the asset)
  when native ETH or any single token exceeds 50% of `totalUsdValue`.

  **Persistence:** every fetch is saved to the `portfolio_snapshots` table
  (`wallet_address`, `chain_id`, `fetched_at`, `total_usd_value`, `raw_json`)
  - `total_usd_value` is its own column so later change-over-time queries
  don't need to parse JSON, while `raw_json` keeps the full priced
  breakdown. Just storage for now, no change-over-time view built on it
  yet. If Postgres isn't reachable the request still succeeds; the failure
  is logged as a warning instead of failing the response.

### Model tiers (for the upcoming AI analysis step)

`backend/models.yaml` maps three tiers to gateway model ids, resolved via
`app/model_tiers.py` + `MODEL_TIER` in `.env` (default `draft`):

| Tier | Model | Use for |
|---|---|---|
| `draft` | `anthropic/claude-haiku-4.5` | iterating on prompts/logic - the default, so nobody burns production spend by accident |
| `production` | `anthropic/claude-sonnet-5` | the analysis output shown to users |
| `premium` | `anthropic/claude-opus-5` | the final demo/polish pass only |

**Not currently called by `/portfolio`** - that endpoint now does real
on-chain data fetching (below) instead of the earlier placeholder AI call,
so nothing in the request path spends AI-gateway tokens today. The tier
config + `app/ai_client.py` are ready for the actual security-analysis step
to call once that's built. An unrecognized tier name fails loudly (500 with
the valid list) rather than silently falling back to a different tier.

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
