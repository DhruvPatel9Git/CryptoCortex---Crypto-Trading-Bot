from fastapi import APIRouter, HTTPException, Query, Depends
from fetch_binance.fetch_ohlc import fetch_historical_data  
from models import Candle
from datetime import timedelta, datetime, timezone
from typing import List
from db import get_current_user
router = APIRouter(tags=["Candles"])

VALID_INTERVALS = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M"
}

@router.post("/fetch_historical_candles")
async def trigger_candle_fetch(days_back: int = 30, interval: str = "1d", current_user: dict = Depends(get_current_user)):
    """Trigger fetching of historical candle data for all symbols from Binance API.
    Returns 400 for invalid interval, 500 for unexpected errors."""
    if interval not in VALID_INTERVALS:
        raise HTTPException(status_code=400, detail="Invalid interval. Use one of: " + ", ".join(VALID_INTERVALS.keys()))
    try:
        await fetch_historical_data(interval=VALID_INTERVALS[interval], days_back=days_back)
        return {"message": f"Historical candle data fetched for last {days_back} days using {interval} interval."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")

@router.get("/candles/{symbol}")
async def get_ohlc_data(symbol: str, days_back: int = Query(30, ge=1)):
    symbol = symbol.upper()
    # FastAPI's dependency injection wraps defaults in Query; when calling directly in tests, coerce.
    if not isinstance(days_back, int):
        days_back = int(getattr(days_back, "default", 30))
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    candles = await Candle.find({
        "symbol": symbol,
        "candle_time": {"$gte": start_time, "$lte": end_time}
    }).sort("candle_time").to_list()

    print(f"{symbol} → Found {len(candles)} candles")

    return [
        {
            "symbol": c.symbol,
            "interval": c.interval,
            "time": c.candle_time,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume)
        }
        for c in candles
    ]
