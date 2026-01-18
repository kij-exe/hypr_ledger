"""Test script to verify builder-only taint detection logic."""

import asyncio
import logging
from datetime import datetime, timezone

from src.datasources.hyperliquid import HyperliquidDataSource
from src.services.position_service import PositionService
from src.services.builder_service import BuilderService
from src.config import Config

# Set up logging to see debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_taint_detection():
    """Test taint detection for a specific user and time range."""
    
    # Configuration
    # This user was found in the builder CSV with BTC trades
    TEST_USER = "0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8"
    TEST_COIN = "BTC"
    
    # Use a specific date range where we know there's data
    START_TIME = "2025-12-22T00:00:00Z"
    END_TIME = "2025-12-23T00:00:00Z"
    
    start_ms = int(datetime.fromisoformat(START_TIME.replace('Z', '+00:00')).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(END_TIME.replace('Z', '+00:00')).timestamp() * 1000)
    
    print("=" * 80)
    print("Testing Builder-Only Taint Detection")
    print("=" * 80)
    print(f"User: {TEST_USER}")
    print(f"Coin: {TEST_COIN}")
    print(f"Time Range: {START_TIME} to {END_TIME}")
    print()
    
    # Initialize services
    config = Config.from_env()
    datasource = HyperliquidDataSource(config.hyperliquid_api_url)
    position_service = PositionService(datasource)
    builder_service = BuilderService(config.target_builder)
    
    print(f"Target Builder: {config.target_builder}")
    print()
    
    # Test 1: Get positions WITHOUT builder-only mode
    print("-" * 80)
    print("TEST 1: Positions WITHOUT builder-only mode")
    print("-" * 80)
    positions_normal = await position_service.get_position_history(
        user=TEST_USER,
        coin=TEST_COIN,
        from_ms=start_ms,
        to_ms=end_ms,
        builder_only=False
    )
    print(f"Found {len(positions_normal)} position states")
    print(f"Tainted field: {positions_normal[0].tainted if positions_normal else 'N/A'} (should be None)")
    print()
    
    # Test 2: Get positions WITH builder-only mode
    print("-" * 80)
    print("TEST 2: Positions WITH builder-only mode")
    print("-" * 80)
    positions_builder = await position_service.get_position_history(
        user=TEST_USER,
        coin=TEST_COIN,
        from_ms=start_ms,
        to_ms=end_ms,
        builder_only=True,
        builder_service=builder_service
    )
    print(f"Found {len(positions_builder)} position states")
    
    if positions_builder:
        tainted_count = sum(1 for p in positions_builder if p.tainted)
        not_tainted_count = sum(1 for p in positions_builder if p.tainted == False)
        none_count = sum(1 for p in positions_builder if p.tainted is None)
        
        print(f"Tainted: {tainted_count}")
        print(f"Not Tainted: {not_tainted_count}")
        print(f"None (no builder data): {none_count}")
        print()
        
        # Show sample positions
        print("Sample position states:")
        for i, pos in enumerate(positions_builder[:5]):
            timestamp = datetime.fromtimestamp(pos.timeMs / 1000, tz=timezone.utc)
            print(f"  {i+1}. Time: {timestamp}, NetSize: {pos.netSize:.4f}, "
                  f"PnL: {pos.realizedPnl:.2f}, Tainted: {pos.tainted}")
    else:
        print("No positions found!")
    
    print()
    print("=" * 80)
    print("RESULTS INTERPRETATION:")
    print("=" * 80)
    
    if positions_builder:
        tainted_count = sum(1 for p in positions_builder if p.tainted)
        not_tainted_count = sum(1 for p in positions_builder if p.tainted == False)
        none_count = sum(1 for p in positions_builder if p.tainted is None)
        
        if none_count == len(positions_builder):
            print("✓ All positions have tainted=None")
            print("  → This means NO builder fills were found for this user")
            print("  → User doesn't trade through the target builder")
            print("  → This is CORRECT behavior - cannot determine taint without builder data")
        elif not_tainted_count > 0 and tainted_count > 0:
            print("✓ Mix of tainted and not-tainted positions")
            print(f"  → {not_tainted_count} clean (only builder fills in lifecycle)")
            print(f"  → {tainted_count} tainted (contains non-builder fills)")
            print("  → This is CORRECT behavior - proper lifecycle-based taint detection")
        elif not_tainted_count == len(positions_builder):
            print("✓ All positions are not-tainted (tainted=False)")
            print("  → All fills matched to builder - 100% builder attribution")
            print("  → This is CORRECT - user trades exclusively through target builder")
        elif tainted_count == len(positions_builder):
            print("⚠ All positions are tainted (tainted=True)")
            print("  → Every lifecycle contains at least one non-builder fill")
            print("  → Check if match rate is reasonable")
            print("  → If match rate is high but all tainted, investigate lifecycle logic")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_taint_detection())
