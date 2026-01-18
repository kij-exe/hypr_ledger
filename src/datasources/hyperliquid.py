"""Hyperliquid public API data source implementation."""

import logging
import asyncio
from typing import Optional

import httpx

from src.models import Fill
from .base import DataSource

logger = logging.getLogger(__name__)

# API constants
MAINNET_API_URL = "https://api.hyperliquid.xyz"
MAX_FILLS_PER_REQUEST = 2000
MAX_RECENT_FILLS = 10000
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 10
RETRY_DELAY = 2.0


class HyperliquidDataSource(DataSource):
    """
    Data source implementation using Hyperliquid public API.
    
    Limitations:
    - Only the 10,000 most recent fills are available per user
    - Maximum 2,000 fills per request
    - Historical equity is not directly available (returns None)
    """

    def __init__(self, api_url: str = MAINNET_API_URL):
        """
        Initialize Hyperliquid data source.
        
        Args:
            api_url: Base URL for the Hyperliquid API
        """
        self.api_url = api_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _make_request(self, endpoint: str, payload: dict, retry_count: int = 0) -> dict:
        """
        Make HTTP request with timeout handling and retries.
        
        Args:
            endpoint: API endpoint path
            payload: Request payload
            retry_count: Current retry attempt
            
        Returns:
            Response JSON data
        """
        client = await self._get_client()
        
        try:
            response = await client.post(
                endpoint,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
            
        except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            if retry_count < MAX_RETRIES:
                logger.warning(
                    f"Request to {endpoint} timed out (attempt {retry_count + 1}/{MAX_RETRIES}). "
                    f"Retrying in {RETRY_DELAY}s..."
                )
                print(f"⚠️  API request timed out. Retrying ({retry_count + 1}/{MAX_RETRIES})...")
                await asyncio.sleep(RETRY_DELAY)
                return await self._make_request(endpoint, payload, retry_count + 1)
            else:
                logger.error(f"Request to {endpoint} failed after {MAX_RETRIES} retries: {e}")
                print(f"❌ API request failed after {MAX_RETRIES} retries: {e}")
                raise
                
        except httpx.HTTPStatusError as e:
            # Handle rate limiting (429 Too Many Requests)
            if e.response.status_code == 429 and retry_count < MAX_RETRIES:
                retry_delay = 0.5
                logger.warning(
                    f"Rate limited (429) on {endpoint} (attempt {retry_count + 1}/{MAX_RETRIES}). "
                    f"Retrying in {retry_delay}s..."
                )
                print(f"⚠️  Rate limited. Retrying in {retry_delay}s ({retry_count + 1}/{MAX_RETRIES})...")
                await asyncio.sleep(retry_delay)
                return await self._make_request(endpoint, payload, retry_count + 1)
            
            logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            raise

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
        return self._client

    async def get_user_fills(
        self,
        user: str,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        coin: Optional[str] = None,
    ) -> list[Fill]:
        """
        Retrieve fills for a user within a time range.
        
        Uses the userFillsByTime endpoint with pagination to fetch all available fills.
        """
        client = await self._get_client()
        all_fills: list[Fill] = []
        
        # Default start time to 0 (beginning of time)
        current_start = start_time_ms or 0
        
        while True:
            payload = {
                "type": "userFillsByTime",
                "user": user,
                "startTime": current_start,
                "aggregateByTime": True,
            }
            
            if end_time_ms is not None:
                payload["endTime"] = end_time_ms

            data = await self._make_request("/info", payload)

            if not data:
                break

            # Parse fills
            batch_fills = [Fill.model_validate(f) for f in data]
            
            # Filter by coin if specified
            if coin:
                batch_fills = [f for f in batch_fills if f.coin == coin]
            
            all_fills.extend(batch_fills)
            
            # Check if we got less than max, meaning no more data
            if len(data) < MAX_FILLS_PER_REQUEST:
                break
            
            # Move start time to after the last fill for pagination
            # Guard against empty batch_fills
            if not batch_fills:
                break
            last_time = max(f.time for f in batch_fills)
            if last_time <= current_start:
                # No progress, break to avoid infinite loop
                break
            current_start = last_time + 1
            
            # Safety check for API limits
            if len(all_fills) >= MAX_RECENT_FILLS:
                logger.warning(
                    f"Reached max fills limit ({MAX_RECENT_FILLS}) for user {user}"
                )
                break

        # Sort by time ascending
        all_fills.sort(key=lambda f: f.time)
        
        return all_fills

    async def get_user_equity(self, user: str) -> float:
        """Get current account equity for a user."""
        payload = {
            "type": "clearinghouseState",
            "user": user,
        }
        
        data = await self._make_request("/info", payload)
        
        # Extract margin summary
        margin_summary = data.get("marginSummary", {})
        account_value = margin_summary.get("accountValue", "0")
        
        return float(account_value)

    async def get_user_equity_at_time(
        self, 
        user: str, 
        time_ms: int
    ) -> Optional[float]:
        """
        Get historical account equity for a user at a specific time.
        
        Note: Hyperliquid public API doesn't directly support historical equity.
        Returns None - callers should use current equity or alternative methods.
        """
        # Historical equity not available via public API
        logger.debug(
            f"Historical equity not available for user {user} at time {time_ms}"
        )
        return None

    async def get_user_deposits(
        self,
        user: str,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
    ) -> list[dict]:
        """
        Retrieve non-funding ledger updates (deposits, withdrawals, transfers).
        
        Uses the userNonFundingLedgerUpdates endpoint.
        """
        client = await self._get_client()
        
        payload = {
            "type": "userNonFundingLedgerUpdates",
            "user": user,
            "startTime": start_time_ms or 0,
        }
        
        if end_time_ms is not None:
            payload["endTime"] = end_time_ms
        
        data = await self._make_request("/info", payload)
        return data if data else []

    async def get_clearinghouse_state(self, user: str) -> dict:
        """
        Retrieve user's perpetuals account summary with current positions.
        
        Uses the clearinghouseState endpoint.
        """
        payload = {
            "type": "clearinghouseState",
            "user": user,
        }
        
        data = await self._make_request("/info", payload)
        return data if data else {}

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
