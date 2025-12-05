from models import Order, User, Transaction, CreditsHistory, TransactionTypeEnum
from services.portfolio import update_or_create_portfolio, update_portfolio_on_sell
from binance_config import client
from fastapi import Request
from datetime import datetime, timezone
from decimal import Decimal
import asyncio
from bson import Decimal128

def decimal128_to_decimal(value):
    if isinstance(value, Decimal128):
        return value.to_decimal()
    return Decimal(str(value))  

async def settle_filled_limit_orders():
    print("Running limit order settlement job...")

    open_orders = await Order.find(Order.status == "NEW").to_list()
    print(f"Found {len(open_orders)} open orders")

    for order in open_orders:
        
        try:
            await order.fetch_link(Order.user)
            user = order.user
            binance_order = client.get_order(
                symbol=order.symbol,
                orderId=order.order_id
            )

            if binance_order["status"] == "FILLED":
                print(f"Order {order.id} is FILLED on Binance")

                now = datetime.now(timezone.utc)
                
                fills = binance_order.get("fills", [])

                total_cost = Decimal("0")
                total_qty = Decimal("0")
                avg_price = Decimal("0")

                if fills:
                    for fill in fills:
                        qty = Decimal(fill["qty"])
                        price = Decimal(fill["price"])
                        total = qty * price

                        total_cost += total
                        total_qty += qty

                        await Transaction.insert(Transaction(
                            user=user.id,
                            order=order.id,
                            symbol=order.symbol,
                            transaction_type=TransactionTypeEnum(order.side.capitalize()),
                            quantity=qty,
                            price=price,
                            total_amount=total,
                            created_at=now
                        ))

                # Convert Decimal128 to Decimal for calculations
                if total_qty == 0:
                    total_qty = decimal128_to_decimal(order.quantity)
                    avg_price = decimal128_to_decimal(order.price) if order.price else Decimal("0")
                    total_cost = total_qty * avg_price
                else:
                    avg_price = total_cost / total_qty if total_qty > 0 else Decimal("0")

                # Convert user credits to Decimal for comparison
                user_credits = decimal128_to_decimal(user.credits)

                if order.side == "BUY":
                    if user_credits < total_cost:
                        print(f"User {user.id} doesn't have enough credits for settlement")
                        continue

                    await update_or_create_portfolio(user.id, order.symbol, total_qty, avg_price)
                    
                    # Update user credits
                    new_credits = user_credits - total_cost
                    user.credits = new_credits
                    await user.save()

                    await CreditsHistory.insert(CreditsHistory(
                        user=user,
                        change_amount=-total_cost,
                        reason="Trade",
                        balance_after=new_credits,
                        metadata={"symbol": order.symbol, "qty": str(total_qty), "price": str(avg_price)}
                    ))

                elif order.side == "SELL":
                    await update_portfolio_on_sell(user.id, order.symbol, total_qty)
                    
                    # Update user credits
                    new_credits = user_credits + total_cost
                    user.credits = new_credits
                    await user.save()

                    await CreditsHistory.insert(CreditsHistory(
                        user=user,
                        change_amount=total_cost,
                        reason="trade",
                        balance_after=new_credits,
                        metadata={"symbol": order.symbol, "qty": str(total_qty), "price": str(avg_price)}
                    ))

                order.status = "FILLED"
                order.executed_at = now
                await order.save()

        except Exception as e:
            print(f"Error processing order {order.id}: {e}")
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc()


            # Celery task wrapper for running this periodic job under Celery
            try:
                from celery_app import app

                @app.task(name="fetch_binance.background_jobs.settle_filled_limit_orders_task", bind=True, max_retries=3, default_retry_delay=10)
                def settle_filled_limit_orders_task(self):
                    """Celery wrapper that runs the async settle_filled_limit_orders function."""
                    try:
                        import asyncio as _asyncio
                        return _asyncio.run(settle_filled_limit_orders())
                    except Exception as exc:
                        # Let Celery handle retries
                        raise self.retry(exc=exc)
            except Exception:
                # If celery_app isn't available (e.g., import-time during some tests), skip wrapper creation
                pass