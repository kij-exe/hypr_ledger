"""Leaderboard entry model for API responses."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LeaderboardEntry(BaseModel):
    """
    A single entry in the leaderboard.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    rank: int
    user: str
    metricValue: float = Field(description="Value of the ranking metric")
    tradeCount: int
    tainted: Optional[bool] = Field(default=None, description="Tainted flag for builder-only mode")
