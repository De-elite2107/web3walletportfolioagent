from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PortfolioSnapshot(Base):
    """One fetched + priced portfolio snapshot for a (wallet_address, chain_id) pair.

    total_usd_value is broken out as its own column (rather than living only
    inside raw_json) so change-over-time queries don't need to parse JSON;
    raw_json keeps the full priced token breakdown for when that's needed.
    No change-over-time view built on this yet - just persistence.
    """

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    fetched_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    total_usd_value: Mapped[object] = mapped_column(Numeric, nullable=True)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)


class SecurityScanSnapshot(Base):
    """One security scan result for a (wallet_address, chain_id) pair.

    Same pattern as PortfolioSnapshot: just persistence for now, no
    change-over-time view built on this yet.
    """

    __tablename__ = "security_scan_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scanned_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
