import { useEffect, useState } from 'react'
import { useAccount, useChainId } from 'wagmi'
import Header from './Header'
import AnalysisChat from './AnalysisChat'
import SecurityScan from './SecurityScan'
import Banner from './components/Banner'
import ErrorBanner, { toPlainMessage } from './components/ErrorBanner'
import Skeleton from './components/Skeleton'
import Spinner from './components/Spinner'
import { API_BASE_URL } from './api'
import type { PortfolioResponse } from './types'
import './App.css'

function formatUsd(value: string | null): string {
  if (value === null) return '—'
  const n = Number(value)
  return Number.isFinite(n) ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '—'
}

function formatPercent(value: number | null): string {
  return value === null ? '—' : `${value}%`
}

function HoldingsTableSkeleton() {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Balance</th>
            <th>Price (USD)</th>
            <th>USD Value</th>
            <th>Allocation %</th>
          </tr>
        </thead>
        <tbody>
          {[0, 1, 2].map((i) => (
            <tr key={i}>
              <td>
                <Skeleton width="60px" />
              </td>
              <td>
                <Skeleton width="80px" />
              </td>
              <td>
                <Skeleton width="70px" />
              </td>
              <td>
                <Skeleton width="70px" />
              </td>
              <td>
                <Skeleton width="50px" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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
    setPortfolio(null)
    setLoading(true)
    setError(null)

    fetch(`${API_BASE_URL}/portfolio?address=${address}&chain_id=${chainId}`, {
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail ? String(body.detail) : `Request failed with status ${res.status}`)
        }
        return res.json() as Promise<PortfolioResponse>
      })
      .then(setPortfolio)
      .catch((err: unknown) => {
        const message = toPlainMessage(err)
        if (message) setError(message)
      })
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [isConnected, address, chainId])

  return (
    <div className="app">
      <Header />

      <main>
        {!isConnected && (
          <div className="connect-screen">
            <h2>Connect a wallet to get started</h2>
            <p>Orblo reads your on-chain holdings, prices them, and flags anything worth reviewing.</p>
          </div>
        )}

        {isConnected && (
          <div>
            <div className="wallet-bar">
              <span>
                Connected as <code>{address}</code>
              </span>
              <span>{chain?.name ?? `Chain ${chainId}`}</span>
            </div>

            {loading && (
              <div className="section">
                <h2>Portfolio</h2>
                <div className="card">
                  <div className="loading-line" style={{ marginBottom: '0.75rem' }}>
                    <Spinner /> Loading portfolio…
                  </div>
                  <div className="portfolio-value">
                    <div className="portfolio-value-label">Total portfolio value</div>
                    <Skeleton width="220px" height="2.4rem" />
                  </div>
                  <HoldingsTableSkeleton />
                </div>
              </div>
            )}

            {!loading && error && (
              <div className="section">
                <h2>Portfolio</h2>
                <ErrorBanner message={error} />
              </div>
            )}

            {!loading && !error && portfolio && (
              <>
                <div className="section">
                  <h2>Portfolio</h2>
                  {portfolio.concentrationRisk && (
                    <div style={{ marginBottom: '1rem' }}>
                      <Banner variant="warning">
                        Concentration risk: <strong>{portfolio.concentrationToken}</strong> makes up more than
                        50% of this wallet's total value.
                      </Banner>
                    </div>
                  )}

                  <div className="card">
                    <div className="portfolio-value">
                      <div className="portfolio-value-label">Total portfolio value</div>
                      <div className="portfolio-value-amount">{formatUsd(portfolio.totalUsdValue)}</div>
                    </div>

                    <div className="table-scroll">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Asset</th>
                            <th>Balance</th>
                            <th>Price (USD)</th>
                            <th>USD Value</th>
                            <th>Allocation %</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>ETH (native)</td>
                            <td>{portfolio.nativeBalance}</td>
                            <td>{formatUsd(portfolio.nativePriceUsd)}</td>
                            <td>{formatUsd(portfolio.nativeUsdValue)}</td>
                            <td>{formatPercent(portfolio.nativeAllocationPercent)}</td>
                          </tr>
                          {portfolio.tokens.map((t) => (
                            <tr key={t.contractAddress}>
                              <td>{t.symbol}</td>
                              <td>{t.balance}</td>
                              <td>{formatUsd(t.priceUsd)}</td>
                              <td>{formatUsd(t.usdValue)}</td>
                              <td>{formatPercent(t.allocationPercent)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                <div className="section">
                  <h2>Recent Transactions</h2>
                  <div className="card">
                    {portfolio.recentTransactions.length === 0 ? (
                      <p className="section-hint">
                        None found{portfolio.source === 'public_rpc' ? ' (requires an Alchemy key)' : ''}.
                      </p>
                    ) : (
                      <div className="table-scroll">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Hash</th>
                              <th>From</th>
                              <th>To</th>
                              <th>Value</th>
                              <th>Timestamp</th>
                            </tr>
                          </thead>
                          <tbody>
                            {portfolio.recentTransactions.map((tx) => (
                              <tr key={tx.hash}>
                                <td>
                                  {tx.hash.slice(0, 10)}…{tx.hash.slice(-6)}
                                </td>
                                <td>
                                  {tx.from.slice(0, 6)}…{tx.from.slice(-4)}
                                </td>
                                <td>
                                  {tx.to.slice(0, 6)}…{tx.to.slice(-4)}
                                </td>
                                <td>{tx.value}</td>
                                <td>{tx.timestamp}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>

                <div className="section">
                  <h2>AI Analysis</h2>
                  <AnalysisChat address={address as string} chainId={chainId} portfolio={portfolio} />
                </div>

                <div className="section">
                  <h2>Security Scan</h2>
                  <SecurityScan address={address as string} chainId={chainId} />
                </div>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
