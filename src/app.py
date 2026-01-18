"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import Config
from src.datasources import HyperliquidDataSource
from src.api import router
from src.api.dependencies import set_datasource

logger = logging.getLogger(__name__)


def create_app(config: Config | None = None) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        config: Application configuration. If None, loads from environment.
        
    Returns:
        Configured FastAPI application
    """
    if config is None:
        config = Config.from_env()
    
    # Create datasource
    datasource = HyperliquidDataSource(api_url=config.hyperliquid_api_url)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler for startup/shutdown."""
        # Startup
        logger.info("Starting Hyperliquid Trade Ledger API")
        logger.info(f"Using Hyperliquid API: {config.hyperliquid_api_url}")
        if config.target_builder:
            logger.info(f"Builder-only mode enabled for: {config.target_builder}")
        
        set_datasource(datasource)
        
        yield
        
        # Shutdown
        logger.info("Shutting down...")
        await datasource.close()
    
    app = FastAPI(
        title="Hyperliquid Trade Ledger API",
        description="Trade history, position history, and PnL tracking for Hyperliquid",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Include API routes
    app.include_router(router)
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app
