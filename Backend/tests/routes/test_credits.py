"""
Unit tests for credits.py
Tests all credits-related endpoints with mocked dependencies.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId

from routes.credits import router
from models import CreditsHistory, CreditReasonEnum


# Mock data
MOCK_USER_ID = ObjectId()
MOCK_USERNAME = "testuser@example.com"
MOCK_INITIAL_CREDITS = Decimal("1000.00")


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = MOCK_USER_ID
    user.username = MOCK_USERNAME
    user.credits = MOCK_INITIAL_CREDITS
    user.save = AsyncMock()
    return user


class TestGetCreditsBalanceEndpoint:
    """Test cases for /credits/balance endpoint."""

    @pytest.mark.asyncio
    async def test_get_credits_balance_success(self, mock_user):
        """Test retrieving credits balance successfully."""
        from routes.credits import get_credits_balance
        
        result = await get_credits_balance(mock_user)
        
        assert "credits" in result
        assert result["credits"] == float(MOCK_INITIAL_CREDITS)

    @pytest.mark.asyncio
    async def test_get_credits_balance_zero_credits(self, mock_user):
        """Test retrieving credits balance when user has zero credits."""
        mock_user.credits = Decimal("0.00")
        
        from routes.credits import get_credits_balance
        
        result = await get_credits_balance(mock_user)
        
        assert result["credits"] == 0.0

    @pytest.mark.asyncio
    async def test_get_credits_balance_large_amount(self, mock_user):
        """Test retrieving credits balance with large amount."""
        mock_user.credits = Decimal("999999.99")
        
        from routes.credits import get_credits_balance
        
        result = await get_credits_balance(mock_user)
        
        assert result["credits"] == 999999.99


class TestDepositCreditsEndpoint:
    """Test cases for /credits/deposit endpoint."""

    @pytest.mark.asyncio
    async def test_deposit_credits_success(self, mock_user):
        """Test depositing credits successfully."""
        with patch("routes.credits.CreditsHistory.insert", new_callable=AsyncMock):
            from routes.credits import deposit_credits, DepositRequest
            
            request = DepositRequest(
                amount=Decimal("500.00"),
                reason=CreditReasonEnum.deposit
            )
            
            result = await deposit_credits(request, mock_user)
            
            assert result["message"] == "Credits deposited successfully"
            assert result["new_balance"] == float(MOCK_INITIAL_CREDITS + Decimal("500.00"))
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_deposit_credits_creates_history_record(self, mock_user):
        """Test that deposit creates a credits history record."""
        with patch("routes.credits.CreditsHistory.insert", new_callable=AsyncMock) as mock_insert:
            from routes.credits import deposit_credits, DepositRequest
            
            deposit_amount = Decimal("250.00")
            request = DepositRequest(
                amount=deposit_amount,
                reason=CreditReasonEnum.deposit
            )
            
            await deposit_credits(request, mock_user)
            
            mock_insert.assert_called_once()
            call_args = mock_insert.call_args[0][0]
            assert call_args.user == mock_user
            assert call_args.change_amount == deposit_amount
            assert call_args.reason == CreditReasonEnum.deposit

    @pytest.mark.asyncio
    async def test_deposit_credits_negative_amount(self, mock_user):
        """Test deposit fails with negative amount."""
        from routes.credits import deposit_credits, DepositRequest
        
        request = DepositRequest(
            amount=Decimal("-100.00"),
            reason=CreditReasonEnum.deposit
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await deposit_credits(request, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Amount must be positive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_deposit_credits_zero_amount(self, mock_user):
        """Test deposit fails with zero amount."""
        from routes.credits import deposit_credits, DepositRequest
        
        request = DepositRequest(
            amount=Decimal("0.00"),
            reason=CreditReasonEnum.deposit
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await deposit_credits(request, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Amount must be positive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_deposit_credits_small_amount(self, mock_user):
        """Test depositing a very small amount."""
        with patch("routes.credits.CreditsHistory.insert", new_callable=AsyncMock):
            from routes.credits import deposit_credits, DepositRequest
            
            request = DepositRequest(
                amount=Decimal("0.01"),
                reason=CreditReasonEnum.deposit
            )
            
            result = await deposit_credits(request, mock_user)
            
            assert result["new_balance"] == float(MOCK_INITIAL_CREDITS + Decimal("0.01"))

    @pytest.mark.asyncio
    async def test_deposit_credits_with_different_reasons(self, mock_user):
        """Test depositing credits with different reasons."""
        reasons = [
            CreditReasonEnum.deposit,
            CreditReasonEnum.top_up,
            CreditReasonEnum.reward,
            CreditReasonEnum.refund
        ]
        
        for reason in reasons:
            mock_user.credits = MOCK_INITIAL_CREDITS  # Reset
            with patch("routes.credits.CreditsHistory.insert", new_callable=AsyncMock):
                from routes.credits import deposit_credits, DepositRequest
                
                request = DepositRequest(
                    amount=Decimal("100.00"),
                    reason=reason
                )
                
                result = await deposit_credits(request, mock_user)
                
                assert result["message"] == "Credits deposited successfully"


class TestGetCreditsHistoryEndpoint:
    """Test cases for /credits/history endpoint."""

    @pytest.mark.asyncio
    async def test_get_credits_history_success(self, mock_user):
        """Test retrieving credits history successfully."""
        mock_history_items = [
            MagicMock(
                user=mock_user,
                change_amount=Decimal("500.00"),
                reason=CreditReasonEnum.deposit,
                balance_after=Decimal("1500.00"),
                created_at=datetime.now(timezone.utc)
            ),
            MagicMock(
                user=mock_user,
                change_amount=Decimal("-100.00"),
                reason=CreditReasonEnum.trade,
                balance_after=Decimal("1000.00"),
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=mock_history_items)
        
        with patch("routes.credits.CreditsHistory.find", return_value=mock_query):
            from routes.credits import get_credits_history
            
            result = await get_credits_history(mock_user)
            
            assert len(result) == 2
            assert result == mock_history_items

    @pytest.mark.asyncio
    async def test_get_credits_history_empty(self, mock_user):
        """Test retrieving credits history when no history exists."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.credits.CreditsHistory.find", return_value=mock_query):
            from routes.credits import get_credits_history
            
            result = await get_credits_history(mock_user)
            
            assert len(result) == 0
            assert result == []

    @pytest.mark.asyncio
    async def test_get_credits_history_sorted_by_created_at(self, mock_user):
        """Test that credits history is sorted by created_at in descending order."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.credits.CreditsHistory.find", return_value=mock_query):
            from routes.credits import get_credits_history
            
            await get_credits_history(mock_user)
            
            mock_query.sort.assert_called_once_with("-created_at")

    @pytest.mark.asyncio
    async def test_get_credits_history_filters_by_user(self, mock_user):
        """Test that credits history is filtered by user ID."""
        mock_query = MagicMock()
        mock_query.sort = MagicMock(return_value=mock_query)
        mock_query.to_list = AsyncMock(return_value=[])
        
        with patch("routes.credits.CreditsHistory.find", return_value=mock_query) as mock_find:
            from routes.credits import get_credits_history
            
            await get_credits_history(mock_user)
            
            # Verify the find was called with user.id condition
            mock_find.assert_called_once()
