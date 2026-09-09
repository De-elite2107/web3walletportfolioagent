import { useState } from 'react'
import ErrorBanner, { toPlainMessage } from './components/ErrorBanner'
import MarkdownLite from './components/MarkdownLite'
import Spinner from './components/Spinner'
import Skeleton from './components/Skeleton'
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
      setChatError(null)
    } catch (err) {
      setAnalyzeError(toPlainMessage(err))
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
      setChatError(toPlainMessage(err))
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="card">
      <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing}>
        {analyzing && <Spinner />}
        {analyzing ? 'Analyzing…' : summary ? 'Re-analyze' : 'Run Analysis'}
      </button>

      {analyzing && !summary && (
        <div style={{ marginTop: '1rem' }}>
          <Skeleton height="1em" />
          <div style={{ height: 8 }} />
          <Skeleton height="1em" width="90%" />
          <div style={{ height: 8 }} />
          <Skeleton height="1em" width="75%" />
        </div>
      )}

      {analyzeError && (
        <div style={{ marginTop: '1rem' }}>
          <ErrorBanner message={analyzeError} />
        </div>
      )}

      {summary && (
        <>
          <div style={{ marginTop: '1rem' }}>
            <MarkdownLite text={summary} />
          </div>

          <h3 style={{ fontSize: '15px', marginTop: '1.5rem', marginBottom: '0.5rem' }}>Ask a follow-up</h3>
          <div
            style={{
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '0.75rem',
              maxHeight: 300,
              overflowY: 'auto',
              marginBottom: '0.5rem',
              background: 'var(--bg)',
            }}
          >
            {messages.length === 0 && <p className="section-hint">No messages yet - ask something below.</p>}
            {messages.map((m, i) => (
              <div key={i} style={{ margin: '0 0 8px' }}>
                <strong>{m.role === 'user' ? 'You' : 'Orblo'}:</strong>{' '}
                {m.role === 'assistant' ? <MarkdownLite text={m.content} /> : m.content}
              </div>
            ))}
            {chatLoading && (
              <div className="loading-line">
                <Spinner /> Thinking…
              </div>
            )}
          </div>
          {chatError && <ErrorBanner message={chatError} />}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="e.g. why is my WETH allocation so high?"
              style={{
                flex: 1,
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid var(--border)',
                background: 'var(--bg)',
                color: 'var(--text-h)',
              }}
              disabled={chatLoading}
            />
            <button type="submit" className="btn btn-primary" disabled={chatLoading || !chatInput.trim()}>
              Send
            </button>
          </form>
        </>
      )}
    </div>
  )
}
