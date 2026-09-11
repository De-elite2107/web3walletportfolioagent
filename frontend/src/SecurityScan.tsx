import { useState } from 'react'
import Banner from './components/Banner'
import ErrorBanner from './components/ErrorBanner'
import Spinner from './components/Spinner'
import Skeleton from './components/Skeleton'
import { API_BASE_URL, fetchJson, toPlainMessage } from './api'
import type { RiskLevel, SecurityScanResponse } from './types'

const BADGE_CLASS: Record<RiskLevel, string> = {
  high: 'badge-high',
  elevated: 'badge-elevated',
  normal: 'badge-normal',
}

const LABEL: Record<RiskLevel, string> = {
  high: 'High',
  elevated: 'Elevated',
  normal: 'Normal',
}

export default function SecurityScan({ address, chainId }: { address: string; chainId: number }) {
  const [result, setResult] = useState<SecurityScanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleScan() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchJson(`${API_BASE_URL}/portfolio/security-scan?address=${address}&chain_id=${chainId}`)
      setResult(data)
    } catch (err) {
      setError(toPlainMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const anyFlagged = result?.approvals.some((a) => a.riskLevel !== 'normal')
  const anyHigh = result?.approvals.some((a) => a.riskLevel === 'high')

  return (
    <div className="card">
      <p className="section-hint">
        Checks which contracts currently hold token spending approval for this wallet, and flags approvals
        worth reviewing. Signals only, not certainty.
      </p>
      <button className="btn btn-primary" onClick={handleScan} disabled={loading}>
        {loading && <Spinner />}
        {loading ? 'Scanning…' : result ? 'Re-scan' : 'Run Security Scan'}
      </button>
      {loading && <p className="section-hint" style={{ marginTop: '0.5rem' }}>This can take up to a minute.</p>}

      {loading && (
        <div style={{ marginTop: '1rem' }}>
          <Skeleton height="2.5rem" />
          <div style={{ height: 12 }} />
          {[0, 1, 2].map((i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <Skeleton height="1.5rem" />
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div style={{ marginTop: '1rem' }}>
          <ErrorBanner message={error} />
        </div>
      )}

      {!loading && !error && result && (
        <>
          <div style={{ marginTop: '1rem' }}>
            <Banner variant={anyHigh ? 'danger' : anyFlagged ? 'warning' : 'success'}>
              {result.overallRiskSummary}
            </Banner>
          </div>
          <p className="section-hint" style={{ marginTop: '0.5rem' }}>
            Scanned the most recent {result.lookbackBlocks.toLocaleString()} blocks (recent activity, not full
            wallet history).
          </p>

          {result.approvals.length > 0 && (
            <div className="table-scroll" style={{ marginTop: '0.5rem' }}>
              <table className="data-table" style={{ tableLayout: 'fixed', minWidth: 640 }}>
                <colgroup>
                  <col style={{ width: '9%' }} />
                  <col style={{ width: '11%' }} />
                  <col style={{ width: '13%' }} />
                  <col style={{ width: '12%' }} />
                  <col style={{ width: '10%' }} />
                  <col style={{ width: '45%' }} />
                </colgroup>
                <thead>
                  <tr>
                    <th>Risk</th>
                    <th>Token</th>
                    <th>Spender</th>
                    <th>Amount</th>
                    <th>Verified</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {result.approvals.map((a) => (
                    <tr key={`${a.tokenAddress}-${a.spender}`}>
                      <td>
                        <span className={`badge ${BADGE_CLASS[a.riskLevel]}`}>{LABEL[a.riskLevel]}</span>
                      </td>
                      <td style={{ overflowWrap: 'break-word' }}>{a.token}</td>
                      <td>
                        <code>
                          {a.spender.slice(0, 8)}…{a.spender.slice(-6)}
                        </code>
                      </td>
                      <td style={{ overflowWrap: 'break-word' }}>{a.amount}</td>
                      <td>{a.isVerified === true ? 'Yes' : a.isVerified === false ? 'No' : 'Unknown'}</td>
                      <td style={{ whiteSpace: 'pre-wrap', overflowWrap: 'break-word' }}>{a.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
