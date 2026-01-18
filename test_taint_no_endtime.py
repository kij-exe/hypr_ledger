"""Test builder taint detection without end time specified."""

import asyncio
import logging
from datetime import datetime, timezone

from src.datasources.hyperliquid import HyperliquidDataSource
from src.services.position_service import PositionService
from src.services.builder_service import BuilderService
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_without_end_time():
    """Test taint detection when toMs is not specified (like API calls from frontend)."""
    
    TEST_USER = "0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8"
    TEST_COIN = "BTC"
    START_TIME = "2025-12-22T00:00:00Z"
    
    start_ms = int(datetime.fromisoformat(START_TIME.replace('Z', '+00:00')).timestamp() * 1000)
    
    print("=" * 80)
    print("Testing Taint Detection WITHOUT End Time (like frontend API calls)")
    print("=" * 80)
    print(f"User: {TEST_USER}")
    print(f"Coin: {TEST_COIN}")
    print(f"Start Time: {START_TIME}")
    print(f"End Time: NOT SPECIFIED (will auto-detect)")
    print()
    
    config = Config.from_env()
    datasource = HyperliquidDataSource(config.hyperliquid_api_url)
    position_service = PositionService(datasource)
    builder_service = BuilderService(config.target_builder)
    
    # Call WITHOUT toMs, just like the frontend does
    positions = await position_service.get_position_history(
        user=TEST_USER,
        coin=TEST_COIN,
        from_ms=start_ms,
        to_ms=None,  # NOT PROVIDED - this was the bug!
        builder_only=True,
        builder_service=builder_service
    )
    
    print(f"Found {len(positions)} position states")
    
    if positions:
        tainted_count = sum(1 for p in positions if p.tainted)
        not_tainted_count = sum(1 for p in positions if p.tainted == False)
        none_count = sum(1 for p in positions if p.tainted is None)
        
        print(f"  Tainted (True): {tainted_count}")
        print(f"  Not Tainted (False): {not_tainted_count}")
        print(f"  None: {none_count}")
        print()
        
        if none_count == len(positions):
            print("❌ FAIL: All positions have tainted=None")
            print("   This suggests builder matching didn't run!")
        elif not_tainted_count > 0 or tainted_count > 0:
            print("✅ SUCCESS: Taint detection working!")
            print(f"   Found mix of tainted/not-tainted positions")
        
        # Show samples
        print("\nSample positions:")
        for i, pos in enumerate(positions[:5]):
            timestamp = datetime.fromtimestamp(pos.timeMs / 1000, tz=timezone.utc)
            print(f"  {i+1}. {timestamp} | NetSize: {pos.netSize:.4f} | Tainted: {pos.tainted}")
    
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_without_end_time())
