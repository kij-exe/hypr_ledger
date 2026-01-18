"""PnL result model for API responses."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PnLResult(BaseModel):
    """
    Aggregated PnL result for a user/coin/time range.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    user: str
    coin: Optional[str] = Field(default=None, description="Coin filter, None for all coins")
    fromMs: Optional[int] = Field(default=None, description="Start time filter")
    toMs: Optional[int] = Field(default=None, description="End time filter")
    realizedPnl: float = Field(description="Absolute USD value of realized PnL")
    returnPct: Optional[float] = Field(default=None, description="Relative return percentage")
    feesPaid: float = Field(description="Total fees paid")
    tradeCount: int = Field(description="Number of trades")
    volume: float = Field(default=0.0, description="Total notional volume traded")
    tainted: Optional[bool] = Field(default=None, description="Tainted flag for builder-only mode")
