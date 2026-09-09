from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PortfolioSnapshot(Base):
    """One fetched portfolio snapshot for a (wallet_address, chain_id) pair.

    Just persistence for now - no change-over-time queries built on this yet.
    """

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fetched_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
