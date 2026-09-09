import { createPublicClient, http } from 'viem'
import { mainnet } from 'viem/chains'

// Client-side on-chain reads via viem.
//
// Security note: ALCHEMY_API_KEY in the root .env is a *backend* secret and
// is intentionally not exposed here. If you want the frontend to hit Alchemy
// directly (instead of routing on-chain reads through the backend), set
// VITE_ALCHEMY_API_KEY in frontend/.env - anything prefixed VITE_ is bundled
// into client-side JS and visible to anyone using the app, so only use a
// key that's safe to expose publicly (e.g. one restricted by domain in the
// Alchemy dashboard). Otherwise this falls back to viem's default public
// RPC transport.
const alchemyKey = import.meta.env.VITE_ALCHEMY_API_KEY

export const publicClient = createPublicClient({
  chain: mainnet,
  transport: alchemyKey
    ? http(`https://eth-mainnet.g.alchemy.com/v2/${alchemyKey}`)
    : http(),
})
