"""Tests for the DataManager module."""

import pytest

from app.services.data_manager_async import DataManager


class TestStockMetadata:
    """Tests for stock metadata CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_or_create_stock_creates_new(self, data_manager: DataManager):
        stock_id = await data_manager.get_or_create_stock("AAPL", name="Apple Inc.")
        assert stock_id > 0

    @pytest.mark.asyncio
    async def test_get_or_create_stock_returns_existing(self, data_manager: DataManager):
        id1 = await data_manager.get_or_create_stock("AAPL")
        id2 = await data_manager.get_or_create_stock("AAPL")
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_symbol_is_uppercased(self, data_manager: DataManager):
        id1 = await data_manager.get_or_create_stock("aapl")
        id2 = await data_manager.get_or_create_stock("AAPL")
        assert id1 == id2

    @pytest.mark.asyncio
    async def test_list_stocks_empty(self, data_manager: DataManager):
        stocks = await data_manager.list_stocks()
        assert stocks == []

    @pytest.mark.asyncio
    async def test_list_stocks_after_create(self, data_manager: DataManager):
        await data_manager.get_or_create_stock("AAPL", name="Apple Inc.")
        await data_manager.get_or_create_stock("GOOGL", name="Alphabet Inc.")
        stocks = await data_manager.list_stocks()
        assert len(stocks) == 2
        symbols = [s.symbol for s in stocks]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols

    @pytest.mark.asyncio
    async def test_get_stock_info(self, data_manager: DataManager):
        await data_manager.get_or_create_stock("TSLA", name="Tesla", sector="Technology")
        info = await data_manager.get_stock_info("TSLA")
        assert info is not None
        assert info.symbol == "TSLA"
        assert info.name == "Tesla"
        assert info.sector == "Technology"

    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, data_manager: DataManager):
        info = await data_manager.get_stock_info("NONEXISTENT")
        assert info is None


class TestCSVImport:
    """Tests for CSV data import."""

    def test_import_csv_basic(self, data_manager: DataManager, sample_csv_content):
        rows = data_manager.import_csv("TEST", sample_csv_content, name="Test Stock")
        assert rows == 5

    def test_import_csv_creates_stock(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("NEWSTOCK", sample_csv_content)
        info = data_manager.get_stock_info("NEWSTOCK")
        assert info is not None
        assert info.symbol == "NEWSTOCK"

    def test_import_csv_data_retrievable(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        df = data_manager.get_ohlcv("TEST")
        assert len(df) == 5
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]

    def test_import_csv_invalid_columns(self, data_manager: DataManager):
        bad_csv = "col1,col2\n1,2\n"
        with pytest.raises(ValueError, match="Missing required column"):
            data_manager.import_csv("TEST", bad_csv)

    def test_import_csv_upsert(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        data_manager.import_csv("TEST", sample_csv_content)
        df = data_manager.get_ohlcv("TEST")
        assert len(df) == 5  # No duplicates


class TestOHLCVQuery:
    """Tests for OHLCV data querying."""

    def test_get_ohlcv_empty(self, data_manager: DataManager):
        df = data_manager.get_ohlcv("NONEXISTENT")
        assert df.empty

    def test_get_ohlcv_with_date_filter(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        df = data_manager.get_ohlcv("TEST", start_date="2024-01-03", end_date="2024-01-05")
        assert len(df) == 3

    def test_get_ohlcv_start_date_only(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        df = data_manager.get_ohlcv("TEST", start_date="2024-01-04")
        assert len(df) == 3

    def test_get_date_range(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        result = data_manager.get_date_range("TEST")
        assert result is not None
        assert result[0] == "2024-01-02"
        assert result[1] == "2024-01-08"

    def test_get_date_range_empty(self, data_manager: DataManager):
        result = data_manager.get_date_range("NONEXISTENT")
        assert result is None


class TestDeleteStock:
    """Tests for stock data deletion."""

    def test_delete_stock_data(self, data_manager: DataManager, sample_csv_content):
        data_manager.import_csv("TEST", sample_csv_content)
        result = data_manager.delete_stock_data("TEST")
        assert result is True
        assert data_manager.get_ohlcv("TEST").empty
        assert data_manager.get_stock_info("TEST") is None

    def test_delete_nonexistent(self, data_manager: DataManager):
        result = data_manager.delete_stock_data("NONEXISTENT")
        assert result is False
