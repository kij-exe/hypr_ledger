"""Trade service for normalizing and filtering fills."""

from typing import Optional
import logging

from src.datasources import DataSource
from src.models import Fill, Trade

logger = logging.getLogger(__name__)


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
            builder_only: If True, mark trades as builder-attributed and filter
            
        Returns:
            List of normalized Trade objects
        """
        fills = await self.datasource.get_user_fills(
            user=user,
            start_time_ms=from_ms,
            end_time_ms=to_ms,
            coin=coin,
        )
        
        # Check builder attribution if requested
        builder_matched_indices = set()
        target_builder = None
        if builder_only and fills:
            from datetime import datetime, timezone
            from src.config import Config
            from src.services.builder_service import BuilderService
            
            config = Config.from_env()
            target_builder = config.target_builder
            builder_service = BuilderService(target_builder)
            
            # Determine time range
            actual_from_ms = from_ms if from_ms else fills[0].time
            actual_to_ms = to_ms if to_ms else fills[-1].time
            
            logger.info(f"Fetching builder fills for trades from {actual_from_ms} to {actual_to_ms}")
            builder_fills = await builder_service.get_builder_fills_for_range(
                user=user,
                start_ms=actual_from_ms,
                end_ms=actual_to_ms
            )
            
            if builder_fills:
                builder_matched_indices = builder_service.match_fills(fills, builder_fills)
                logger.info(f"Matched {len(builder_matched_indices)}/{len(fills)} trades to builder")
        
        # Convert fills to trades, marking builder attribution
        trades = []
        for idx, fill in enumerate(fills):
            # Trade is NOT tainted if it matched the builder
            # Trade IS tainted if it didn't match (non-builder)
            is_builder_attributed = idx in builder_matched_indices if builder_only else None
            tainted = not is_builder_attributed if is_builder_attributed is not None else False
            
            trades.append(Trade(
                timeMs=fill.time,
                coin=fill.coin,
                side="Buy" if fill.is_buy else "Sell",
                px=fill.price,
                sz=fill.size,
                fee=fill.fee_amount,
                closedPnl=fill.realized_pnl,
                builder=target_builder if is_builder_attributed else None,
                tainted=tainted,
            ))
        
        # Filter to only builder-attributed trades if requested
        if builder_only:
            trades = [t for t in trades if not t.tainted]
            logger.info(f"Filtered to {len(trades)} builder-attributed trades")
        
        return trades

    def _fill_to_trade(self, fill: Fill) -> Trade:
        """Convert a Fill to a normalized Trade (deprecated - use get_trades)."""
        return Trade(
            timeMs=fill.time,
            coin=fill.coin,
            side="Buy" if fill.is_buy else "Sell",
            px=fill.price,
            sz=fill.size,
            fee=fill.fee_amount,
            closedPnl=fill.realized_pnl,
            builder=None,
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
