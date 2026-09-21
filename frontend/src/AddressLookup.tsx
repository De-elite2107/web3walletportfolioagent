import { useState } from 'react'
import { ADDRESS_RE } from './api'

/** Read-only lookup: view any public address's dashboard without connecting
 * a wallet. Everything shown is public on-chain data - no signature or
 * transaction is ever requested in this mode.
 */
export default function AddressLookup({ onSubmit }: { onSubmit: (address: string) => void }) {
  const [value, setValue] = useState('')
  const trimmed = value.trim()
  const valid = ADDRESS_RE.test(trimmed)

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (valid) onSubmit(trimmed)
      }}
      style={{ display: 'flex', gap: '0.5rem', width: '100%', maxWidth: 560 }}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="0x… paste any public address"
        aria-label="Public wallet address to view read-only"
        style={{
          flex: 1,
          padding: '10px 12px',
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg)',
          color: 'var(--text-h)',
          fontFamily: 'var(--mono)',
          fontSize: 14,
        }}
      />
      <button type="submit" className="btn" disabled={!valid}>
        View read-only
      </button>
    </form>
  )
}
