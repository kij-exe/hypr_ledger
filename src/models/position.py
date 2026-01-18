"""Position state model for tracking position history."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class PositionState(BaseModel):
    """
    A snapshot of position state at a point in time.
    
    Used to reconstruct position history timeline.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    timeMs: int = Field(description="Timestamp in milliseconds")
    coin: str
    netSize: float = Field(description="Net position size (positive=long, negative=short)")
    avgEntryPx: float = Field(description="Average entry price")
    realizedPnl: float = Field(default=0.0, description="Cumulative realized PnL up to this point")
    tainted: Optional[bool] = Field(default=None, description="Tainted flag for builder-only mode")

    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no exposure)."""
        return abs(self.netSize) < 1e-10

    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.netSize > 0

    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.netSize < 0


class LeverageInfo(BaseModel):
    """Leverage information for a position."""
    model_config = ConfigDict(populate_by_name=True)
    
    type: Literal["cross", "isolated"] = Field(description="Leverage type")
    value: int = Field(description="Leverage value")
    rawUsd: Optional[str] = Field(default=None, description="Raw USD value")


class CumFunding(BaseModel):
    """Cumulative funding information."""
    model_config = ConfigDict(populate_by_name=True)
    
    allTime: str = Field(description="All-time cumulative funding")
    sinceChange: str = Field(description="Funding since last change")
    sinceOpen: str = Field(description="Funding since position opened")


class PositionData(BaseModel):
    """Current position data from clearinghouseState."""
    model_config = ConfigDict(populate_by_name=True)
    
    coin: str = Field(description="Asset symbol")
    szi: str = Field(description="Signed size (positive=long, negative=short)")
    entryPx: str = Field(description="Entry price")
    positionValue: str = Field(description="Notional position value")
    unrealizedPnl: str = Field(description="Unrealized PnL")
    returnOnEquity: str = Field(description="Return on equity")
    liquidationPx: str = Field(description="Liquidation price")
    marginUsed: str = Field(description="Margin used for position")
    maxLeverage: int = Field(description="Maximum allowed leverage")
    leverage: LeverageInfo = Field(description="Leverage information")
    cumFunding: CumFunding = Field(description="Cumulative funding")


class AssetPosition(BaseModel):
    """Asset position wrapper."""
    model_config = ConfigDict(populate_by_name=True)
    
    type: str = Field(description="Position type (e.g., 'oneWay')")
    position: PositionData = Field(description="Position details")


class MarginSummary(BaseModel):
    """Margin summary information."""
    model_config = ConfigDict(populate_by_name=True)
    
    accountValue: str = Field(description="Total account value")
    totalMarginUsed: str = Field(description="Total margin used")
    totalNtlPos: str = Field(description="Total notional position value")
    totalRawUsd: str = Field(description="Total raw USD value")


class CurrentPositionResponse(BaseModel):
    """Response from clearinghouseState endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    assetPositions: list[AssetPosition] = Field(description="List of open positions")
    marginSummary: MarginSummary = Field(description="Margin summary")
    crossMarginSummary: MarginSummary = Field(description="Cross margin summary")
    crossMaintenanceMarginUsed: str = Field(description="Cross maintenance margin used")
    withdrawable: str = Field(description="Withdrawable balance")
    time: int = Field(description="Timestamp in milliseconds")


class SimplePosition(BaseModel):
    """Simplified position with essential fields."""
    model_config = ConfigDict(populate_by_name=True)
    
    coin: str = Field(description="Asset symbol")
    szi: str = Field(description="Signed size (positive=long, negative=short)")
    entryPx: str = Field(description="Entry price")
    liqPx: str = Field(description="Liquidation price")
    marginUsed: str = Field(description="Margin used for position")
    unrealizedPnl: str = Field(description="Unrealized PnL")
    leverage: int = Field(description="Leverage value")


class SimpleMarginSummary(BaseModel):
    """Simplified margin summary."""
    model_config = ConfigDict(populate_by_name=True)
    
    accountValue: str = Field(description="Total account value")
    totalMarginUsed: str = Field(description="Total margin used")
    withdrawable: str = Field(description="Withdrawable balance")


class SimplePositionResponse(BaseModel):
    """Simplified position response with essential fields."""
    model_config = ConfigDict(populate_by_name=True)
    
    positions: list[SimplePosition] = Field(description="List of open positions")
    marginSummary: SimpleMarginSummary = Field(description="Margin summary")
    time: int = Field(description="Timestamp in milliseconds")
