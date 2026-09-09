export interface Token {
  symbol: string
  contractAddress: string
  balance: string
  priceUsd: string | null
  usdValue: string | null
  allocationPercent: number | null
}

export interface Transaction {
  hash: string
  from: string
  to: string
  value: number | string
  timestamp: string
}

export interface PortfolioResponse {
  address: string
  chainId: number
  nativeBalance: string
  nativePriceUsd: string | null
  nativeUsdValue: string | null
  nativeAllocationPercent: number | null
  tokens: Token[]
  recentTransactions: Transaction[]
  totalUsdValue: string
  concentrationRisk: boolean
  concentrationToken: string | null
  source?: string
}

export type RiskLevel = 'high' | 'elevated' | 'normal'

export interface SecurityFinding {
  token: string
  tokenAddress: string
  spender: string
  amount: string
  isUnlimited: boolean
  isVerified: boolean | null
  riskLevel: RiskLevel
  note: string
}

export interface SecurityScanResponse {
  address: string
  chainId: number
  lookbackBlocks: number
  approvals: SecurityFinding[]
  overallRiskSummary: string
}
