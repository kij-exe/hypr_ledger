"""Application configuration."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    # API settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Hyperliquid API
    hyperliquid_api_url: str = "https://api.hyperliquid.xyz"
    
    # Builder-only mode (placeholder for future implementation)
    target_builder: str | None = None
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            hyperliquid_api_url=os.getenv(
                "HYPERLIQUID_API_URL", 
                "https://api.hyperliquid.xyz"
            ),
            target_builder=os.getenv("TARGET_BUILDER"),
        )
