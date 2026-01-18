"""Compare trades vs positions taint detection."""

import asyncio
import logging
from datetime import datetime, timezone

from src.datasources.hyperliquid import HyperliquidDataSource
from src.services.position_service import PositionService
from src.services.trade_service import TradeService
from src.services.builder_service import BuilderService
from src.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def compare_trades_and_positions():
    """Compare trades and positions to debug taint detection."""
    
    # Use a user with builder fills
    TEST_USER = "0xb9e18a24143a1ad1b2a0a38a74b553733c0fdbb8"
    TEST_COIN = "BTC"
    START_TIME = "2025-12-22T00:00:00Z"
    END_TIME = "2025-12-23T00:00:00Z"  # Full day to see mixed scenario
    
    start_ms = int(datetime.fromisoformat(START_TIME.replace('Z', '+00:00')).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(END_TIME.replace('Z', '+00:00')).timestamp() * 1000)
    
    print("=" * 80)
    print("COMPARING TRADES vs POSITIONS TAINT DETECTION")
    print("=" * 80)
    print(f"User: {TEST_USER}")
    print(f"Coin: {TEST_COIN}")
    print(f"Time: {START_TIME} to {END_TIME}")
    print()
    
    config = Config.from_env()
    datasource = HyperliquidDataSource(config.hyperliquid_api_url)
    
    # Test 1: Get trades with builder-only mode
    print("-" * 80)
    print("TRADES (builder-only mode)")
    print("-" * 80)
    trade_service = TradeService(datasource)
    trades = await trade_service.get_trades(
        user=TEST_USER,
        coin=TEST_COIN,
        from_ms=start_ms,
        to_ms=end_ms,
        builder_only=True
    )
    
    print(f"Total trades returned: {len(trades)}")
    tainted_trades = [t for t in trades if t.tainted]
    not_tainted_trades = [t for t in trades if not t.tainted]
    print(f"  Tainted: {len(tainted_trades)}")
    print(f"  Not tainted: {len(not_tainted_trades)}")
    
    if trades:
        print("\nFirst 5 trades:")
        for i, t in enumerate(trades[:5]):
            ts = datetime.fromtimestamp(t.timeMs / 1000, tz=timezone.utc)
            print(f"  {i+1}. {ts} | {t.side} {t.sz} @ {t.px} | Tainted: {t.tainted}")
    
    print()
    
    # Test 2: Get positions with builder-only mode
    print("-" * 80)
    print("POSITIONS (builder-only mode)")
    print("-" * 80)
    position_service = PositionService(datasource)
    builder_service = BuilderService(config.target_builder)
    
    positions = await position_service.get_position_history(
        user=TEST_USER,
        coin=TEST_COIN,
        from_ms=start_ms,
        to_ms=end_ms,
        builder_only=True,
        builder_service=builder_service
    )
    
    print(f"Total position states: {len(positions)}")
    tainted_positions = [p for p in positions if p.tainted]
    not_tainted_positions = [p for p in positions if p.tainted == False]
    none_positions = [p for p in positions if p.tainted is None]
    
    print(f"  Tainted (True): {len(tainted_positions)}")
    print(f"  Not tainted (False): {len(not_tainted_positions)}")
    print(f"  None: {len(none_positions)}")
    
    if positions:
        print("\nFirst 5 position states:")
        for i, p in enumerate(positions[:5]):
            ts = datetime.fromtimestamp(p.timeMs / 1000, tz=timezone.utc)
            print(f"  {i+1}. {ts} | NetSize: {p.netSize:.4f} | PnL: {p.realizedPnl:.2f} | Tainted: {p.tainted}")
    
    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    
    if len(not_tainted_trades) > 0 and len(not_tainted_positions) == 0:
        print("❌ MISMATCH DETECTED!")
        print(f"   - Trades show {len(not_tainted_trades)} clean trades (tainted=False)")
        print(f"   - But ALL positions are tainted or None")
        print()
        print("This suggests the position lifecycle logic is too strict OR")
        print("there's a bug in how lifecycle fills are being checked against builder indices")
    elif len(not_tainted_trades) > 0 and len(not_tainted_positions) > 0:
        print("✅ BOTH trades and positions show non-tainted items")
        print(f"   - {len(not_tainted_trades)} clean trades")
        print(f"   - {len(not_tainted_positions)} clean position states")
    else:
        print("⚠️  No clean trades found - user may not trade through builder in this period")
    
    print("=" * 80)
    print("\nCheck the logs above for detailed builder matching information.")
    print("Look for 'Matched fill indices' and 'Lifecycle fills' to debug.")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(compare_trades_and_positions())
