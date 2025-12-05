import logging
from decimal import Decimal
from datetime import datetime, timezone
import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError

try:
    from .celery_app import app
except Exception:
    # Fallback when module is executed without package context
    from celery_app import app
from models import (
    Order, Transaction, CreditsHistory,
    TransactionTypeEnum, CreditReasonEnum
)
from db import init_db_for_worker
from services.portfolio import (
    update_or_create_portfolio,
    update_portfolio_on_sell,
    get_user_by_id
)
from binance_config import client
from binance.exceptions import BinanceAPIException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trading fee constant
TRADING_FEE_RATE = Decimal("0.001")


_worker_loop = None
_worker_loop_thread = None

def _ensure_worker_loop():
    """Ensure a persistent event loop running in a background thread for this worker process.

    Using a persistent loop avoids creating and closing event loops per task, which can
    leave Motor/Beanie tied to a closed loop and cause 'Event loop is closed' errors.
    """
    global _worker_loop, _worker_loop_thread
    if _worker_loop is None:
        _worker_loop = asyncio.new_event_loop()
        _worker_loop_thread = threading.Thread(target=_worker_loop.run_forever, daemon=True)
        _worker_loop_thread.start()
    return _worker_loop


@app.task(name="process_trade_task", bind=True, max_retries=3, default_retry_delay=10)
def process_trade_task(self, order_data: dict):
    """Celery task wrapper that schedules the async worker on a persistent event loop.

    This schedules `worker_main` on a background event loop (thread) and waits for the
    result using `run_coroutine_threadsafe`. This keeps Motor/Beanie initializations bound
    to a long-lived loop and avoids `RuntimeError: Event loop is closed` on subsequent tasks.
    """
    try:
        logger.info(f"🎯 Received trade task: {order_data}")
        loop = _ensure_worker_loop()
        future = asyncio.run_coroutine_threadsafe(worker_main(order_data), loop)
        # Wait for completion; allow a generous timeout in case of network delays
        return future.result(timeout=300)
    except FutureTimeoutError as exc:
        logger.exception(f"❌ Celery trade task timeout: {exc}")
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception(f"❌ Celery trade task top-level error: {exc}")
        raise self.retry(exc=exc)


async def worker_main(order_data: dict):
    """
    Async worker function that executes the trade logic.
    """
    now = datetime.now(timezone.utc)

    user_id = order_data["user_id"]
    symbol = order_data["symbol"].upper()
    side = order_data["side"].upper()
    order_type = order_data["order_type"].upper()
    quantity = Decimal(str(order_data["quantity"]))
    price = Decimal(str(order_data.get("price") or "0"))

    logger.info(f"⚡ Starting worker_main for user {user_id}, {side} {quantity} {symbol} ({order_type})")

    try:
        # ✅ Initialize DB
        await init_db_for_worker()
        logger.info("✅ DB initialized")

        # ✅ Fetch User
        current_user = await get_user_by_id(user_id)
        if not current_user:
            logger.error(f"❌ User not found: {user_id}")
            return

        # --- PLACE ORDER ON BINANCE ---

        order_data_resp, fill_price = await place_order_on_binance(
            symbol, side, order_type, quantity, price
        )

        # --- RECORD ORDER IN DB ---

        order_doc = await record_order(
            user_id, symbol, side, order_type, quantity,
            fill_price, order_data_resp, now
        )

        if order_data_resp["status"] != "FILLED":
            logger.warning(f"⚠️ Order not FILLED immediately. Status: {order_data_resp['status']}")
            return

        # --- RECORD TRANSACTION & UPDATE ACCOUNTS ---

        await handle_filled_order(
            current_user, order_doc, symbol, side, quantity,
            fill_price, order_data_resp, now
        )

        logger.info(f"✅ Trade task complete for user {user_id}")

    except Exception as e:
        logger.exception(f"❌ Celery worker error: {e}")


async def place_order_on_binance(symbol, side, order_type, quantity, price):
    """
    Handles placing the order on Binance and returns (response, fill_price).
    """
    # Fetch symbol filters to validate minNotional and stepSize
    try:
        symbol_info = client.get_symbol_info(symbol)
    except Exception:
        symbol_info = None

    min_notional = None
    step_size = None
    if symbol_info and "filters" in symbol_info:
        for f in symbol_info["filters"]:
            if f.get("filterType") in ("MIN_NOTIONAL", "NOTIONAL"):
                # some Binance versions use MIN_NOTIONAL or NOTIONAL
                if f.get("minNotional"):
                    min_notional = Decimal(str(f.get("minNotional")))
                elif f.get("notional"):
                    min_notional = Decimal(str(f.get("notional")))
            if f.get("filterType") == "LOT_SIZE":
                step_size = Decimal(str(f.get("stepSize"))) if f.get("stepSize") else None

    def quantize_to_step(qty, step):
        if not step:
            return qty
        # round down to nearest step size
        try:
            return (qty // step) * step
        except Exception:
            return qty

    if order_type == "LIMIT":
        if not price:
            raise ValueError("LIMIT orders require a price")

        ticker = client.get_symbol_ticker(symbol=symbol)
        live_price = Decimal(ticker["price"])

        is_fillable = (live_price <= price if side == "BUY" else live_price >= price)

        if is_fillable:
            logger.info(f"✅ LIMIT condition met (live: {live_price}, target: {price}) - placing MARKET")
            qty_to_place = quantize_to_step(quantity, step_size)
            # Validate min notional (quote quantity)
            if min_notional is not None:
                notional = qty_to_place * live_price
                if notional < min_notional:
                    raise ValueError(f"Order notional {notional} is below minimum {min_notional} for {symbol}")

            order_payload = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": float(qty_to_place)
            }
            logger.info(
                "Placing MARKET order (LIMIT condition met): symbol=%s qty_to_place=%s step_size=%s min_notional=%s notional=%s payload=%s",
                symbol, str(qty_to_place), str(step_size), str(min_notional), str(qty_to_place * live_price), order_payload
            )
            try:
                resp = client.create_order(**order_payload)
            except BinanceAPIException as exc:
                logger.error(f"BinanceAPIException placing MARKET order: {exc}")
                raise
            return resp, Decimal(resp["fills"][0]["price"])
        else:
            logger.info("⌛ LIMIT condition not met - placing LIMIT GTC")
            qty_to_place = quantize_to_step(quantity, step_size)
            if min_notional is not None:
                notional = qty_to_place * Decimal(str(price))
                if notional < min_notional:
                    raise ValueError(f"Order notional {notional} is below minimum {min_notional} for {symbol}")

            order_payload = {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": float(qty_to_place),
                "price": float(price)
            }
            logger.info(
                "Placing LIMIT order: symbol=%s qty_to_place=%s step_size=%s min_notional=%s notional=%s payload=%s",
                symbol, str(qty_to_place), str(step_size), str(min_notional), str(qty_to_place * Decimal(str(price))), order_payload
            )
            try:
                resp = client.create_order(**order_payload)
            except BinanceAPIException as exc:
                logger.error(f"BinanceAPIException placing LIMIT order: {exc}")
                raise
            return resp, price

    else:
        logger.info("✅ MARKET order")
        logger.info("Preparing MARKET order: quantizing to step size and validating minNotional")
        qty_to_place = quantize_to_step(quantity, step_size)
        # Validate min notional using a live price
        try:
            live_price = Decimal(client.get_symbol_ticker(symbol=symbol)["price"])
        except Exception:
            live_price = None

        if min_notional is not None and live_price is not None:
            notional = qty_to_place * live_price
            if notional < min_notional:
                raise ValueError(f"Order notional {notional} is below minimum {min_notional} for {symbol}")

        order_payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": float(qty_to_place)
        }
        logger.info(
            "Placing MARKET order: symbol=%s qty_to_place=%s step_size=%s min_notional=%s notional=%s payload=%s",
            symbol, str(qty_to_place), str(step_size), str(min_notional), str((live_price * qty_to_place) if live_price is not None else None), order_payload
        )
        try:
            resp = client.create_order(**order_payload)
        except BinanceAPIException as exc:
            logger.error(f"BinanceAPIException placing MARKET order: {exc}")
            raise
        return resp, Decimal(resp["fills"][0]["price"])


async def record_order(user_id, symbol, side, order_type, quantity, fill_price, order_data_resp, now):
    """
    Creates and saves the Order document in DB.
    """
    order_doc = Order(
        user=user_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=fill_price,
        status=order_data_resp["status"],
        order_id=str(order_data_resp.get("orderId")) if order_data_resp.get("orderId") else None,
        created_at=now,
        executed_at=now if order_data_resp["status"] == "FILLED" else None
    )
    await order_doc.save()
    logger.info(f"✅ Order saved: {order_doc.id}")
    return order_doc


async def handle_filled_order(current_user, order_doc, symbol, side, quantity, fill_price, order_data_resp, now):
    """
    Handles transaction recording and portfolio/credits update for FILLED orders.
    """
    if order_doc.order_type == "MARKET":
        fill = order_data_resp["fills"][0]
        qty = Decimal(fill["qty"])
        fill_price = Decimal(fill["price"])
    else:
        qty = quantity

    total = qty * fill_price
    trading_fee = (total * TRADING_FEE_RATE).quantize(Decimal("0.00000001"))
    total_with_fee = total + trading_fee if side == "BUY" else total - trading_fee

    # ✅ Record Transaction
    txn = Transaction(
        user=str(current_user.id),
        order=order_doc.id,
        symbol=symbol,
        transaction_type=TransactionTypeEnum(side.capitalize()),
        quantity=qty,
        price=fill_price,
        total_amount=total,
        created_at=now
    )
    await txn.save()
    logger.info(f"✅ Transaction saved: {txn.id}")

    # ✅ Update Portfolio & Credits
    if side == "BUY":
        if current_user.credits < total_with_fee:
            raise ValueError("Not enough credits to buy (including fee)")

        await update_or_create_portfolio(current_user, symbol, qty, fill_price)
        current_user.credits -= total_with_fee

    elif side == "SELL":
        result = await update_portfolio_on_sell(current_user.id, symbol, qty)
        logger.info(f"✅ Portfolio updated on sell: {result}")
        current_user.credits += total_with_fee

    current_user.updated_at = now
    await current_user.save()

    # ✅ Credits History
    history = CreditsHistory(
        user=current_user,
        change_amount=-total_with_fee if side == "BUY" else total_with_fee,
        reason=CreditReasonEnum.trade,
        balance_after=current_user.credits,
        metadata={
            "symbol": symbol,
            "qty": str(qty),
            "price": str(fill_price),
            "trading_fee": str(trading_fee)
        }
    )
    await history.save()
    logger.info(f"✅ Credits history saved: {history.id}")
