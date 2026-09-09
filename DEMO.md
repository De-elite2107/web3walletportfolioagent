# Demo script

A 5-step walkthrough for a live or recorded demo. Total time: ~3-4 minutes,
mostly waiting on the security scan (it can take up to a minute - see
[Known limitations](README.md#known-limitations)).

## Before you start: pick the right wallet

**Use a wallet with an existing unlimited token approval, not a clean one.**
A security scan that comes back "nothing found" is a weak demo - it proves
the feature runs, not that it's useful. If you don't have a wallet you know
has flagged approvals, connect one that's used a DEX or aggregator (1inch,
Uniswap, KyberSwap) in the last day or so - "approve unlimited spending" is
the default UX on most of those, so an active DeFi wallet almost always has
at least one `elevated`-risk finding to show.

If you don't have one handy, `0x74de5d4fcbf63e00296fd95d33236b9794016631`
is a real, public mainnet wallet (verified during development) with dozens
of active unlimited approvals to well-known routers - safe to reference
since it's read-only (no private key involved) and its data is already
public on any block explorer. The app currently only shows the *connected*
wallet's data (no manual address-lookup field), so to actually demo with an
address you don't hold keys for, connect via a wallet extension that
supports watch-only/read-only addresses (e.g. Rabby Wallet's "Add
contacts" -> watch mode) rather than a standard MetaMask connection. If
that's not set up in time, calling the backend directly is a fine fallback
for just this one step:
```
curl "http://localhost:8000/portfolio/security-scan?address=0x74de5d4fcbf63e00296fd95d33236b9794016631&chain_id=1"
```

## The 5 steps

**1. Connect wallet.** Load the app, click **Connect Wallet** in the
header, approve in your wallet extension. Say: *"This reads your wallet
directly on-chain - no signup, no data collection beyond what's already
public."*

**2. Show portfolio value.** Once connected, the Portfolio section loads:
total USD value up top, then a holdings table (native ETH + every ERC-20
token, each priced via Chainlink or CoinGecko). If the wallet is
concentrated in one asset, point out the yellow concentration-risk banner
above the table. Say: *"Every balance and price here is a live on-chain
read, not cached or estimated."*

**3. Show the analysis summary.** Scroll to **AI Analysis**, click **Run
Analysis**. While it loads (a few seconds), say what's happening: *"This
sends the priced portfolio data to an LLM with a strict prompt - describe
only what's in the data, no investment advice, no speculation."* When it
returns, point out that the summary correctly cites the actual numbers
(total value, concentration percentage) - not generic boilerplate.

**4. Ask one chat question.** In the follow-up box below the summary, ask
something concrete: *"Why is my [asset] allocation so high?"* or *"What's
my biggest holding?"* The reply should reference the specific number from
the data. Say: *"This isn't a separate chatbot - it's grounded in the exact
snapshot you're looking at, including the conversation history."*

**5. Show a flagged security finding.** Scroll to **Security Scan**, click
**Run Security Scan** (mention it can take up to a minute - it's doing a
real on-chain log scan plus a live web search per flagged contract, not a
cached lookup). When results land, point at a `high` or `elevated` badge:
name the spender, the amount ("unlimited"), and read the note - especially
if it's a case where the model correctly distinguished a legitimate router
from an actual incident report. Close with: *"This is the part a plain
balance-sheet wallet tracker doesn't do - it doesn't just show you what you
hold, it tells you what's worth reviewing about it."*
