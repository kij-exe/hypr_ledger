"""Trade service for normalizing and filtering fills."""

from typing import Optional

from src.datasources import DataSource
from src.models import Fill, Trade


class TradeService:
    """Service for retrieving and normalizing trade data."""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource

    async def get_trades(
        self,
        user: str,
        coin: Optional[str] = None,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        builder_only: bool = False,
    ) -> list[Trade]:
        """
        Get normalized trades for a user.
        
        Args:
            user: User address
            coin: Optional coin filter
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            builder_only: If True, filter to builder-attributed trades only
            
        Returns:
            List of normalized Trade objects
        """
        fills = await self.datasource.get_user_fills(
            user=user,
            start_time_ms=from_ms,
            end_time_ms=to_ms,
            coin=coin,
        )
        
        trades = [self._fill_to_trade(f) for f in fills]
        
        # builder_only filtering is a placeholder for now
        # When implemented, would filter by TARGET_BUILDER
        if builder_only:
            # TODO: Implement builder filtering when builder attribution is available
            pass
        
        return trades

    def _fill_to_trade(self, fill: Fill) -> Trade:
        """Convert a Fill to a normalized Trade."""
        return Trade(
            timeMs=fill.time,
            coin=fill.coin,
            side="Buy" if fill.is_buy else "Sell",
            px=fill.price,
            sz=fill.size,
            fee=fill.fee_amount,
            closedPnl=fill.realized_pnl,
            builder=None,  # TODO: Extract builder from fill when available
            tainted=False,
        )


def calculate_trade_aggregates(trades: list[Trade]) -> dict:
    """
    Calculate aggregate statistics from trades.
    
    This is a shared utility used by multiple services.
    
    Returns:
        dict with: realized_pnl, fees_paid, trade_count, volume
    """
    realized_pnl = sum(t.closedPnl for t in trades)
    fees_paid = sum(t.fee for t in trades)
    trade_count = len(trades)
    volume = sum(t.px * t.sz for t in trades)
    
    return {
        "realized_pnl": realized_pnl,
        "fees_paid": fees_paid,
        "trade_count": trade_count,
        "volume": volume,
    }
