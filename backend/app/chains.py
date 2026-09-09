"""Supported chains for the /portfolio endpoint.

Matches the frontend's Wagmi config (chains: [mainnet, sepolia]).
"""

CHAINS = {
    1: {
        "name": "mainnet",
        "alchemy_subdomain": "eth-mainnet",
        # Fallback public RPC, used only when ALCHEMY_API_KEY is not set.
        "public_rpc": "https://ethereum-rpc.publicnode.com",
    },
    11155111: {
        "name": "sepolia",
        "alchemy_subdomain": "eth-sepolia",
        "public_rpc": "https://ethereum-sepolia-rpc.publicnode.com",
    },
}

# Used only by the public-RPC fallback path (no Alchemy key): Alchemy's
# alchemy_getTokenBalances auto-discovers every token a wallet has ever
# touched, but plain JSON-RPC has no such index, so the fallback can only
# check balances for a fixed list of well-known contracts. Mainnet-only for
# now - there's no single canonical set of Sepolia test tokens worth
# hardcoding, and guessing wrong contract addresses is worse than an empty
# list.
KNOWN_TOKENS = {
    1: [
        {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
        {"symbol": "USDT", "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
        {"symbol": "DAI", "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18},
        {"symbol": "WETH", "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "decimals": 18},
    ],
}
