import { useEffect, useState } from 'react'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount, useChainId } from 'wagmi'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface Token {
  symbol: string
  contractAddress: string
  balance: string
}

interface Transaction {
  hash: string
  from: string
  to: string
  value: number | string
  timestamp: string
}

interface PortfolioResponse {
  address: string
  chainId: number
  nativeBalance: string
  tokens: Token[]
  recentTransactions: Transaction[]
  source?: string
}

function App() {
  const { address, isConnected, chain } = useAccount()
  const chainId = useChainId()

  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isConnected || !address) {
      setPortfolio(null)
      setError(null)
      return
    }

    const controller = new AbortController()
    setLoading(true)
    setError(null)

    fetch(`${API_BASE_URL}/portfolio?address=${address}&chain_id=${chainId}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail || `Request failed with status ${res.status}`)
        }
        return res.json() as Promise<PortfolioResponse>
      })
      .then(setPortfolio)
      .catch((err: Error) => {
        if (err.name !== 'AbortError') setError(err.message)
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [isConnected, address, chainId])

  return (
    <div className="app">
      <header className="app-header">
        <ConnectButton />
        <h1>Orblo</h1>
        <p>Wallet portfolio &amp; security analysis</p>
      </header>

      <main>
        {!isConnected && <p>Connect a wallet to view your portfolio.</p>}

        {isConnected && (
          <div>
            <p>
              Connected as <code>{address}</code> on{' '}
              <strong>{chain?.name ?? `chain ${chainId}`}</strong>
            </p>

            {loading && <p>Loading portfolio…</p>}
            {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}

            {portfolio && (
              <table cellPadding={6} style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #ccc' }}>
                <tbody>
                  {Object.entries(portfolio).map(([key, value]) => (
                    <tr key={key} style={{ border: '1px solid #ccc' }}>
                      <td style={{ border: '1px solid #ccc', verticalAlign: 'top' }}>
                        <strong>{key}</strong>
                      </td>
                      <td style={{ border: '1px solid #ccc' }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                          {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                        </pre>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
