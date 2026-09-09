import { ConnectButton } from '@rainbow-me/rainbowkit'

export default function Header() {
  return (
    <header className="app-header">
      <div className="app-header-title">
        <span className="app-logo" aria-hidden="true">
          🔮
        </span>
        <div>
          <h1 className="app-name">Orblo</h1>
          <p className="app-tagline">Wallet portfolio &amp; security analysis</p>
        </div>
      </div>
      <ConnectButton />
    </header>
  )
}
