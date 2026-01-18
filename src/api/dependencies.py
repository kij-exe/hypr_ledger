"""FastAPI dependencies for dependency injection."""

from src.datasources import DataSource

# Global datasource instance - initialized at app startup
_datasource: DataSource | None = None


def set_datasource(datasource: DataSource) -> None:
    """Set the global datasource instance."""
    global _datasource
    _datasource = datasource


def get_datasource() -> DataSource:
    """Get the global datasource instance for dependency injection."""
    if _datasource is None:
        raise RuntimeError("DataSource not initialized. Call set_datasource() first.")
    return _datasource
