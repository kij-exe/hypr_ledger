"""Leaderboard service for ranking users by various metrics."""

from enum import Enum
from typing import Optional

from src.datasources import DataSource
from src.models import LeaderboardEntry, CombinedLeaderboardEntry
from .pnl_service import calculate_pnl_for_users


class LeaderboardMetric(str, Enum):
    """Available metrics for leaderboard ranking."""
    VOLUME = "volume"
    PNL = "pnl"
    RETURN_PCT = "returnPct"


class LeaderboardService:
    """Service for generating user leaderboards."""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource

    async def get_leaderboard(
        self,
        users: list[str],
        coin: Optional[str] = None,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        metric: LeaderboardMetric = LeaderboardMetric.PNL,
        builder_only: bool = False,
        max_start_capital: Optional[float] = None,
    ) -> list[LeaderboardEntry]:
        """
        Generate a leaderboard ranking users by a specified metric.
        
        Args:
            users: List of user addresses to include
            coin: Optional coin filter
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            metric: Ranking metric (volume, pnl, returnPct)
            builder_only: If True, only include builder-attributed trades
            max_start_capital: Cap for capital normalization
            
        Returns:
            List of LeaderboardEntry sorted by rank (1 = best)
        """
        # Calculate PnL for all users
        pnl_results = await calculate_pnl_for_users(
            datasource=self.datasource,
            users=users,
            coin=coin,
            from_ms=from_ms,
            to_ms=to_ms,
            builder_only=builder_only,
            max_start_capital=max_start_capital,
        )
        
        # Extract metric values and create entries
        entries: list[tuple[str, float, int, Optional[bool]]] = []
        
        for result in pnl_results:
            metric_value = self._get_metric_value(result, metric)
            if metric_value is not None:
                entries.append((
                    result.user,
                    metric_value,
                    result.tradeCount,
                    result.tainted,
                ))
        
        # Sort by metric value (descending for all metrics)
        entries.sort(key=lambda x: x[1], reverse=True)
        
        # Create ranked entries
        leaderboard = [
            LeaderboardEntry(
                rank=i + 1,
                user=user,
                metricValue=metric_value,
                tradeCount=trade_count,
                tainted=tainted,
            )
            for i, (user, metric_value, trade_count, tainted) in enumerate(entries)
        ]
        
        return leaderboard

    def _get_metric_value(self, result, metric: LeaderboardMetric) -> Optional[float]:
        """Extract the metric value from a PnL result."""
        if metric == LeaderboardMetric.VOLUME:
            return result.volume
        elif metric == LeaderboardMetric.PNL:
            return result.realizedPnl
        elif metric == LeaderboardMetric.RETURN_PCT:
            return result.returnPct
        return None

    async def get_combined_leaderboard(
        self,
        users: list[str],
        coin: Optional[str] = None,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        builder_only: bool = False,
        max_start_capital: Optional[float] = None,
    ) -> list[CombinedLeaderboardEntry]:
        """
        Get leaderboard with all metrics for each user.
        
        Useful for competition displays where users can sort by different metrics.
        
        Args:
            users: List of user addresses to include
            coin: Optional coin filter
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            builder_only: If True, only include builder-attributed trades
            max_start_capital: Cap for capital normalization
            
        Returns:
            List of CombinedLeaderboardEntry with all metrics
        """
        # Calculate PnL for all users
        pnl_results = await calculate_pnl_for_users(
            datasource=self.datasource,
            users=users,
            coin=coin,
            from_ms=from_ms,
            to_ms=to_ms,
            builder_only=builder_only,
            max_start_capital=max_start_capital,
        )
        
        # Create combined entries
        combined = [
            CombinedLeaderboardEntry(
                user=result.user,
                volume=result.volume,
                pnl=result.realizedPnl,
                returnPct=result.returnPct if result.returnPct is not None else 0.0,
                tradeCount=result.tradeCount,
                tainted=result.tainted,
            )
            for result in pnl_results
        ]
        
        return combined
