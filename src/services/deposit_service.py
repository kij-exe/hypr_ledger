"""Deposit service for tracking user deposits and withdrawals."""

from typing import Optional

from src.datasources import DataSource
from src.models import Deposit, DepositResult


class DepositService:
    """Service for tracking user deposits."""

    def __init__(self, datasource: DataSource):
        self.datasource = datasource

    async def get_deposits(
        self,
        user: str,
        from_ms: Optional[int] = None,
        to_ms: Optional[int] = None,
    ) -> DepositResult:
        """
        Get deposit tracking information for a user.
        
        Enables filtering users who reloaded capital during competition window.
        
        Args:
            user: User address
            from_ms: Start time in milliseconds
            to_ms: End time in milliseconds
            
        Returns:
            DepositResult with total deposits, count, and individual deposits
        """
        # Get ledger updates
        ledger_updates = await self.datasource.get_user_deposits(
            user=user,
            start_time_ms=from_ms,
            end_time_ms=to_ms,
        )
        
        # Filter and parse deposits
        deposits: list[Deposit] = []
        total_deposits = 0.0
        
        for update in ledger_updates:
            delta = update.get("delta", {})
            update_type = delta.get("type", "")
            
            # Only track actual deposits (not withdrawals or transfers)
            if update_type == "deposit":
                amount = float(delta.get("usdc", 0))
                
                # Deposits should be positive
                if amount > 0:
                    deposits.append(Deposit(
                        timeMs=update.get("time", 0),
                        amount=amount,
                        hash=update.get("hash", ""),
                        txType=update_type,
                    ))
                    total_deposits += amount
        
        # Sort by time descending
        deposits.sort(key=lambda d: d.timeMs, reverse=True)
        
        return DepositResult(
            totalDeposits=total_deposits,
            depositCount=len(deposits),
            deposits=deposits,
        )
