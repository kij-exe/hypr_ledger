"""Position service for reconstructing position history."""

from typing import Optional

from src.datasources import DataSource
from src.models import (
    Fill, 
    PositionState, 
    CurrentPositionResponse,
    SimplePosition,
    SimpleMarginSummary,
    SimplePositionResponse,
)


class PositionService:
    """Service for reconstructing and querying position history."""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource

    async def get_position_history(
        self,
        user: str,
        coin: str,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        builder_only: bool = False,
    ) -> list[PositionState]:
        """
        Get position history timeline for a user and coin.
        
        Reconstructs position states from fills using average cost method.
        
        Args:
            user: User address
            coin: Coin to get position history for
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            builder_only: If True, only include builder-attributed trades
            
        Returns:
            List of PositionState objects representing timeline
        """
        fills = await self.datasource.get_user_fills(
            user=user,
            start_time_ms=from_ms,
            end_time_ms=to_ms,
            coin=coin,
        )
        
        return self._reconstruct_position_history(fills, coin)

    def _reconstruct_position_history(
        self, 
        fills: list[Fill], 
        coin: str
    ) -> list[PositionState]:
        """
        Reconstruct position history from fills using average cost method.
        
        The average cost method:
        - When increasing position: new_avg = (old_size * old_avg + new_size * new_px) / total_size
        - When decreasing position: avg stays the same until position flips
        - When position flips: new_avg = execution price of the remaining position
        """
        if not fills:
            return []

        history: list[PositionState] = []
        
        # State tracking
        net_size = 0.0
        avg_entry_px = 0.0
        cumulative_pnl = 0.0

        for fill in fills:
            signed_size = fill.signed_size
            cumulative_pnl += fill.realized_pnl
            
            if abs(net_size) < 1e-10:
                # Starting fresh position
                net_size = signed_size
                avg_entry_px = fill.price
            elif (net_size > 0 and signed_size > 0) or (net_size < 0 and signed_size < 0):
                # Increasing position - update average
                total_size = net_size + signed_size
                avg_entry_px = (
                    (abs(net_size) * avg_entry_px + abs(signed_size) * fill.price) 
                    / abs(total_size)
                )
                net_size = total_size
            else:
                # Decreasing or flipping position
                new_size = net_size + signed_size
                
                if abs(new_size) < 1e-10:
                    # Position closed
                    net_size = 0.0
                    avg_entry_px = 0.0
                elif (new_size > 0) != (net_size > 0):
                    # Position flipped
                    net_size = new_size
                    avg_entry_px = fill.price
                else:
                    # Partial close - avg stays same
                    net_size = new_size

            # Record state after this fill
            history.append(PositionState(
                timeMs=fill.time,
                coin=coin,
                netSize=net_size,
                avgEntryPx=avg_entry_px,
                realizedPnl=cumulative_pnl,
                tainted=None,  # TODO: Set based on builder-only mode
            ))

        return history

    async def get_current_positions(self, user: str) -> CurrentPositionResponse:
        """
        Get user's current open positions with risk metrics.
        
        Args:
            user: User address
            
        Returns:
            CurrentPositionResponse with positions, margin summary, liquidation prices
        """
        data = await self.datasource.get_clearinghouse_state(user)
        return CurrentPositionResponse.model_validate(data)

    async def get_simple_positions(self, user: str) -> SimplePositionResponse:
        """
        Get simplified view of user's current positions.
        
        Args:
            user: User address
            
        Returns:
            SimplePositionResponse with essential fields: liqPx, marginUsed, etc.
        """
        data = await self.datasource.get_clearinghouse_state(user)
        
        positions = []
        for asset_pos in data.get("assetPositions", []):
            pos = asset_pos.get("position", {})
            positions.append(SimplePosition(
                coin=pos.get("coin", ""),
                szi=pos.get("szi", "0"),
                entryPx=pos.get("entryPx", "0"),
                liqPx=pos.get("liquidationPx", "0"),
                marginUsed=pos.get("marginUsed", "0"),
                unrealizedPnl=pos.get("unrealizedPnl", "0"),
                leverage=pos.get("leverage", {}).get("value", 1),
            ))
        
        margin = data.get("marginSummary", {})
        margin_summary = SimpleMarginSummary(
            accountValue=margin.get("accountValue", "0"),
            totalMarginUsed=margin.get("totalMarginUsed", "0"),
            withdrawable=data.get("withdrawable", "0"),
        )
        
        return SimplePositionResponse(
            positions=positions,
            marginSummary=margin_summary,
            time=data.get("time", 0),
        )

    async def get_position_lifecycles(
        self,
        user: str,
        coin: str,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
    ) -> list[tuple[int, int]]:
        """
        Get position lifecycles (start_ms, end_ms) for taint detection.
        
        A lifecycle starts when net_size moves from 0 to non-zero,
        and ends when it returns to 0.
        
        Returns:
            List of (start_time_ms, end_time_ms) tuples
        """
        history = await self.get_position_history(user, coin, from_ms, to_ms)
        
        lifecycles: list[tuple[int, int]] = []
        lifecycle_start: Optional[int] = None
        was_flat = True
        
        for state in history:
            is_flat = state.is_flat
            
            if was_flat and not is_flat:
                # Starting new lifecycle
                lifecycle_start = state.timeMs
            elif not was_flat and is_flat and lifecycle_start is not None:
                # Ending lifecycle
                lifecycles.append((lifecycle_start, state.timeMs))
                lifecycle_start = None
            
            was_flat = is_flat
        
        # Handle open position at end
        if lifecycle_start is not None and not was_flat:
            # Position still open - use last timestamp
            if history:
                lifecycles.append((lifecycle_start, history[-1].timeMs))
        
        return lifecycles
