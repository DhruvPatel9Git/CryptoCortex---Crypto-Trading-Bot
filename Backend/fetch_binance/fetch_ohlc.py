from models import CryptoPair, Candle, CandleSyncTracker
from binance_config import client
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from binance.client import Client as BinanceClient

BINANCE_INTERVAL = BinanceClient.KLINE_INTERVAL_1DAY

async def fetch_historical_data(interval: str = BINANCE_INTERVAL, days_back: int = 30):
    pairs = await CryptoPair.find_all().to_list()
    now = datetime.now(timezone.utc)

    # Skip if Binance client not available
    try:
        from binance_config import client as _client
        if not getattr(_client, "is_available", lambda: False)():
            print("Binance client not available — skipping fetch_historical_data")
            return
    except Exception:
        print("Error checking Binance client availability — skipping fetch_historical_data")
        return

    for pair in pairs:
        try:
            # Get last fetched time from tracker
            tracker = await CandleSyncTracker.find_one({"symbol": pair.symbol})
            start_time = tracker.last_fetched if tracker else now - timedelta(days=30)
            end_time = now

            # Fetch new klines
            klines = client.get_historical_klines(
                symbol=pair.symbol,
                interval=interval,
                start_str=start_time.strftime('%d %b, %Y'),
                end_str=end_time.strftime('%d %b, %Y')
            )
            klines.sort(key=lambda k: k[0])
            candles_to_insert = []
            for kline in klines:
                candle_time = datetime.fromtimestamp(kline[0] / 1000)

                candle = Candle(
                    symbol=pair.symbol,
                    interval=interval,
                    open=Decimal(kline[1]),
                    high=Decimal(kline[2]),
                    low=Decimal(kline[3]),
                    close=Decimal(kline[4]),
                    volume=Decimal(kline[5]),
                    candle_time=candle_time
                )
                candles_to_insert.append(candle)

            if candles_to_insert:
                # Insert all new candles
                await Candle.insert_many(candles_to_insert)

                # Update tracker with latest candle time
                latest_time = max(c.candle_time for c in candles_to_insert)

                existing_tracker = await CandleSyncTracker.find_one({"symbol": pair.symbol})

                if existing_tracker:
                    existing_tracker.last_fetched = latest_time
                    await existing_tracker.save()
                else:
                    await CandleSyncTracker(symbol=pair.symbol, last_fetched=latest_time).insert()

        except Exception as e:
            print(f"❌ Error syncing {pair.symbol}: {e}")
