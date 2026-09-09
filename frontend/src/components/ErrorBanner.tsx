import Banner from './Banner'

/** Turns a raw error into a plain-language message. The backend already
 * returns clean, readable `detail` strings for known failure modes (bad
 * address, Alchemy/Etherscan/LLM failures, timeouts) - this only needs to
 * cover the case where the request never reached the backend at all.
 */
export function toPlainMessage(err: unknown): string {
  if (err instanceof TypeError) {
    // Browsers surface a network-level failure (backend down, CORS, no
    // connection) as a generic "Failed to fetch" / "Load failed" TypeError.
    return 'Could not reach the server - is the backend running?'
  }
  if (err instanceof DOMException && err.name === 'AbortError') {
    return ''
  }
  return err instanceof Error ? err.message : String(err)
}

export default function ErrorBanner({ message }: { message: string }) {
  return <Banner variant="danger">{message}</Banner>
}
