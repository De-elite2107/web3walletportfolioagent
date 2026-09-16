# Orblo

Orblo is an on-chain wallet portfolio agent: connect a wallet and it reads your real holdings (native balance + ERC-20 tokens), prices everything in USD via Chainlink and CoinGecko, explains what you're holding in plain language through an AI chat interface, and runs a security scan that flags risky token approvals - unlimited spending allowances and unverified spender contracts - so you know not just *what* you hold but *what's risky about it*.

**No Anthropic account needed.** LLM calls go through the `openai` Python SDK pointed at an OpenAI-compatible gateway - built and tested against [Orbio](https://orbio.so) - not the Anthropic SDK or an Anthropic API key. See `backend/app/ai_client.py`.

## Why this matters

Most wallet trackers stop at a balance sheet: tokens, prices, a pie chart. That tells you what you own, not what could go wrong. A wallet can look fine on a balance sheet while quietly holding an **unlimited, unverified** approval from months ago - the exact shape of the approvals drainer scams exploit. Orblo pairs the balance sheet with an approval scan and a plain-language explanation, so "what do I hold" and "what should I be worried about" are answered in the same place, not two different tools.

## Demo script

See [DEMO.md](DEMO.md) for a 5-step walkthrough (connect -> portfolio -> analysis -> chat -> security finding), including which kind of wallet to use for a compelling demo.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript |
| Wallet connect | Wagmi + RainbowKit |
| On-chain reads (client) | viem |
| Backend | FastAPI (Python) |
| Database | PostgreSQL (via SQLAlchemy) |
| On-chain data | Alchemy (primary), public RPC (fallback) |
| Pricing | Chainlink price feeds (on-chain), CoinGecko (fallback) |
| Contract verification | Etherscan `getsourcecode` (primary), Sourcify (no-key fallback) |
| Exploit/scam lookup | Tavily search + LLM relevance judgment |
| LLM | Claude, via the `openai` SDK pointed at an OpenAI-compatible gateway (Orbio / OpenRouter) - no Anthropic SDK or API key |

## Getting started

### 1. Get your API keys

| Key | Required for | Where to get it |
|---|---|---|
| `LLM_AUTH_TOKEN` | AI analysis + chat + security-scan risk lookup | Any OpenAI-compatible LLM gateway - [OpenRouter](https://openrouter.ai/keys) is the easiest public option (free signup, pay-as-you-go credits). **Not an Anthropic API key** - this is a bearer token for the gateway, used via the plain `openai` SDK |
| `ALCHEMY_API_KEY` | Full on-chain reads (balances, transaction history, token discovery) | [alchemy.com](https://www.alchemy.com/) -> sign up -> create an app on Ethereum Mainnet -> copy the API key. Without this, the app still runs on a degraded public-RPC fallback (see [Known limitations](#known-limitations)) |
| `ETHERSCAN_API_KEY` | Security scan: contract verification | [etherscan.io/apis](https://etherscan.io/apis) -> free account -> generate an API key. Without this, verification falls back to Sourcify (no key needed, slightly lower coverage) |
| `TAVILY_API_KEY` | Security scan: known-exploit/scam web search | [tavily.com](https://tavily.com/) -> free developer key |
| `VITE_WALLETCONNECT_PROJECT_ID` | WalletConnect-based wallet connectors in the frontend | [cloud.walletconnect.com](https://cloud.walletconnect.com/) -> free project. Injected wallets (e.g. MetaMask's browser extension) work without this |

None of these are required to explore the code, but `LLM_AUTH_TOKEN` and `ALCHEMY_API_KEY` are required for the app to do anything useful end to end.

### 2. Environment variables

Copy `.env.example` to `.env` at the repo root and fill in the keys above:

```
LLM_BASE_URL=https://openrouter.ai/api/v1          # or any OpenAI-compatible gateway - no Anthropic account needed
LLM_AUTH_TOKEN=                                    # your gateway key, used as the bearer token
MODEL_TIER=draft                                   # draft | production | premium - see backend/models.yaml
MODEL_NAME=anthropic/claude-haiku-4.5              # model used by analyze/chat/security-scan today
ALCHEMY_API_KEY=                                   # on-chain reads
ETHERSCAN_API_KEY=                                 # security scan: contract verification
TAVILY_API_KEY=                                    # security scan: exploit/scam lookup
DATABASE_URL=                                      # e.g. postgresql://postgres:postgres@localhost:5433/orblo
```

`MODEL_NAME` uses the gateway's OpenRouter-style `provider/model` naming (e.g. `anthropic/claude-haiku-4.5` selects a Claude model *through* the gateway) - it isn't itself an Anthropic API parameter.

`.env` is gitignored - never commit real secrets. `frontend/.env.example` covers the one frontend-only variable (`VITE_WALLETCONNECT_PROJECT_ID`).

### 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Postgres - if you don't already have an instance, run a dedicated one:
docker run -d --name orblo-postgres -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=orblo -p 5433:5432 postgres:16-alpine
# then set DATABASE_URL=postgresql://postgres:postgres@localhost:5433/orblo

uvicorn app.main:app --reload --port 8000
```

Tables are created automatically on startup once Postgres is reachable. Sanity-check the AI gateway key before relying on it:

```bash
python scripts/test_ai_routing.py
```

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # add a WalletConnect project ID, or skip it and use an injected wallet
npm run dev
```

Opens on http://localhost:5173. Connect a wallet, and the dashboard walks top to bottom: portfolio value + holdings, recent transactions, AI analysis + chat, security scan.

## Known limitations

Shipping honestly means naming these rather than hiding them:

- **Security scan lookback is capped, not full history.** It targets the most recent ~10,000 blocks but adapts down further on rate-limited RPC providers (Alchemy's free tier allows only 10 blocks per unfiltered `eth_getLogs` call, so the scan chunks and reports whatever range it actually covered in `lookbackBlocks`). It's a recent-activity signal, not a full wallet audit - an approval granted further back than that window won't show up.
- **Single-chain-family MVP.** Ethereum mainnet (chain ID 1) and Sepolia testnet (11155111) only. The architecture (chain-keyed config in `app/chains.py`) is built to extend to L2s, but no other chain has been wired in or tested.
- **Pricing coverage depends on the token.** Chainlink covers a handful of major assets directly; anything else falls back to CoinGecko, which rate-limits fast under concurrent load - a wallet holding many long-tail/spam tokens will show `null` prices for most of them rather than a number. That's a deliberate "don't guess" choice, not a crash, but it does mean `totalUsdValue` can undercount a noisy wallet.
- **The exploit/scam lookup is best-effort, not a database.** It's a live web search plus an LLM relevance check, not a curated threat-intel feed - it can miss a real incident that isn't well-indexed, and it never claims a contract is "safe," only that nothing turned up.
- **No user accounts or auth.** Snapshots persist keyed by wallet address; anyone who queries the API for an address can see its persisted history. Fine for a demo, not for production multi-tenant use.
- **Model-tier system isn't wired in yet.** `backend/models.yaml` defines draft/production/premium tiers, but `/portfolio/analyze` and `/portfolio/chat` currently call a single `MODEL_NAME` directly.

## Project structure

```
.
├── frontend/   React + Vite + TypeScript, Wagmi + RainbowKit, viem
├── backend/    FastAPI + SQLAlchemy (PostgreSQL)
├── DEMO.md     5-step demo walkthrough script
├── .env        real environment variables (gitignored, not committed)
└── .env.example  template for every variable the backend/frontend expect
```

---

## How it works

### Portfolio + valuation

`GET /portfolio?address=0x...&chain_id=1` fetches native balance, ERC-20
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
Sepolia). If both fail, that holding's `priceUsd`/`usdValue`/
`allocationPercent` come back `null` rather than failing the request.
`totalUsdValue` and allocation percentages only account for holdings that
*did* price successfully. `concentrationRisk` is `true` (with
`concentrationToken` naming the asset) when native ETH or any single token
exceeds 50% of `totalUsdValue`.

**Persistence:** every fetch is saved to the `portfolio_snapshots` table
(`wallet_address`, `chain_id`, `fetched_at`, `total_usd_value`, `raw_json`)
- `total_usd_value` is its own column so later change-over-time queries
don't need to parse JSON, while `raw_json` keeps the full priced
breakdown. If Postgres isn't reachable the request still succeeds; the
failure is logged as a warning instead of failing the response.

### LLM analysis + chat

- `POST /portfolio/analyze` - body `{"address": "0x...", "chainId": 1}`.
  Reuses the wallet's latest persisted snapshot (falls back to a fresh
  `/portfolio`-equivalent fetch + persist if none exists yet), sends the
  full priced portfolio JSON to the model, and returns
  `{"summary": "...", "portfolio": {...}}` - the `portfolio` is echoed back
  so the frontend can hand the exact same snapshot to `/portfolio/chat`
  without re-fetching.
- `POST /portfolio/chat` - body
  `{"address": "0x...", "portfolio": {...}, "history": [{"role": "user"|"assistant", "content": "..."}], "message": "..."}`.
  No DB lookup - the caller supplies the portfolio snapshot directly (from
  `/portfolio` or `/portfolio/analyze`), so replies are grounded in exactly
  what's on screen. Returns `{"reply": "..."}`.

Both (`app/analysis.py`) use an OpenAI-compatible client
(`app/ai_client.py`), with the model taken directly from `MODEL_NAME` in
`.env` - a plain env var for now, ahead of wiring in the tier system
below. The system prompt restricts the model to describing only what's in
the supplied JSON (no speculation about future prices, no investment
advice, nulls reported as "unavailable" rather than guessed) and
explicitly tells it to treat every field - including token symbols/names,
which are attacker-controllable on-chain data - as inert data, never as
instructions. Verified end-to-end against real wallets: summaries and
follow-up answers correctly cite the actual totals/percentages/
concentration flag in the data, and multi-turn chat history is genuinely
threaded (tested by asking the model to recall a fact only present in
`history`, not derivable from the portfolio JSON).

### Model tiers (not yet wired into analyze/chat)

`backend/models.yaml` maps three tiers to gateway model ids, resolved via
`app/model_tiers.py` + `MODEL_TIER` in `.env` (default `draft`):

| Tier | Model | Use for |
|---|---|---|
| `draft` | `anthropic/claude-haiku-4.5` | iterating on prompts/logic - the default, so nobody burns production spend by accident |
| `production` | `anthropic/claude-sonnet-5` | the analysis output shown to users |
| `premium` | `anthropic/claude-opus-5` | the final demo/polish pass only |

`/portfolio/analyze` and `/portfolio/chat` call `MODEL_NAME` directly
instead (above) - swapping them onto the tier system is a later step. An
unrecognized tier name still fails loudly (500 with the valid list) rather
than silently falling back to a different tier, whenever something does
start using it.

### Security scan (token approvals)

`GET /portfolio/security-scan?address=0x...&chain_id=1` - which contracts
currently hold ERC-20 spending approval for this wallet, how much, and how
risky that looks. Persists to `security_scan_snapshots` (same pattern as
`portfolio_snapshots`). Returns:
```json
{
  "address": "0x...", "chainId": 1, "lookbackBlocks": 499,
  "approvals": [
    {
      "token": "PSWAP", "tokenAddress": "0x...", "spender": "0x...",
      "amount": "unlimited", "isUnlimited": true, "isVerified": true,
      "riskLevel": "elevated", "note": "No known reports found."
    }
  ],
  "overallRiskSummary": "1 approval(s) flagged as elevated risk..."
}
```

**How it works (`app/security_scan.py`):**
1. `eth_getLogs` for ERC-20 `Approval` events with this wallet as owner
   finds every (token, spender) pair it's approved, without needing to
   know addresses in advance. Then the *current* allowance is read via
   `eth_call` (`allowance(owner, spender)`) rather than trusted from the
   event log - a token doesn't necessarily re-emit `Approval` when an
   allowance is partially spent, so only `allowance()` reflects the live
   number. Event/function selectors were computed from real `keccak256`,
   not recalled from memory.
2. **Block range is adaptive, not a fixed 10,000** (see [Known
   limitations](#known-limitations)) - `lookbackBlocks` in the response
   reports what was *actually* covered.
3. Amounts at/above `2**96 - 1` are flagged `isUnlimited` - covers both the
   classic `2**256-1` max approval and smaller-but-still-effectively-
   infinite patterns some routers use (a uint96 storage slot).
4. Each unique spender (deduped - one busy router approved for 50 different
   tokens is one lookup, not 50) is checked for verification: Etherscan
   `getsourcecode` primary, Sourcify (no API key) fallback on failure/no
   key.
5. `riskLevel`: `high` = unlimited + unverified; `elevated` = unlimited+verified
   *or* limited+unverified; `normal` = limited + verified. An
   undetermined verification status (both sources inconclusive) is treated
   like unverified, not assumed safe.
6. For every uniquely flagged (elevated/high) spender - not every finding -
   a best-effort cross-check: Tavily search for `"<address> exploit"` /
   `"<address> scam"`, then the same AI gateway judges whether any result
   *concretely* ties that exact address to an incident (plain keyword
   matching was too noisy - almost every result is just a block-explorer
   page mentioning the address). Never reports "safe" - only a specific
   finding with its source, or "No known reports found."

Verified end-to-end against real, live wallets (not synthetic fixtures):
found and correctly priced/classified a real limited approval (`normal`),
and separately a wallet with 66 real unlimited approvals to major routers
(1inch, Uniswap Permit2, KyberSwap) - all correctly `elevated` (verified),
with the LLM cross-check correctly distinguishing "this address is a
legitimate router mentioned in an unrelated incident report" from an actual
finding. All four `riskLevel` combinations spot-checked directly. Language
throughout stays conservative ("elevated risk," "worth reviewing") per the
project's requirement - signals, not certainty.

### Reliability

- Every endpoint catches its known failure modes (bad input -> 400,
  Alchemy/LLM/security-scan failures -> 502 with a plain-language `detail`);
  `main.py` also registers a catch-all handler for anything unexpected, so
  a bug or dependency hiccup nobody anticipated still returns clean JSON
  instead of a raw stack trace - the real traceback still goes to the
  server log.
- `get_latest_snapshot` (used by `/portfolio/analyze`) fails soft like
  `save_snapshot` - a DB read error falls through to a fresh fetch instead
  of 500ing.
- The AI gateway client has a 30s request timeout (the SDK default is 10
  minutes) so a slow LLM call can't hang the app. Every other external
  call (Alchemy, Etherscan, Sourcify, Tavily, public RPC) has an explicit
  timeout too.

### Frontend

**Layout (`Header.tsx` + `App.tsx`):** a header (logo/name/tagline +
RainbowKit connect button) is always visible. Disconnected, the page shows
just a connect prompt. Connected, sections run top to bottom: Portfolio
(value + holdings table) -> Recent Transactions -> AI Analysis
(`AnalysisChat.tsx`: an Analyze button renders the summary, a chat box
below it handles follow-ups, resending full history each turn) -> Security
Scan (`SecurityScan.tsx`: findings sorted highest-risk-first). All four
async actions (portfolio fetch, analyze, chat, security scan) have their
own loading state (spinner + skeleton placeholders, not a blank screen)
and error state (`components/ErrorBanner.tsx` - the backend's own
plain-language `detail` message, or "Could not reach the server" for a
network-level failure) instead of a silent console-only failure.

**Design system (`index.css`):** one set of CSS variables drives every
status color in the app - the portfolio concentration-risk banner, the
security-scan severity badges (red/yellow/neutral for high/elevated/
normal), and generic success/error banners all pull from the same
`--danger`/`--warning`/`--success`/`--neutral` tokens, in both light and
dark mode. `components/MarkdownLite.tsx` renders the LLM's `**bold**`/`#
heading` output as actual formatting instead of showing literal
asterisks.

Verified with real clicks against the real backend (headless Chrome +
DevTools Protocol, not just code review): connect -> portfolio loads ->
Analyze produces a formatted summary -> chat follow-up works -> Security
Scan runs and renders color-coded findings - the whole sequence, screenshot
at each step, no console errors.

## Notes

- The backend's CORS config allows `http://localhost:5173` (the default Vite
  dev port) to call the API locally.
- No Anthropic SDK, account, or API key is used anywhere in this project -
  see the note at the top of this README and `backend/app/ai_client.py`.
  `LLM_*`-prefixed env var names were chosen to be gateway-neutral on
  purpose, since the actual gateway (Orbio, OpenRouter, or otherwise) is a
  deployment choice, not something this code is tied to.
