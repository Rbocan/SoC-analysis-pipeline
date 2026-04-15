"""Tests for startup auto-seed logic."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_maybe_seed_calls_create_admin():
    """create_admin is always called regardless of parquet state."""
    with patch("app.startup.create_admin", new_callable=AsyncMock) as mock_admin, \
         patch("app.startup.generate_data"), \
         patch("app.startup.pathlib.Path") as mock_path_cls:
        mock_path_cls.return_value.glob.return_value = iter(["existing.parquet"])
        from app.startup import maybe_seed
        await maybe_seed()
        mock_admin.assert_called_once()


@pytest.mark.asyncio
async def test_maybe_seed_generates_data_when_no_parquet():
    """generate_data is called when no .parquet files exist."""
    with patch("app.startup.create_admin", new_callable=AsyncMock), \
         patch("app.startup.generate_data") as mock_gen, \
         patch("app.startup.pathlib.Path") as mock_path_cls:
        mock_path_cls.return_value.glob.return_value = iter([])
        from app.startup import maybe_seed
        await maybe_seed()
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_maybe_seed_skips_generate_when_parquet_exists():
    """generate_data is NOT called when parquet files already exist."""
    with patch("app.startup.create_admin", new_callable=AsyncMock), \
         patch("app.startup.generate_data") as mock_gen, \
         patch("app.startup.pathlib.Path") as mock_path_cls:
        mock_path_cls.return_value.glob.return_value = iter(["soc_a8.parquet"])
        from app.startup import maybe_seed
        await maybe_seed()
        mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_seed_uses_configured_parquet_dir():
    """maybe_seed passes the parquet_dir argument to Path."""
    with patch("app.startup.create_admin", new_callable=AsyncMock), \
         patch("app.startup.generate_data"), \
         patch("app.startup.pathlib.Path") as mock_path_cls:
        mock_path_cls.return_value.glob.return_value = iter([])
        from app.startup import maybe_seed
        await maybe_seed(parquet_dir="/custom/path")
        mock_path_cls.assert_called_with("/custom/path")
