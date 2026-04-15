"""Startup logic: auto-seed database and parquet data on first boot."""
import pathlib
from app.seed import create_admin, generate_data


async def maybe_seed(parquet_dir: str = "/data/parquet") -> None:
    """Create admin user and generate synthetic data if not already present.

    Safe to call on every startup — create_admin is idempotent, and
    generate_data only runs when no .parquet files exist.
    """
    await create_admin()
    if not any(pathlib.Path(parquet_dir).glob("*.parquet")):
        generate_data()
