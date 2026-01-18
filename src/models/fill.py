"""Fill model representing a single trade fill from the exchange."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FillSide(str, Enum):
    """Side of the fill."""
    BUY = "B"
    SELL = "A"


class Fill(BaseModel):
    """
    Normalized fill data from Hyperliquid.
    
    This is the raw fill data as returned by the data source,
    before any additional processing.
    """
    coin: str
    px: str = Field(description="Price as string")
    sz: str = Field(description="Size as string")
    side: FillSide
    time: int = Field(description="Timestamp in milliseconds")
    start_position: str = Field(alias="startPosition", description="Position before fill")
    dir: str = Field(description="Direction: 'Open Long', 'Close Long', etc.")
    closed_pnl: str = Field(alias="closedPnl", description="Realized PnL from this fill")
    hash: str = Field(description="Transaction hash")
    oid: int = Field(description="Order ID")
    crossed: bool = Field(description="Whether this was a taker order")
    fee: str = Field(description="Total fee")
    tid: int = Field(description="Trade ID")
    fee_token: str = Field(alias="feeToken", default="USDC")
    builder_fee: Optional[str] = Field(alias="builderFee", default=None)

    class Config:
        populate_by_name = True

    @property
    def price(self) -> float:
        """Get price as float."""
        return float(self.px)

    @property
    def size(self) -> float:
        """Get size as float."""
        return float(self.sz)

    @property
    def fee_amount(self) -> float:
        """Get fee as float."""
        return float(self.fee)

    @property
    def realized_pnl(self) -> float:
        """Get closed PnL as float."""
        return float(self.closed_pnl)

    @property
    def builder_fee_amount(self) -> Optional[float]:
        """Get builder fee as float if present."""
        return float(self.builder_fee) if self.builder_fee else None

    @property
    def is_buy(self) -> bool:
        """Check if this is a buy."""
        return self.side == FillSide.BUY

    @property
    def signed_size(self) -> float:
        """Get signed size (positive for buy, negative for sell)."""
        return self.size if self.is_buy else -self.size
