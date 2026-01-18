"""API routes for the trade ledger service."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.datasources import DataSource
from src.models import (
    Trade, 
    PositionState, 
    PnLResult, 
    LeaderboardEntry,
    CombinedLeaderboardEntry,
    DepositResult,
    CurrentPositionResponse,
    SimplePositionResponse,
)
from src.services import (
    TradeService, 
    PositionService, 
    PnLService, 
    LeaderboardService,
    DepositService,
)
from src.services.leaderboard_service import LeaderboardMetric
from .dependencies import get_datasource

router = APIRouter(prefix="/v1")


@router.get("/trades", response_model=list[Trade])
async def get_trades(
    user: str = Query(
        ..., 
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    coin: Optional[str] = Query(
        None, 
        description="Coin filter",
        example="SOL"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds",
        example=1766449358096
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds",
        example=1766449704759
    ),
    builderOnly: bool = Query(
        False, 
        description="Filter to builder-attributed trades only"
    ),
    datasource: DataSource = Depends(get_datasource),
) -> list[Trade]:
    """
    Get normalized fills for a user.
    
    Returns: timeMs, coin, side, px, sz, fee, closedPnl, builder
    """
    service = TradeService(datasource)
    return await service.get_trades(
        user=user,
        coin=coin,
        from_ms=fromMs,
        to_ms=toMs,
        builder_only=builderOnly,
    )


@router.get("/positions/history", response_model=list[PositionState])
async def get_position_history(
    user: str = Query(
        ..., 
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    coin: Optional[str] = Query(
        None, 
        description="Coin to get position history for (if not provided, all coins are included)",
        example="SOL"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds",
        example=1766449358096
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds",
        example=1766449704759
    ),
    builderOnly: bool = Query(
        False, 
        description="Filter to builder-attributed trades only"
    ),
    datasource: DataSource = Depends(get_datasource),
) -> list[PositionState]:
    """
    Get position history timeline for a user and coin.
    
    Returns: timeMs, netSize, avgEntryPx, tainted
    """
    service = PositionService(datasource)
    return await service.get_position_history(
        user=user,
        coin=coin,
        from_ms=fromMs,
        to_ms=toMs,
        builder_only=builderOnly,
    )


@router.get("/pnl", response_model=PnLResult)
async def get_pnl(
    user: str = Query(
        ..., 
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    coin: Optional[str] = Query(
        None, 
        description="Coin filter",
        example="SOL"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds",
        example=1766449358096
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds",
        example=1766449704759
    ),
    builderOnly: bool = Query(
        False, 
        description="Filter to builder-attributed trades only"
    ),
    maxStartCapital: Optional[float] = Query(
        None, 
        description="Cap for capital normalization",
        example=1000.0
    ),
    datasource: DataSource = Depends(get_datasource),
) -> PnLResult:
    """
    Get PnL metrics for a user.
    
    Returns: realizedPnl, returnPct, feesPaid, tradeCount, volume, tainted
    """
    service = PnLService(datasource)
    return await service.get_pnl(
        user=user,
        coin=coin,
        from_ms=fromMs,
        to_ms=toMs,
        builder_only=builderOnly,
        max_start_capital=maxStartCapital,
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    users: str = Query(
        ..., 
        description="Comma-separated list of user addresses",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17,0x186b7610ff3f2e3fd7985b95f525ee0e37a79a74,0x6c8031a9eb4415284f3f89c0420f697c87168263"
    ),
    coin: Optional[str] = Query(
        None, 
        description="Coin filter",
        example="BTC"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds"
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds"
    ),
    metric: str = Query(
        "pnl", 
        description="Ranking metric: volume, pnl, or returnPct",
        example="pnl"
    ),
    builderOnly: bool = Query(
        False, 
        description="Filter to builder-attributed trades only"
    ),
    maxStartCapital: Optional[float] = Query(
        None, 
        description="Cap for capital normalization",
        example=1000.0
    ),
    datasource: DataSource = Depends(get_datasource),
) -> list[LeaderboardEntry]:
    """
    Get leaderboard ranking users by specified metric.
    
    Returns ranked list: rank, user, metricValue, tradeCount, tainted
    """
    # Parse users from comma-separated string
    user_list = [u.strip() for u in users.split(",") if u.strip()]
    
    # Parse metric
    try:
        leaderboard_metric = LeaderboardMetric(metric)
    except ValueError:
        leaderboard_metric = LeaderboardMetric.PNL
    
    service = LeaderboardService(datasource)
    return await service.get_leaderboard(
        users=user_list,
        coin=coin,
        from_ms=fromMs,
        to_ms=toMs,
        metric=leaderboard_metric,
        builder_only=builderOnly,
        max_start_capital=maxStartCapital,
    )


@router.get("/leaderboard/combined", response_model=list[CombinedLeaderboardEntry])
async def get_combined_leaderboard(
    users: str = Query(
        ..., 
        description="Comma-separated list of user addresses",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17,0x186b7610ff3f2e3fd7985b95f525ee0e37a79a74"
    ),
    coin: Optional[str] = Query(
        None, 
        description="Coin filter",
        example="BTC"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds"
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds"
    ),
    builderOnly: bool = Query(
        False, 
        description="Filter to builder-attributed trades only"
    ),
    maxStartCapital: Optional[float] = Query(
        None, 
        description="Cap for capital normalization",
        example=1000.0
    ),
    datasource: DataSource = Depends(get_datasource),
) -> list[CombinedLeaderboardEntry]:
    """
    Get combined leaderboard with all metrics (volume, PnL, returnPct).
    
    Useful for competition displays where sorting by different metrics is needed.
    Returns all three metrics for each user without pre-ranking.
    """
    # Parse users from comma-separated string
    user_list = [u.strip() for u in users.split(",") if u.strip()]
    
    service = LeaderboardService(datasource)
    return await service.get_combined_leaderboard(
        users=user_list,
        coin=coin,
        from_ms=fromMs,
        to_ms=toMs,
        builder_only=builderOnly,
        max_start_capital=maxStartCapital,
    )


@router.get("/positions/current", response_model=SimplePositionResponse)
async def get_current_positions(
    user: str = Query(
        ...,
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    datasource: DataSource = Depends(get_datasource),
) -> SimplePositionResponse:
    """
    Get user's current open positions (simplified).
    
    Returns positions with liqPx, marginUsed, leverage, unrealizedPnl.
    """
    service = PositionService(datasource)
    return await service.get_simple_positions(user=user)


@router.get("/positions/current/full", response_model=CurrentPositionResponse)
async def get_current_positions_full(
    user: str = Query(
        ...,
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    datasource: DataSource = Depends(get_datasource),
) -> CurrentPositionResponse:
    """
    Get user's current open positions with full risk metrics.
    
    Returns full positions with all fields including cumFunding, returnOnEquity, etc.
    """
    service = PositionService(datasource)
    return await service.get_current_positions(user=user)


@router.get("/deposits", response_model=DepositResult)
async def get_deposits(
    user: str = Query(
        ..., 
        description="User address",
        example="0x0e09b56ef137f417e424f1265425e93bfff77e17"
    ),
    fromMs: Optional[int] = Query(
        None, 
        description="Start time in milliseconds",
        example=1704057200000
    ),
    toMs: Optional[int] = Query(
        None, 
        description="End time in milliseconds"
    ),
    datasource: DataSource = Depends(get_datasource),
) -> DepositResult:
    """
    Get deposit tracking information for a user.
    
    Enables filtering users who reloaded capital during competition window.
    
    Returns: totalDeposits, depositCount, deposits[]
    """
    service = DepositService(datasource)
    return await service.get_deposits(
        user=user,
        from_ms=fromMs,
        to_ms=toMs,
    )


