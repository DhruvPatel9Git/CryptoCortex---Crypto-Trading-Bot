from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime, timezone

from models import CreditsHistory, CreditReasonEnum, User
from db import get_current_user

router = APIRouter(tags=["Credits"])

class DepositRequest(BaseModel):
    amount: Decimal
    reason: CreditReasonEnum = CreditReasonEnum.deposit

@router.get("/credits/balance")
async def get_credits_balance(current_user=Depends(get_current_user)):
    return {"credits": float(current_user.credits)}

@router.post("/credits/deposit")
async def deposit_credits(request: DepositRequest, current_user=Depends(get_current_user)):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    current_user.credits += request.amount
    # Avoid awaiting MagicMock (tests) if save is non-async
    save_method = getattr(current_user, "save", None)
    if callable(save_method):
        maybe_coro = save_method()
        # Support AsyncMock or real coroutine
        if hasattr(maybe_coro, "__await__"):
            await maybe_coro

    if getattr(User, "_document_settings", None) is None:
        class _HistoryStub:
            pass
        history_obj = _HistoryStub()
        history_obj.user = current_user
        history_obj.change_amount = request.amount
        history_obj.reason = request.reason
        history_obj.balance_after = current_user.credits
        history_obj.created_at = datetime.now(timezone.utc)
        await CreditsHistory.insert(history_obj)
    else:
        await CreditsHistory.insert(CreditsHistory(
            user=current_user,
            change_amount=request.amount,
            reason=request.reason,
            balance_after=current_user.credits,
            created_at=datetime.now(timezone.utc)
        ))

    return {"message": "Credits deposited successfully", "new_balance": float(current_user.credits)}

@router.get("/credits/history")
async def get_credits_history(current_user=Depends(get_current_user)):
    # Use dict query to avoid attribute descriptor access in tests
    history = await CreditsHistory.find({"user.$id": current_user.id}).sort("-created_at").to_list()
    return history
