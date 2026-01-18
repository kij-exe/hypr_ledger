"""Abstract base class for data sources."""

from abc import ABC, abstractmethod
from typing import Optional

from src.models import Fill


class DataSource(ABC):
    """
    Abstract interface for trade data sources.
    
    This abstraction allows swapping between different data providers
    (Hyperliquid public API, Insilico-HL, HyperServe, etc.) with minimal changes.
    """

    @abstractmethod
    async def get_user_fills(
        self,
        user: str,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        coin: Optional[str] = None,
    ) -> list[Fill]:
        """
        Retrieve fills for a user within a time range.
        
        Args:
            user: User address (0x...)
            start_time_ms: Start time in milliseconds (inclusive), None for no lower bound
            end_time_ms: End time in milliseconds (inclusive), None for current time
            coin: Optional coin filter, None for all coins
            
        Returns:
            List of Fill objects sorted by time ascending
            
        Note:
            Implementation should handle pagination internally if needed.
            The returned fills should be complete within the time range
            (subject to API limitations which should be documented).
        """
        pass

    @abstractmethod
    async def get_user_equity(self, user: str) -> float:
        """
        Get current account equity for a user.
        
        Args:
            user: User address (0x...)
            
        Returns:
            Current equity in USD
        """
        pass

    @abstractmethod
    async def get_user_equity_at_time(
        self, 
        user: str, 
        time_ms: int
    ) -> Optional[float]:
        """
        Get historical account equity for a user at a specific time.
        
        Args:
            user: User address (0x...)
            time_ms: Timestamp in milliseconds
            
        Returns:
            Equity in USD at the specified time, or None if not available
            
        Note:
            Not all data sources support historical equity.
            If not available, implementation should return None.
        """
        pass

    @abstractmethod
    async def get_user_deposits(
        self,
        user: str,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> list[dict]:
        """
        Retrieve deposit/withdrawal ledger updates for a user.
        
        Args:
            user: User address (0x...)
            start_time_ms: Start time in milliseconds (inclusive), None for no lower bound
            end_time_ms: End time in milliseconds (inclusive), None for current time
            
        Returns:
            List of ledger update dicts with 'time', 'delta', 'hash' fields
        """
        pass

    @abstractmethod
    async def get_clearinghouse_state(self, user: str) -> dict:
        """
        Retrieve user's perpetuals account summary with current positions.
        
        Args:
            user: User address (0x...)
            
        Returns:
            Dict with assetPositions, marginSummary, withdrawable, etc.
        """
        pass

    async def close(self) -> None:
        """
        Clean up resources (e.g., close HTTP sessions).
        
        Override this if the data source holds resources that need cleanup.
        """
        pass
