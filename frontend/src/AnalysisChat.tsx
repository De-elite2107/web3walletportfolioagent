import { useState } from 'react'
import { API_BASE_URL } from './api'
import type { PortfolioResponse } from './types'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

async function parseErrorOrJson(res: Response) {
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ? String(body.detail) : `Request failed with status ${res.status}`)
  }
  return res.json()
}

export default function AnalysisChat({
  address,
  chainId,
  portfolio,
}: {
  address: string
  chainId: number
  portfolio: PortfolioResponse
}) {
  const [summary, setSummary] = useState<string | null>(null)
  const [analyzedPortfolio, setAnalyzedPortfolio] = useState<PortfolioResponse>(portfolio)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)

  async function handleAnalyze() {
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const data = await parseErrorOrJson(
        await fetch(`${API_BASE_URL}/portfolio/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address, chainId }),
        }),
      )
      setSummary(data.summary)
      setAnalyzedPortfolio(data.portfolio)
      setMessages([])
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : String(err))
    } finally {
      setAnalyzing(false)
    }
  }

  async function handleSend() {
    const trimmed = chatInput.trim()
    if (!trimmed || chatLoading) return

    const nextMessages: ChatMessage[] = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setChatInput('')
    setChatLoading(true)
    setChatError(null)

    try {
      const data = await parseErrorOrJson(
        await fetch(`${API_BASE_URL}/portfolio/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address, portfolio: analyzedPortfolio, history: messages, message: trimmed }),
        }),
      )
      setMessages([...nextMessages, { role: 'assistant', content: data.reply }])
    } catch (err) {
      setChatError(err instanceof Error ? err.message : String(err))
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div style={{ marginTop: '2rem', textAlign: 'left' }}>
      <button onClick={handleAnalyze} disabled={analyzing}>
        {analyzing ? 'Analyzing…' : summary ? 'Re-analyze' : 'Analyze'}
      </button>
      {analyzeError && <p style={{ color: 'crimson' }}>Error: {analyzeError}</p>}

      {summary && (
        <>
          <h3>Analysis</h3>
          <p style={{ whiteSpace: 'pre-wrap' }}>{summary}</p>

          <h3>Ask a follow-up</h3>
          <div
            style={{
              border: '1px solid #ccc',
              borderRadius: 4,
              padding: '0.75rem',
              maxHeight: 300,
              overflowY: 'auto',
              marginBottom: '0.5rem',
            }}
          >
            {messages.length === 0 && <p style={{ color: '#666' }}>No messages yet - ask something below.</p>}
            {messages.map((m, i) => (
              <p key={i}>
                <strong>{m.role === 'user' ? 'You' : 'Orblo'}:</strong> {m.content}
              </p>
            ))}
            {chatLoading && <p style={{ color: '#666' }}>Thinking…</p>}
          </div>
          {chatError && <p style={{ color: 'crimson' }}>Error: {chatError}</p>}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            style={{ display: 'flex', gap: '0.5rem' }}
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="e.g. why is my WETH allocation so high?"
              style={{ flex: 1, padding: '0.5rem' }}
              disabled={chatLoading}
            />
            <button type="submit" disabled={chatLoading || !chatInput.trim()}>
              Send
            </button>
          </form>
        </>
      )}
    </div>
  )
}
