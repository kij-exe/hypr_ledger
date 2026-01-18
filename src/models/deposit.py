"""Deposit model for API responses."""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Deposit(BaseModel):
    """A single deposit transaction."""
    model_config = ConfigDict(populate_by_name=True)
    
    timeMs: int = Field(description="Timestamp in milliseconds")
    amount: float = Field(description="Deposit amount in USD")
    hash: str = Field(description="Transaction hash")
    txType: str = Field(description="Transaction type (e.g., 'deposit')")


class DepositResult(BaseModel):
    """
    Deposit tracking result for a user.
    
    Enables filtering users who reloaded capital during competition window.
    """
    model_config = ConfigDict(populate_by_name=True)
    
    totalDeposits: float = Field(description="Total deposited amount in USD")
    depositCount: int = Field(description="Number of deposit transactions")
    deposits: list[Deposit] = Field(description="List of individual deposits")
