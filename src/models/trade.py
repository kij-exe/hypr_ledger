"""Trade model for API responses."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Trade(BaseModel):
    """
    Normalized trade for API response.
    
    This is the processed/normalized version of a Fill
    suitable for API responses.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    timeMs: int = Field(description="Timestamp in milliseconds")
    coin: str
    side: str = Field(description="'Buy' or 'Sell'")
    px: float = Field(description="Price")
    sz: float = Field(description="Size")
    fee: float = Field(description="Fee amount")
    closedPnl: float = Field(description="Realized PnL")
    builder: Optional[str] = Field(default=None, description="Builder address if attributed")
    tainted: bool = Field(default=False, description="Whether this trade is tainted (builder-only mode)")
