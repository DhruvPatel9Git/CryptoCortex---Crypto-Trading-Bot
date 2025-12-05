from fastapi import APIRouter, HTTPException, Depends
from models import OrderRequest
from db import get_current_user
import re
from chatbot.candle_context_builder import get_candlestick_context
from chatbot.order_context_builder import is_order_history_request, get_order_history_context
from chatbot.qa_utils_safe import question_answer
from chatbot.symbol_extractor import extract_symbol_and_date
from datetime import datetime, time
try:
    from ..trade_tasks import process_trade_task  # ✅ import your Celery task
except Exception:
    from trade_tasks import process_trade_task  # fallback for top-level imports

router = APIRouter()

def expand_date_to_full_day(date_obj):
    start = datetime.combine(date_obj, time.min)
    end = datetime.combine(date_obj, time.max)
    return start, end

def parse_trade_command(text):
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)

    market_pattern = r"^(buy|sell)\s+([\d.]+)\s+([a-z]+)\s+at\s+market\s+price$"
    limit_pattern = r"^(buy|sell)\s+([\d.]+)\s+([a-z]+)\s+at\s+limit\s+price\s+([\d.]+)$"

    market_match = re.match(market_pattern, text)
    if market_match:
        side, qty, symbol = market_match.groups()
        return {
            "side": side.upper(),
            "quantity": float(qty),
            "symbol": symbol.upper(),
            "order_type": "MARKET",
            "price": None
        }

    limit_match = re.match(limit_pattern, text)
    if limit_match:
        side, qty, symbol, price = limit_match.groups()
        return {
            "side": side.upper(),
            "quantity": float(qty),
            "symbol": symbol.upper(),
            "order_type": "LIMIT",
            "price": float(price)
        }

    return None

@router.post("/qa")
async def qa_main(body: dict, current_user=Depends(get_current_user)):
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Missing question in request.")

    # ✅ Check if it's a trade command
    trade_data = parse_trade_command(question)
    if trade_data:
        try:
            # Build the payload for the task queue (Celery)
            task_payload = {
                "user_id": str(current_user.id),
                "symbol": trade_data["symbol"],
                "side": trade_data["side"],
                "order_type": trade_data["order_type"],
                "quantity": str(trade_data["quantity"]),
                "price": str(trade_data["price"]) if trade_data["price"] else None
            }

            # ✅ Enqueue with task queue (support legacy `.send()` for tests)
            enqueue_fn = getattr(process_trade_task, "send", None)
            if callable(enqueue_fn):
                enqueue_fn(task_payload)
            else:
                process_trade_task.delay(task_payload)

            return {
                "question": question,
                "answer": f" Order received! Queued to place {trade_data['side']} {trade_data['quantity']} {trade_data['symbol']} at {trade_data['order_type']}!"
            }

        except Exception as e:
            return {"error": f"❌ Failed to queue trade task: {str(e)}"}

    # ✅ Check for order history
    if is_order_history_request(question):
        context = await get_order_history_context(current_user)
        if not context:
            return {"error": "You have no recent orders."}
        # context may be list[str] or a single str
        if isinstance(context, list):
            answer_text = "\n".join(context)
            snippet_source = "\n".join(context)
        else:
            answer_text = context
            snippet_source = context
        return {
            "question": question,
            "answer": answer_text,
            "context_snippet": snippet_source[:500] + "..." if len(snippet_source) > 500 else snippet_source
        }

    # ✅ Else: candlestick data
    symbol, date = extract_symbol_and_date(question)
    if not symbol or not date:
        return {"error": "Sorry, I couldn't understand your question."}

    start_dt, end_dt = expand_date_to_full_day(date)
    context = await get_candlestick_context(symbol, start_dt, end_dt)
    if not context:
        return {"error": f"No candlestick data found for {symbol} on {date}."}

    answer = question_answer(question, context)
    return {
        "question": question,
        "answer": answer,
        "context_snippet": context[:500] + "..." if len(context) > 500 else context
    }
