"""API routes for stock data management (download, import, query)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.schemas import DownloadRequest, OHLCVBar, StockInfo
from app.services.data_manager_async import DataManager

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/stocks", response_model=list[StockInfo])
async def list_stocks(db: AsyncSession = Depends(get_db)):
    """List all stocks with stored data."""
    data_manager = DataManager(db)
    stocks = await data_manager.list_stocks()
    await db.commit()
    return stocks


@router.get("/stocks/{symbol}", response_model=StockInfo)
async def get_stock(symbol: str, db: AsyncSession = Depends(get_db)):
    """Get stock metadata by symbol."""
    data_manager = DataManager(db)
    info = await data_manager.get_stock_info(symbol)
    await db.commit()

    if not info:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")
    return info


@router.get("/stocks/{symbol}/ohlcv", response_model=list[OHLCVBar])
async def get_ohlcv(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Query OHLCV data for a stock within a date range."""
    data_manager = DataManager(db)
    df = await data_manager.get_ohlcv(symbol, start_date, end_date)
    await db.commit()

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for '{symbol}'")

    bars = []
    for date_idx, row in df.iterrows():
        bars.append(
            OHLCVBar(
                date=date_idx.strftime("%Y-%m-%d"),
                open=round(row["open"], 4),
                high=round(row["high"], 4),
                low=round(row["low"], 4),
                close=round(row["close"], 4),
                volume=int(row["volume"]),
            )
        )
    return bars


@router.get("/stocks/{symbol}/date-range")
async def get_date_range(symbol: str, db: AsyncSession = Depends(get_db)):
    """Get the date range of stored data for a stock."""
    data_manager = DataManager(db)
    result = await data_manager.get_date_range(symbol)
    await db.commit()

    if not result:
        raise HTTPException(status_code=404, detail=f"No data found for '{symbol}'")

    return {"symbol": symbol, "start_date": result[0], "end_date": result[1]}


@router.post("/download")
async def download_stock(request: DownloadRequest, db: AsyncSession = Depends(get_db)):
    """Download stock data from yfinance and store in database."""
    data_manager = DataManager(db)

    try:
        rows = await data_manager.download_stock_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            period=request.period,
        )
        await db.commit()

        return {
            "symbol": request.symbol.upper(),
            "rows_imported": rows,
            "message": f"Successfully downloaded {rows} rows for {request.symbol.upper()}",
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}")


@router.post("/import-csv")
async def import_csv(
    symbol: str = Form(...),
    name: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import OHLCV data from a CSV file upload."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    data_manager = DataManager(db)

    try:
        content = (await file.read()).decode("utf-8")
        rows = await data_manager.import_csv(symbol, content, name=name)
        await db.commit()

        return {
            "symbol": symbol.upper(),
            "rows_imported": rows,
            "message": f"Successfully imported {rows} rows for {symbol.upper()}",
        }
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/stocks/{symbol}")
async def delete_stock(symbol: str, db: AsyncSession = Depends(get_db)):
    """Delete all data for a stock."""
    data_manager = DataManager(db)
    deleted = await data_manager.delete_stock_data(symbol)

    if not deleted:
        await db.rollback()
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")

    await db.commit()
    return {"message": f"Deleted all data for {symbol.upper()}"}
