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
        coin: Optional[str] = None,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
        builder_only: bool = False,
        builder_service: Optional["BuilderService"] = None,
    ) -> list[PositionState]:
        """
        Get position history timeline for a user and coin.
        
        Reconstructs position states from fills using average cost method.
        If coin is not specified, combines realized PnL across all coins.
        
        Args:
            user: User address
            coin: Coin to get position history for (if None, all coins are included)
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            builder_only: If True, mark tainted positions and they can be filtered
            builder_service: Builder service for matching builder fills (required if builder_only=True)
            
        Returns:
            List of PositionState objects representing timeline
        """
        fills = await self.datasource.get_user_fills(
            user=user,
            start_time_ms=from_ms,
            end_time_ms=to_ms,
            coin=coin,
        )
        
        # Get builder fills if builder_only mode is enabled
        builder_fill_indices = set()
        if builder_only and builder_service and from_ms and to_ms:
            from src.services.builder_service import BuilderService
            builder_fills = await builder_service.get_builder_fills_for_range(
                user=user,
                start_ms=from_ms,
                end_ms=to_ms
            )
            builder_fill_indices = builder_service.match_fills(fills, builder_fills)
        
        return self._reconstruct_position_history(fills, coin, builder_fill_indices if builder_only else None)

    def _reconstruct_position_history(
        self, 
        fills: list[Fill], 
        coin: Optional[str],
        builder_fill_indices: Optional[set[int]] = None
    ) -> list[PositionState]:
        """
        Reconstruct position history from fills using average cost method.
        
        If coin is None, tracks positions across all coins and combines realized PnL.
        If builder_fill_indices is provided, marks positions as tainted based on lifecycle analysis.
        
        The average cost method:
        - When increasing position: new_avg = (old_size * old_avg + new_size * new_px) / total_size
        - When decreasing position: avg stays the same until position flips
        - When position flips: new_avg = execution price of the remaining position
        """
        if not fills:
            return []

        history: list[PositionState] = []
        
        if coin is None:
            # Multi-coin mode: track positions per coin and combine PnL
            return self._reconstruct_multi_coin_history(fills, builder_fill_indices)
        
        # Single coin mode: original logic
        # State tracking
        net_size = 0.0
        avg_entry_px = 0.0
        cumulative_pnl = 0.0
        
        # Track lifecycles for taint detection
        lifecycle_start_idx: Optional[int] = None
        lifecycle_fills: list[int] = []  # Indices of fills in current lifecycle

        for fill_idx, fill in enumerate(fills):
            signed_size = fill.signed_size
            cumulative_pnl += fill.realized_pnl
            
            was_flat = abs(net_size) < 1e-10
            
            if was_flat:
                # Starting fresh position - start new lifecycle
                lifecycle_start_idx = fill_idx
                lifecycle_fills = [fill_idx]
                net_size = signed_size
                avg_entry_px = fill.price
            elif (net_size > 0 and signed_size > 0) or (net_size < 0 and signed_size < 0):
                # Increasing position - update average
                lifecycle_fills.append(fill_idx)
                total_size = net_size + signed_size
                avg_entry_px = (
                    (abs(net_size) * avg_entry_px + abs(signed_size) * fill.price) 
                    / abs(total_size)
                )
                net_size = total_size
            else:
                # Decreasing or flipping position
                lifecycle_fills.append(fill_idx)
                new_size = net_size + signed_size
                
                if abs(new_size) < 1e-10:
                    # Position closed - end lifecycle
                    net_size = 0.0
                    avg_entry_px = 0.0
                elif (new_size > 0) != (net_size > 0):
                    # Position flipped
                    net_size = new_size
                    avg_entry_px = fill.price
                else:
                    # Partial close - avg stays same
                    net_size = new_size

            # Determine taint status for this position state
            tainted = None
            if builder_fill_indices is not None and lifecycle_start_idx is not None:
                # Check if any fill in current lifecycle is not builder-attributed
                tainted = any(idx not in builder_fill_indices for idx in lifecycle_fills)

            # Record state after this fill
            history.append(PositionState(
                timeMs=fill.time,
                coin=coin,
                netSize=net_size,
                avgEntryPx=avg_entry_px,
                realizedPnl=cumulative_pnl,
                tainted=tainted,
            ))

        return history

    def _reconstruct_multi_coin_history(
        self, 
        fills: list[Fill],
        builder_fill_indices: Optional[set[int]] = None
    ) -> list[PositionState]:
        """
        Reconstruct position history across all coins, combining realized PnL.
        
        When tracking multiple coins:
        - Realized PnL is summed across all coins
        - Net size is set to 0 (since we can't meaningfully combine sizes across different coins)
        - Each fill creates a new state with updated cumulative PnL
        - Taint detection tracks lifecycles per coin
        """
        if not fills:
            return []
        
        # Track positions per coin
        coin_positions: dict[str, dict] = {}
        # Track lifecycles per coin for taint detection
        coin_lifecycles: dict[str, list[int]] = {}
        history: list[PositionState] = []
        cumulative_pnl = 0.0
        
        for fill_idx, fill in enumerate(fills):
            coin_name = fill.coin
            cumulative_pnl += fill.realized_pnl
            
            # Initialize coin tracking if needed
            if coin_name not in coin_positions:
                coin_positions[coin_name] = {
                    'net_size': 0.0,
                    'avg_entry_px': 0.0
                }
            
            coin_state = coin_positions[coin_name]
            net_size = coin_state['net_size']
            avg_entry_px = coin_state['avg_entry_px']
            signed_size = fill.signed_size
            
            was_flat = abs(net_size) < 1e-10
            
            # Update position for this coin using same logic as single-coin
            if was_flat:
                # Start new lifecycle for this coin
                if coin_name not in coin_lifecycles:
                    coin_lifecycles[coin_name] = []
                coin_lifecycles[coin_name] = [fill_idx]
                net_size = signed_size
                avg_entry_px = fill.price
            elif (net_size > 0 and signed_size > 0) or (net_size < 0 and signed_size < 0):
                # Add to current lifecycle
                coin_lifecycles[coin_name].append(fill_idx)
                total_size = net_size + signed_size
                avg_entry_px = (
                    (abs(net_size) * avg_entry_px + abs(signed_size) * fill.price) 
                    / abs(total_size)
                )
                net_size = total_size
            else:
                # Add to current lifecycle
                if coin_name in coin_lifecycles:
                    coin_lifecycles[coin_name].append(fill_idx)
                new_size = net_size + signed_size
                if abs(new_size) < 1e-10:
                    net_size = 0.0
                    avg_entry_px = 0.0
                elif (net_size > 0 and new_size < 0) or (net_size < 0 and new_size > 0):
                    net_size = new_size
                    avg_entry_px = fill.price
                else:
                    net_size = new_size
            
            coin_state['net_size'] = net_size
            coin_state['avg_entry_px'] = avg_entry_px
            
            # Compute taint status
            # A multi-coin position is tainted if ANY coin's active lifecycle contains a non-builder fill
            tainted = None
            if builder_fill_indices is not None:
                tainted = False
                for coin_lifecycle in coin_lifecycles.values():
                    if coin_lifecycle:  # Only check active lifecycles
                        if any(idx not in builder_fill_indices for idx in coin_lifecycle):
                            tainted = True
                            break
            
            # Create position state with combined PnL and netSize=0
            history.append(PositionState(
                timeMs=fill.time,
                coin="ALL",  # Indicate this is combined across all coins
                netSize=0.0,  # Can't meaningfully combine sizes across coins
                avgEntryPx=0.0,
                realizedPnl=cumulative_pnl,
                tainted=tainted,
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
