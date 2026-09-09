"""Token-approval security scan: which contracts currently hold spending
approval over a wallet's ERC-20 tokens, how much, and how risky that looks.

Approach:
1. eth_getLogs for ERC-20 Approval events with this wallet as owner, over
   the most recent LOOKBACK_BLOCKS blocks - finds every (token, spender)
   pair the wallet has recently approved, without needing to know
   token/spender addresses in advance. Capped rather than full history:
   large public RPCs rate-limit/reject wide eth_getLogs ranges, and this
   scan is framed as covering "recent activity," not a full audit.
2. For each unique pair, read the *current* allowance via eth_call
   (allowance(owner, spender)) rather than trusting the event's logged
   value - a token doesn't necessarily emit a new Approval event when an
   allowance is partially spent, so only allowance() reflects the live
   number.
3. For each spender with a nonzero current allowance: is the amount at/near
   uint256 max ("unlimited")? Is the spender contract verified (source
   published)? Combine into a conservative riskLevel, and for anything
   flagged elevated/high, do a best-effort exploit/scam cross-check
   (app/risk_lookup.py).

Event/function selectors below were computed from real keccak256, not
recalled from memory - see the project's dev notes.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import verification
from app.alchemy_client import get_token_metadata
from app.chains import CHAINS
from app.config import settings
from app.models import SecurityScanSnapshot
from app.risk_lookup import check_known_risk

logger = logging.getLogger("orblo.security_scan")

APPROVAL_TOPIC = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"  # Approval(address,address,uint256)
_ALLOWANCE_SELECTOR = "0xdd62ed3e"  # allowance(address,address)
_SYMBOL_SELECTOR = "0x95d89b41"  # symbol()
_DECIMALS_SELECTOR = "0x313ce567"  # decimals()

LOOKBACK_BLOCKS = 10_000

# If a single eth_getLogs call across LOOKBACK_BLOCKS is rejected for
# spanning too many blocks (common on rate-limited/free-tier RPC providers -
# Alchemy's free tier allows just 10 blocks per unfiltered call), chunk
# backwards from the latest block instead, capped to this many calls so a
# tightly-limited provider doesn't turn one scan into hundreds of
# round-trips. The scan reports whatever range it actually covered.
_MAX_LOG_CHUNKS = 50
_RANGE_LIMIT_RE = re.compile(r"up to a[n]? (\d+) block range", re.IGNORECASE)

# Any allowance at or above this is treated as "unlimited" - covers both the
# classic 2**256-1 max approval and smaller-but-still-effectively-infinite
# patterns (e.g. some routers store approvals in a uint96 slot for gas
# savings, so they max out at 2**96-1 instead).
UNLIMITED_THRESHOLD = 2**96 - 1


def _rpc_url(chain_id: int) -> str:
    if settings.alchemy_api_key:
        return f"https://{CHAINS[chain_id]['alchemy_subdomain']}.g.alchemy.com/v2/{settings.alchemy_api_key}"
    return CHAINS[chain_id]["public_rpc"]


def _rpc_call(url: str, method: str, params: list, request_id: int = 1):
    resp = httpx.post(url, json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}, timeout=20)
    # Some providers (Alchemy included) return a validation error - e.g. the
    # eth_getLogs block-range limit - as an actual HTTP 400 with the JSON-RPC
    # error envelope as the body, rather than HTTP 200 + an "error" field.
    # Try to parse the error out of the body before falling back to a raw
    # HTTP status exception.
    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()
        raise
    if "error" in data:
        raise RuntimeError(f"RPC error calling {method}: {data['error']}")
    resp.raise_for_status()
    return data["result"]


def _rpc_batch(url: str, calls: list[tuple[str, list]]) -> list[dict]:
    body = [{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]
    resp = httpx.post(url, json=body, timeout=25)
    resp.raise_for_status()
    results = resp.json()
    results.sort(key=lambda r: r["id"])
    return results


def _pad_address(address: str) -> str:
    return address[2:].lower().rjust(64, "0")


def _decode_string_return(hex_data: str) -> str | None:
    """Best-effort decode of a `string` eth_call return. Handles the
    standard ABI-encoded dynamic string; falls back to a legacy fixed
    bytes32 return (used by a few old tokens) if that layout doesn't parse.
    """
    try:
        raw = bytes.fromhex(hex_data[2:])
        if len(raw) >= 64:
            offset = int.from_bytes(raw[:32], "big")
            length = int.from_bytes(raw[offset : offset + 32], "big")
            decoded = raw[offset + 32 : offset + 32 + length].decode("utf-8", errors="strict").strip("\x00")
            if decoded:
                return decoded
        decoded = raw.rstrip(b"\x00").decode("utf-8", errors="strict")
        return decoded or None
    except Exception:  # noqa: BLE001 - display-only, never worth failing the scan over
        return None


def _dedupe_pairs(logs: list[dict]) -> list[tuple[str, str]]:
    pairs: dict[tuple[str, str], tuple[str, str]] = {}
    for log in logs:
        token, spender = log["address"], "0x" + log["topics"][2][-40:]
        pairs[(token.lower(), spender.lower())] = (token, spender)
    return list(pairs.values())


def _find_approval_pairs(url: str, owner: str) -> tuple[list[tuple[str, str]], int]:
    """Unique (token, spender) pairs from recent Approval logs where `owner`
    is the approving wallet. Returns (pairs, blocks_actually_covered) - the
    latter can be less than LOOKBACK_BLOCKS if the provider limits how many
    blocks one eth_getLogs call can span (see _MAX_LOG_CHUNKS above).
    """
    latest = int(_rpc_call(url, "eth_blockNumber", []), 16)
    from_block = max(latest - LOOKBACK_BLOCKS, 0)
    topics = [APPROVAL_TOPIC, "0x" + _pad_address(owner)]

    try:
        logs = _rpc_call(url, "eth_getLogs", [{"fromBlock": hex(from_block), "toBlock": "latest", "topics": topics}])
        return _dedupe_pairs(logs), latest - from_block
    except RuntimeError as e:
        match = _RANGE_LIMIT_RE.search(str(e))
        if not match:
            raise
        chunk_size = int(match.group(1))
        logger.info("eth_getLogs range-limited to %d blocks/call - falling back to chunked queries", chunk_size)

    calls = []
    block = latest
    while block >= from_block and len(calls) < _MAX_LOG_CHUNKS:
        chunk_from = max(block - chunk_size + 1, from_block)
        calls.append(("eth_getLogs", [{"fromBlock": hex(chunk_from), "toBlock": hex(block), "topics": topics}]))
        block = chunk_from - 1

    results = _rpc_batch(url, calls)
    logs = [log for r in results for log in (r.get("result") or [])]
    blocks_covered = latest - max(block + 1, from_block)
    return _dedupe_pairs(logs), blocks_covered


def _current_allowances(url: str, owner: str, pairs: list[tuple[str, str]]) -> list[dict]:
    """Live allowance() for each pair, nonzero only - the log only tells us
    a pair was *ever* approved, not what's still approved now.
    """
    if not pairs:
        return []
    calls = [
        ("eth_call", [{"to": token, "data": _ALLOWANCE_SELECTOR + _pad_address(owner) + _pad_address(spender)}, "latest"])
        for token, spender in pairs
    ]
    results = _rpc_batch(url, calls)

    approvals = []
    for (token, spender), result in zip(pairs, results):
        raw = result.get("result")
        if not raw or raw == "0x":
            continue
        amount = int(raw, 16)
        if amount > 0:
            approvals.append({"token": token, "spender": spender, "amount": amount})
    return approvals


def _token_symbols(chain_id: int, url: str, token_addresses: list[str]) -> dict[str, dict]:
    """{address: {"symbol":..., "decimals":...}} - via Alchemy if configured
    (one batched call), else individual eth_calls against each token.
    """
    if settings.alchemy_api_key:
        return get_token_metadata(chain_id, settings.alchemy_api_key, token_addresses)

    calls = []
    for addr in token_addresses:
        calls.append(("eth_call", [{"to": addr, "data": _SYMBOL_SELECTOR}, "latest"]))
        calls.append(("eth_call", [{"to": addr, "data": _DECIMALS_SELECTOR}, "latest"]))
    results = _rpc_batch(url, calls)

    metadata = {}
    for i, addr in enumerate(token_addresses):
        symbol_result, decimals_result = results[2 * i], results[2 * i + 1]
        symbol = _decode_string_return(symbol_result["result"]) if symbol_result.get("result") else None
        try:
            decimals = int(decimals_result["result"], 16) if decimals_result.get("result") else None
        except ValueError:
            decimals = None
        metadata[addr] = {"symbol": symbol, "decimals": decimals}
    return metadata


def _risk_level(is_unlimited: bool, is_verified: bool | None) -> str:
    if is_unlimited and not is_verified:
        return "high"
    if is_unlimited or not is_verified:
        return "elevated"
    return "normal"


def run_security_scan(chain_id: int, address: str) -> dict:
    url = _rpc_url(chain_id)

    pairs, blocks_covered = _find_approval_pairs(url, address)
    raw_approvals = _current_allowances(url, address, pairs)

    if not raw_approvals:
        return {
            "address": address,
            "chainId": chain_id,
            "lookbackBlocks": blocks_covered,
            "approvals": [],
            "overallRiskSummary": (
                f"No active token approvals found in the most recent {blocks_covered:,} blocks "
                "(recent activity only, not full wallet history)."
            ),
        }

    token_metadata = _token_symbols(chain_id, url, list({a["token"] for a in raw_approvals}))

    # Dedupe by spender before firing off verification checks - a wallet
    # that's approved the same router (1inch, Permit2, ...) for many
    # different tokens should trigger one Etherscan/Sourcify lookup for
    # that spender, not one per approval.
    unique_spenders = list({a["spender"] for a in raw_approvals})
    with ThreadPoolExecutor(max_workers=max(len(unique_spenders), 1)) as pool:
        verify_futures = {
            spender: pool.submit(verification.is_verified, chain_id, spender, settings.etherscan_api_key)
            for spender in unique_spenders
        }
        verify_results = {spender: f.result() for spender, f in verify_futures.items()}

    findings = []
    for a in raw_approvals:
        is_unlimited = a["amount"] >= UNLIMITED_THRESHOLD
        is_verified = verify_results.get(a["spender"])
        risk_level = _risk_level(is_unlimited, is_verified)

        meta = token_metadata.get(a["token"], {})
        decimals = meta.get("decimals")
        symbol = meta.get("symbol") or a["token"]
        amount_str = str(Decimal(a["amount"]) / (Decimal(10) ** decimals)) if decimals is not None else str(a["amount"])

        findings.append(
            {
                "token": symbol,
                "tokenAddress": a["token"],
                "spender": a["spender"],
                "amount": "unlimited" if is_unlimited else amount_str,
                "isUnlimited": is_unlimited,
                "isVerified": is_verified,
                "riskLevel": risk_level,
                "note": None,  # filled in below for flagged findings only
            }
        )

    # Known-risk cross-check is best-effort and costs a search + LLM call -
    # only run it for what's already flagged elevated/high, and only once
    # per unique spender (same dedup reasoning as verification above).
    flagged = [f for f in findings if f["riskLevel"] != "normal"]
    unique_flagged_spenders = list({f["spender"] for f in flagged})
    if unique_flagged_spenders:
        with ThreadPoolExecutor(max_workers=max(len(unique_flagged_spenders), 1)) as pool:
            note_futures = {spender: pool.submit(check_known_risk, spender) for spender in unique_flagged_spenders}
            notes_by_spender = {spender: f.result() for spender, f in note_futures.items()}
        for f in flagged:
            f["note"] = notes_by_spender[f["spender"]]

    for f in findings:
        if f["note"] is None:
            f["note"] = "Standard approval - no elevated-risk signals."

    risk_order = {"high": 0, "elevated": 1, "normal": 2}
    findings.sort(key=lambda f: risk_order[f["riskLevel"]])

    high_count = sum(1 for f in findings if f["riskLevel"] == "high")
    elevated_count = sum(1 for f in findings if f["riskLevel"] == "elevated")

    if high_count:
        high_spenders = ", ".join(f["spender"] for f in findings if f["riskLevel"] == "high")
        summary = (
            f"{high_count} approval(s) worth reviewing closely: unverified contract(s) ({high_spenders}) "
            f"hold unlimited spending approval. {elevated_count} additional approval(s) flagged as elevated risk."
        )
    elif elevated_count:
        summary = f"{elevated_count} approval(s) flagged as elevated risk (unlimited approval to a verified contract, or approval to an unverified contract) - worth reviewing."
    else:
        summary = f"{len(findings)} active approval(s) found, none flagged - all are limited-amount approvals to verified contracts."

    return {
        "address": address,
        "chainId": chain_id,
        "lookbackBlocks": blocks_covered,
        "approvals": findings,
        "overallRiskSummary": summary,
    }


def save_scan(db: Session, wallet_address: str, chain_id: int, raw_json: dict) -> None:
    """Persist a scan result. Fails soft, same as portfolio.save_snapshot -
    logs and returns on any DB error rather than failing the request.
    """
    try:
        db.add(SecurityScanSnapshot(wallet_address=wallet_address, chain_id=chain_id, raw_json=raw_json))
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning("failed to persist security scan for %s on chain %s: %s", wallet_address, chain_id, e)
