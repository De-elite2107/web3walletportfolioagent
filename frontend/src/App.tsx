import { ConnectButton } from '@rainbow-me/rainbowkit'
import { useAccount } from 'wagmi'
import './App.css'

function App() {
  const { address, isConnected } = useAccount()

  return (
    <div className="app">
      <header className="app-header">
        <h1>Orblo</h1>
        <p>Wallet portfolio &amp; security analysis</p>
        <ConnectButton />
      </header>

      <main>
        {isConnected ? (
          <p>
            Connected as <code>{address}</code>
          </p>
        ) : (
          <p>Connect a wallet to view your portfolio.</p>
        )}
      </main>
    </div>
  )
}

export default App
