from binance_config import client as binance_client
from decimal import Decimal
from datetime import datetime, timezone
from bson.decimal128 import Decimal128
from models import CryptoPair
import asyncio


def to_decimal128(val):
    if val is None:
        return None
    if isinstance(val, Decimal128):
        return val
    return Decimal128(str(val))




async def fetch_and_store_binance_symbols():
    """Fetch exchange symbols from Binance and insert/update `CryptoPair` documents.

    Binance client calls are blocking; use `asyncio.to_thread` so we don't block the
    event loop during startup.
    """
    # fetch exchange info in thread
    # If Binance client isn't available, skip fetching symbols
    try:
        if not getattr(binance_client, "is_available", lambda: False)():
            print("Binance client not available — skipping fetch_and_store_binance_symbols")
            return
    except Exception:
        print("Error checking Binance client availability — skipping fetch_and_store_binance_symbols")
        return

    exchange_info = await asyncio.to_thread(binance_client.get_exchange_info)
    symbols = exchange_info.get("symbols", [])

    for s in symbols:
        if s["status"] != "TRADING" or not s.get("isSpotTradingAllowed", False):
            continue

        symbol = s["symbol"]
        base_asset = s["baseAsset"]
        quote_asset = s["quoteAsset"]
        status = s["status"]

        if not symbol.endswith("USDT"):
            continue

        # fetch ticker in thread
        price_data = await asyncio.to_thread(binance_client.get_symbol_ticker, symbol=symbol)
        price = to_decimal128(price_data.get("price")) if "price" in price_data else None
        now = datetime.now(timezone.utc)

        filters = {f["filterType"]: f for f in s.get("filters", [])}
        lot_size = filters.get("LOT_SIZE", {})
        price_filter = filters.get("PRICE_FILTER", {})

        min_qty = to_decimal128(lot_size.get("minQty", "0")) if "minQty" in lot_size else None
        step_size = to_decimal128(lot_size.get("stepSize", "0")) if "stepSize" in lot_size else None
        tick_size = to_decimal128(price_filter.get("tickSize", "0")) if "tickSize" in price_filter else None

        existing = await CryptoPair.find_one(CryptoPair.symbol == symbol)

        if existing:
            await existing.set({
                CryptoPair.last_price: price,
                CryptoPair.last_price_time: now,
                CryptoPair.status: status,
                CryptoPair.min_qty: min_qty,
                CryptoPair.step_size: step_size,
                CryptoPair.tick_size: tick_size,
            })
        else:
            doc = CryptoPair(
                symbol=symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                status=status,
                last_price=price,
                last_price_time=now,
                min_qty=min_qty,
                step_size=step_size,
                tick_size=tick_size,
                created_at=now,
            )
            await doc.insert()
