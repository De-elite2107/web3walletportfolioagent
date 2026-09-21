export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** Same shape the backend enforces (app/eth_utils.py) - used to validate an
 * address before it's ever put in a request or read from the URL.
 */
export const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/

/** Turns a raw error into a plain-language message. The backend already
 * returns clean, readable `detail` strings for known failure modes (bad
 * address, Alchemy/Etherscan/LLM failures, timeouts, rate limits) - this
 * only needs to cover the case where the request never reached the backend
 * at all.
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

/** Shared fetch-and-parse helper: on a non-2xx response, reads the
 * backend's `detail` string and throws it as a plain Error (falling back to
 * a generic message if the body isn't JSON); on success, returns the
 * parsed JSON body. Used by every component that calls the API so the
 * "check res.ok, parse the error, throw" logic exists in exactly one place.
 */
export async function fetchJson(input: RequestInfo, init?: RequestInit) {
  const res = await fetch(input, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ? String(body.detail) : `Request failed with status ${res.status}`)
  }
  return res.json()
}
