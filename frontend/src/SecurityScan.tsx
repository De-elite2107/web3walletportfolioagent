import { useState } from 'react'
import { API_BASE_URL } from './api'
import type { RiskLevel, SecurityScanResponse } from './types'

const RISK_STYLE: Record<RiskLevel, { background: string; border: string; label: string }> = {
  high: { background: '#f8d7da', border: '#dc3545', label: 'High' },
  elevated: { background: '#fff3cd', border: '#e0a800', label: 'Elevated' },
  normal: { background: '#f1f1f1', border: '#ccc', label: 'Normal' },
}

export default function SecurityScan({ address, chainId }: { address: string; chainId: number }) {
  const [result, setResult] = useState<SecurityScanResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleScan() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE_URL}/portfolio/security-scan?address=${address}&chain_id=${chainId}`)
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ? String(body.detail) : `Request failed with status ${res.status}`)
      }
      setResult(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const anyFlagged = result?.approvals.some((a) => a.riskLevel !== 'normal')

  return (
    <div style={{ marginTop: '2rem', textAlign: 'left' }}>
      <h3>Security Scan</h3>
      <p style={{ color: '#666', fontSize: '0.9rem' }}>
        Checks which contracts currently hold token spending approval for this wallet, and flags approvals
        worth reviewing. Signals only, not certainty.
      </p>
      <button onClick={handleScan} disabled={loading}>
        {loading ? 'Scanning… (can take up to a minute)' : result ? 'Re-scan' : 'Run Security Scan'}
      </button>
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}

      {result && (
        <>
          <div
            style={{
              marginTop: '1rem',
              background: anyFlagged ? '#fff3cd' : '#d4edda',
              border: `1px solid ${anyFlagged ? '#e0a800' : '#28a745'}`,
              color: '#333',
              padding: '0.75rem 1rem',
              borderRadius: 4,
            }}
          >
            {result.overallRiskSummary}
          </div>
          <p style={{ color: '#666', fontSize: '0.85rem' }}>
            Scanned the most recent {result.lookbackBlocks.toLocaleString()} blocks (recent activity, not full
            wallet history).
          </p>

          {result.approvals.length > 0 && (
            <table cellPadding={6} style={{ borderCollapse: 'collapse', width: '100%', marginTop: '0.5rem' }}>
              <thead>
                <tr style={{ textAlign: 'left' }}>
                  <th>Risk</th>
                  <th>Token</th>
                  <th>Spender</th>
                  <th>Amount</th>
                  <th>Verified</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {result.approvals.map((a) => {
                  const style = RISK_STYLE[a.riskLevel]
                  return (
                    <tr key={`${a.tokenAddress}-${a.spender}`} style={{ background: style.background }}>
                      <td style={{ border: `1px solid ${style.border}`, fontWeight: 600 }}>{style.label}</td>
                      <td style={{ border: `1px solid ${style.border}` }}>{a.token}</td>
                      <td style={{ border: `1px solid ${style.border}` }}>
                        {a.spender.slice(0, 8)}…{a.spender.slice(-6)}
                      </td>
                      <td style={{ border: `1px solid ${style.border}` }}>{a.amount}</td>
                      <td style={{ border: `1px solid ${style.border}` }}>
                        {a.isVerified === true ? 'Yes' : a.isVerified === false ? 'No' : 'Unknown'}
                      </td>
                      <td style={{ border: `1px solid ${style.border}`, whiteSpace: 'pre-wrap' }}>{a.note}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
