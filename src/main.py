"""Application entry point."""

import logging
import uvicorn

from src.config import Config
from src.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    """Run the application."""
    config = Config.from_env()
    app = create_app(config)
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
    )


if __name__ == "__main__":
    main()
