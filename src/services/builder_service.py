"""Builder service for fetching and matching builder-attributed trades."""

import httpx
import lz4.frame
import csv
from datetime import datetime, timezone, timedelta
from io import StringIO
from typing import Dict, List, Set, Optional
import logging

from src.models import Fill

logger = logging.getLogger(__name__)


class BuilderFill:
    """Represents a fill from builder CSV."""
    
    def __init__(self, data: Dict[str, str]):
        self.time_iso = data['time']
        self.time_ms = self._iso_to_ms(data['time'])
        self.user = data['user'].lower()
        self.coin = data['coin']
        self.side = data['side']  # "Bid" or "Ask"
        self.px = float(data['px'])
        self.sz = float(data['sz'])
        self.closed_pnl = float(data['closed_pnl'])
        self.builder_fee = float(data['builder_fee'])
    
    @staticmethod
    def _iso_to_ms(iso_time: str) -> int:
        """Convert ISO 8601 timestamp to milliseconds."""
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1000)


class BuilderService:
    """Service for fetching and matching builder-attributed trades."""
    
    def __init__(self, builder_address: str):
        """
        Initialize builder service.
        
        Args:
            builder_address: Target builder address
        """
        self.builder_address = builder_address.lower()
        self._csv_cache: Dict[str, List[BuilderFill]] = {}
    
    async def fetch_builder_csv(self, date: str) -> List[BuilderFill]:
        """
        Fetch and parse builder CSV file for a specific date.
        
        Args:
            date: Date in YYYYMMDD format
        
        Returns:
            List of BuilderFill objects
        """
        # Check cache first
        if date in self._csv_cache:
            logger.debug(f"Using cached builder CSV for {date}")
            return self._csv_cache[date]
        
        url = f"https://stats-data.hyperliquid.xyz/Mainnet/builder_fills/{self.builder_address}/{date}.csv.lz4"
        logger.info(f"Fetching builder CSV: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Decompress LZ4
                decompressed = lz4.frame.decompress(response.content)
                csv_text = decompressed.decode('utf-8')
                
                # Parse CSV
                reader = csv.DictReader(StringIO(csv_text))
                fills = [BuilderFill(row) for row in reader]
                
                # Cache the result
                self._csv_cache[date] = fills
                logger.info(f"Loaded {len(fills)} builder fills for {date}")
                
                return fills
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403 or e.response.status_code == 404:
                logger.warning(f"Builder CSV not available for {date}: {e}")
                # Cache empty list to avoid repeated failed requests
                self._csv_cache[date] = []
                return []
            raise
        except Exception as e:
            logger.error(f"Error fetching builder CSV for {date}: {e}")
            return []
    
    async def get_builder_fills_for_range(
        self,
        user: str,
        start_ms: int,
        end_ms: int
    ) -> List[BuilderFill]:
        """
        Get builder fills for a user within a time range.
        
        Args:
            user: User address
            start_ms: Start time in milliseconds
            end_ms: End time in milliseconds
        
        Returns:
            List of BuilderFill objects for this user
        """
        user = user.lower()
        
        # Calculate date range
        start_date = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        end_date = datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)
        
        # Fetch CSV files for each day in range
        all_fills: List[BuilderFill] = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y%m%d")
            day_fills = await self.fetch_builder_csv(date_str)
            
            # Filter for this user and time range
            user_fills = [
                fill for fill in day_fills
                if fill.user == user and start_ms <= fill.time_ms <= end_ms
            ]
            
            all_fills.extend(user_fills)
            current_date += timedelta(days=1)
        
        logger.info(f"Found {len(all_fills)} builder fills for user {user[:10]}...")
        return all_fills
    
    def match_fills(
        self,
        api_fills: List[Fill],
        builder_fills: List[BuilderFill]
    ) -> Set[int]:
        """
        Match API fills with builder fills and return indices of matched API fills.
        
        Args:
            api_fills: List of fills from Hyperliquid API
            builder_fills: List of fills from builder CSV
        
        Returns:
            Set of indices of API fills that match builder fills
        """
        matched_indices: Set[int] = set()
        unmatched_builder = set(range(len(builder_fills)))
        
        for api_idx, api_fill in enumerate(api_fills):
            # Parse API fill details
            api_time = api_fill.time
            api_coin = api_fill.coin
            api_px = float(api_fill.price)
            api_sz = abs(float(api_fill.signed_size))
            api_dir = api_fill.dir
            
            # Determine expected side from dir
            # Long positions: Open=Buy (Bid), Close=Sell (Ask)
            # Short positions: Open=Sell (Ask), Close=Buy (Bid)
            if 'Long' in api_dir:
                expected_side = 'Bid' if 'Open' in api_dir else 'Ask'
            elif 'Short' in api_dir:
                expected_side = 'Ask' if 'Open' in api_dir else 'Bid'
            else:
                expected_side = None
            
            # Try to find matching builder fill
            for builder_idx in list(unmatched_builder):
                builder_fill = builder_fills[builder_idx]
                
                # Match criteria:
                # - Time within 1 second (CSV has second precision)
                # - Same coin
                # - Same price (within 0.01%)
                # - Same size (within 0.01%)
                # - Side matches if known
                
                time_diff = abs(api_time - builder_fill.time_ms)
                px_diff = abs(api_px - builder_fill.px) / api_px if api_px > 0 else 0
                sz_diff = abs(api_sz - builder_fill.sz) / api_sz if api_sz > 0 else 0
                
                if (time_diff <= 1000 and  # Within 1 second
                    api_coin == builder_fill.coin and
                    px_diff < 0.0001 and  # Within 0.01%
                    sz_diff < 0.0001 and  # Within 0.01%
                    (expected_side is None or expected_side == builder_fill.side)):
                    
                    matched_indices.add(api_idx)
                    unmatched_builder.remove(builder_idx)
                    break
        
        match_rate = (len(matched_indices) / len(api_fills) * 100) if api_fills else 0
        logger.info(f"Matched {len(matched_indices)}/{len(api_fills)} fills ({match_rate:.1f}%)")
        
        return matched_indices
