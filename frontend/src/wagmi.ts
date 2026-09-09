import { getDefaultConfig } from '@rainbow-me/rainbowkit'
import { mainnet, sepolia } from 'wagmi/chains'

// Public WalletConnect Cloud project ID used by RainbowKit's connect modal.
// Get your own at https://cloud.walletconnect.com and set it here or via
// VITE_WALLETCONNECT_PROJECT_ID in frontend/.env for production use.
const walletConnectProjectId =
  import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'YOUR_WALLETCONNECT_PROJECT_ID'

export const config = getDefaultConfig({
  appName: 'Orblo',
  projectId: walletConnectProjectId,
  chains: [mainnet, sepolia],
  ssr: false,
})
