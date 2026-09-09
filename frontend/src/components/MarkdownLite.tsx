import type { ReactNode } from 'react'

/** Minimal renderer for the light markdown the LLM tends to use in
 * analysis/chat replies (headings, **bold**, blank-line paragraphs) - just
 * enough that responses don't show literal `**`/`#` characters. Not a full
 * markdown parser; doesn't need to be one for this use case.
 */
function renderInline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

export default function MarkdownLite({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <>
      {lines.map((line, i) => {
        if (line.startsWith('### ')) {
          return (
            <h4 key={i} style={{ margin: '0.75em 0 0.25em', fontSize: '1em' }}>
              {renderInline(line.slice(4))}
            </h4>
          )
        }
        if (line.startsWith('## ') || line.startsWith('# ')) {
          return (
            <h4 key={i} style={{ margin: '0.75em 0 0.25em', fontSize: '1.05em' }}>
              {renderInline(line.replace(/^#+\s/, ''))}
            </h4>
          )
        }
        if (line.trim() === '') {
          return <div key={i} style={{ height: '0.5em' }} />
        }
        return (
          <p key={i} style={{ margin: '0 0 0.4em' }}>
            {renderInline(line)}
          </p>
        )
      })}
    </>
  )
}
