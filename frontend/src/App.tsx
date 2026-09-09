import { useEffect, useState } from 'react'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount, useChainId } from 'wagmi'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface Token {
  symbol: string
  contractAddress: string
  balance: string
  priceUsd: string | null
  usdValue: string | null
  allocationPercent: number | null
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
  nativePriceUsd: string | null
  nativeUsdValue: string | null
  nativeAllocationPercent: number | null
  tokens: Token[]
  recentTransactions: Transaction[]
  totalUsdValue: string
  concentrationRisk: boolean
  concentrationToken: string | null
  source?: string
}

function formatUsd(value: string | null): string {
  if (value === null) return '—'
  const n = Number(value)
  return Number.isFinite(n) ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'
}

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${value}%`
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
              <>
                {portfolio.concentrationRisk && (
                  <div
                    style={{
                      background: '#fff3cd',
                      border: '1px solid #e0a800',
                      color: '#664d03',
                      padding: '0.75rem 1rem',
                      borderRadius: 4,
                      marginBottom: '1rem',
                      textAlign: 'left',
                    }}
                  >
                    ⚠️ Concentration risk: <strong>{portfolio.concentrationToken}</strong> makes up more
                    than 50% of this wallet's total value.
                  </div>
                )}

                <div style={{ margin: '1rem 0' }}>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>Total portfolio value</div>
                  <div style={{ fontSize: '2rem', fontWeight: 700 }}>{formatUsd(portfolio.totalUsdValue)}</div>
                </div>

                <table cellPadding={6} style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #ccc' }}>
                  <thead>
                    <tr style={{ border: '1px solid #ccc', textAlign: 'left' }}>
                      <th style={{ border: '1px solid #ccc' }}>Asset</th>
                      <th style={{ border: '1px solid #ccc' }}>Balance</th>
                      <th style={{ border: '1px solid #ccc' }}>Price (USD)</th>
                      <th style={{ border: '1px solid #ccc' }}>USD Value</th>
                      <th style={{ border: '1px solid #ccc' }}>Allocation %</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ border: '1px solid #ccc' }}>
                      <td style={{ border: '1px solid #ccc' }}>ETH (native)</td>
                      <td style={{ border: '1px solid #ccc' }}>{portfolio.nativeBalance}</td>
                      <td style={{ border: '1px solid #ccc' }}>{formatUsd(portfolio.nativePriceUsd)}</td>
                      <td style={{ border: '1px solid #ccc' }}>{formatUsd(portfolio.nativeUsdValue)}</td>
                      <td style={{ border: '1px solid #ccc' }}>{formatPercent(portfolio.nativeAllocationPercent)}</td>
                    </tr>
                    {portfolio.tokens.map((t) => (
                      <tr key={t.contractAddress} style={{ border: '1px solid #ccc' }}>
                        <td style={{ border: '1px solid #ccc' }}>{t.symbol}</td>
                        <td style={{ border: '1px solid #ccc' }}>{t.balance}</td>
                        <td style={{ border: '1px solid #ccc' }}>{formatUsd(t.priceUsd)}</td>
                        <td style={{ border: '1px solid #ccc' }}>{formatUsd(t.usdValue)}</td>
                        <td style={{ border: '1px solid #ccc' }}>{formatPercent(t.allocationPercent)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <h3 style={{ marginTop: '2rem' }}>Recent Transactions</h3>
                {portfolio.recentTransactions.length === 0 ? (
                  <p style={{ color: '#666' }}>
                    None found{portfolio.source === 'public_rpc' ? ' (requires an Alchemy key)' : ''}.
                  </p>
                ) : (
                  <table cellPadding={6} style={{ borderCollapse: 'collapse', width: '100%', border: '1px solid #ccc' }}>
                    <thead>
                      <tr style={{ border: '1px solid #ccc', textAlign: 'left' }}>
                        <th style={{ border: '1px solid #ccc' }}>Hash</th>
                        <th style={{ border: '1px solid #ccc' }}>From</th>
                        <th style={{ border: '1px solid #ccc' }}>To</th>
                        <th style={{ border: '1px solid #ccc' }}>Value</th>
                        <th style={{ border: '1px solid #ccc' }}>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.recentTransactions.map((tx) => (
                        <tr key={tx.hash} style={{ border: '1px solid #ccc' }}>
                          <td style={{ border: '1px solid #ccc' }}>
                            {tx.hash.slice(0, 10)}…{tx.hash.slice(-6)}
                          </td>
                          <td style={{ border: '1px solid #ccc' }}>
                            {tx.from.slice(0, 6)}…{tx.from.slice(-4)}
                          </td>
                          <td style={{ border: '1px solid #ccc' }}>
                            {tx.to.slice(0, 6)}…{tx.to.slice(-4)}
                          </td>
                          <td style={{ border: '1px solid #ccc' }}>{tx.value}</td>
                          <td style={{ border: '1px solid #ccc' }}>{tx.timestamp}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
