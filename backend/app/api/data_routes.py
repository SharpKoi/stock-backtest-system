"""API routes for stock data management (download, import, query)."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import DownloadRequest, OHLCVBar, StockInfo
from app.services.data_manager import DataManager

router = APIRouter(prefix="/api/data", tags=["data"])

data_manager = DataManager()


@router.get("/stocks", response_model=list[StockInfo])
def list_stocks():
    """List all stocks with stored data."""
    return data_manager.list_stocks()


@router.get("/stocks/{symbol}", response_model=StockInfo)
def get_stock(symbol: str):
    """Get stock metadata by symbol."""
    info = data_manager.get_stock_info(symbol)
    if not info:
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found")
    return info


@router.get("/stocks/{symbol}/ohlcv", response_model=list[OHLCVBar])
def get_ohlcv(symbol: str, start_date: str | None = None,
              end_date: str | None = None):
    """Query OHLCV data for a stock within a date range."""
    df = data_manager.get_ohlcv(symbol, start_date, end_date)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for '{symbol}'"
        )
    bars = []
    for date_idx, row in df.iterrows():
        bars.append(OHLCVBar(
            date=date_idx.strftime("%Y-%m-%d"),
            open=round(row["open"], 4),
            high=round(row["high"], 4),
            low=round(row["low"], 4),
            close=round(row["close"], 4),
            volume=int(row["volume"]),
        ))
    return bars


@router.get("/stocks/{symbol}/date-range")
def get_date_range(symbol: str):
    """Get the date range of stored data for a stock."""
    result = data_manager.get_date_range(symbol)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for '{symbol}'"
        )
    return {"symbol": symbol, "start_date": result[0], "end_date": result[1]}


@router.post("/download")
def download_stock(request: DownloadRequest):
    """Download stock data from yfinance and store in database."""
    try:
        rows = data_manager.download_stock_data(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            period=request.period,
        )
        return {
            "symbol": request.symbol.upper(),
            "rows_imported": rows,
            "message": f"Successfully downloaded {rows} rows for {request.symbol.upper()}"
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}")


@router.post("/import-csv")
async def import_csv(symbol: str = Form(...),
                     name: str = Form(None),
                     file: UploadFile = File(...)):
    """Import OHLCV data from a CSV file upload."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = (await file.read()).decode("utf-8")
        rows = data_manager.import_csv(symbol, content, name=name)
        return {
            "symbol": symbol.upper(),
            "rows_imported": rows,
            "message": f"Successfully imported {rows} rows for {symbol.upper()}"
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/stocks/{symbol}")
def delete_stock(symbol: str):
    """Delete all data for a stock."""
    deleted = data_manager.delete_stock_data(symbol)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Stock '{symbol}' not found"
        )
    return {"message": f"Deleted all data for {symbol.upper()}"}
