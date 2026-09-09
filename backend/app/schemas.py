from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    address: str
    chainId: int = 1


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    address: str
    portfolio: dict
    history: list[ChatMessage] = Field(default_factory=list)
    message: str
