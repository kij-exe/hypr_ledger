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
    
    # Builder-only mode configuration
    # Default builder address (can be overridden via TARGET_BUILDER env var)
    target_builder: str = "0x2868fc0d9786a740b491577a43502259efa78a39"
    
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
            target_builder=os.getenv(
                "TARGET_BUILDER",
                "0x2868fc0d9786a740b491577a43502259efa78a39"
            ),
        )
