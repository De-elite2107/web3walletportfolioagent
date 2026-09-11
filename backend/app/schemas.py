from pydantic import BaseModel, ConfigDict, Field


class AnalyzeRequest(BaseModel):
    address: str
    chainId: int = 1


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str = Field(..., max_length=4000)


class TokenHolding(BaseModel):
    """Mirrors the shape returned by /portfolio's `tokens` entries."""

    model_config = ConfigDict(extra="ignore")

    symbol: str = Field(..., max_length=200)
    contractAddress: str
    balance: str
    priceUsd: str | None = None
    usdValue: str | None = None
    allocationPercent: float | None = None


class Transaction(BaseModel):
    """Mirrors /portfolio's `recentTransactions` entries."""

    model_config = ConfigDict(extra="ignore")

    hash: str
    from_: str = Field(alias="from")
    to: str
    value: float | str
    timestamp: str


class PortfolioPayload(BaseModel):
    """The portfolio snapshot shape /portfolio and /portfolio/analyze return.

    /portfolio/chat takes this directly from the client rather than
    re-fetching, so it's grounded in exactly what's on screen - but that
    means it's also the one place a client controls the entire object sent
    into the LLM prompt. Validating the real shape (rather than accepting
    an arbitrary dict) keeps this from being usable as a free-form text
    injection channel into the LLM.
    """

    model_config = ConfigDict(extra="ignore")

    address: str
    chainId: int
    nativeBalance: str
    nativePriceUsd: str | None = None
    nativeUsdValue: str | None = None
    nativeAllocationPercent: float | None = None
    tokens: list[TokenHolding] = Field(default_factory=list, max_length=500)
    recentTransactions: list[Transaction] = Field(default_factory=list, max_length=100)
    totalUsdValue: str
    concentrationRisk: bool
    concentrationToken: str | None = None
    source: str | None = None


class ChatRequest(BaseModel):
    address: str
    portfolio: PortfolioPayload
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    message: str = Field(..., min_length=1, max_length=2000)
