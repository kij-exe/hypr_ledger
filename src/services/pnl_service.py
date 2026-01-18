"""PnL service for calculating realized PnL and returns."""

from typing import Optional

from src.datasources import DataSource
from src.models import PnLResult
from .trade_service import TradeService, calculate_trade_aggregates


class PnLService:
    """Service for calculating PnL metrics."""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource
        self.trade_service = TradeService(datasource)

    async def get_pnl(
        self,
        user: str,
        coin: Optional[str] = None,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        builder_only: bool = False,
        max_start_capital: Optional[float] = None,
    ) -> PnLResult:
        """
        Calculate PnL metrics for a user.
        
        Args:
            user: User address
            coin: Optional coin filter
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            builder_only: If True, only include builder-attributed trades
            max_start_capital: Cap for capital normalization (for fair comparison)
            
        Returns:
            PnLResult with realized PnL, return %, fees, trade count
        """
        # Get trades
        trades = await self.trade_service.get_trades(
            user=user,
            coin=coin,
            from_ms=from_ms,
            to_ms=to_ms,
            builder_only=builder_only,
        )
        
        # Calculate aggregates
        aggregates = calculate_trade_aggregates(trades)
        
        # Calculate return percentage
        return_pct = await self._calculate_return_pct(
            user=user,
            realized_pnl=aggregates["realized_pnl"],
            from_ms=from_ms,
            max_start_capital=max_start_capital,
        )
        
        return PnLResult(
            user=user,
            coin=coin,
            fromMs=from_ms,
            toMs=to_ms,
            realizedPnl=aggregates["realized_pnl"],
            returnPct=return_pct,
            feesPaid=aggregates["fees_paid"],
            tradeCount=aggregates["trade_count"],
            volume=aggregates["volume"],
            tainted=None,  # TODO: Set based on builder-only mode
        )

    async def _calculate_return_pct(
        self,
        user: str,
        realized_pnl: float,
        from_ms: Optional[int],
        max_start_capital: Optional[float],
    ) -> Optional[float]:
        """
        Calculate return percentage using capped normalization.
        
        Formula: returnPct = realizedPnl / effectiveCapital * 100
        where: effectiveCapital = min(equityAtFromMs, maxStartCapital)
        """
        # Try to get equity at start time
        if from_ms is not None:
            equity = await self.datasource.get_user_equity_at_time(user, from_ms)
        else:
            equity = None
        
        # Fall back to current equity if historical not available
        if equity is None:
            equity = await self.datasource.get_user_equity(user)
        
        if equity is None or equity <= 0:
            return None
        
        # Apply capital cap
        effective_capital = equity
        if max_start_capital is not None:
            effective_capital = min(equity, max_start_capital)
        
        if effective_capital <= 0:
            return None
        
        return (realized_pnl / effective_capital) * 100


async def calculate_pnl_for_users(
    datasource: DataSource,
    users: list[str],
    coin: Optional[str] = None,
    from_ms: Optional[int] = None,
    to_ms: Optional[int] = None,
    builder_only: bool = False,
    max_start_capital: Optional[float] = None,
) -> list[PnLResult]:
    """
    Calculate PnL for multiple users.
    
    Utility function used by leaderboard service.
    """
    pnl_service = PnLService(datasource)
    results = []
    
    for user in users:
        result = await pnl_service.get_pnl(
            user=user,
            coin=coin,
            from_ms=from_ms,
            to_ms=to_ms,
            builder_only=builder_only,
            max_start_capital=max_start_capital,
        )
        results.append(result)
    
    return results
