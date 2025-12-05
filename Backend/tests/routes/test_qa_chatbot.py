"""
Unit tests for qa_chatbot.py
Tests all Q&A chatbot endpoints with mocked dependencies.
"""
import sys
import types
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
from bson import ObjectId

# Prevent heavy Transformer model load by stubbing chatbot.qa_utils before importing the route
fake_qa_utils = types.ModuleType("chatbot.qa_utils")
def _fake_question_answer(question, context):
    return "Answer"
fake_qa_utils.question_answer = _fake_question_answer
sys.modules.setdefault("chatbot.qa_utils", fake_qa_utils)

from routes.qa_chatbot import router, parse_trade_command, expand_date_to_full_day


# Mock data
MOCK_USER_ID = ObjectId()


@pytest.fixture
def mock_user():
    """Create a mock user object."""
    user = MagicMock()
    user.id = MOCK_USER_ID
    user.username = "testuser@example.com"
    return user


class TestExpandDateToFullDay:
    """Test cases for expand_date_to_full_day helper function."""

    def test_expand_date_to_full_day(self):
        """Test expanding date to full day range."""
        test_date = date(2025, 11, 10)
        start, end = expand_date_to_full_day(test_date)
        
        assert start.date() == test_date
        assert end.date() == test_date
        assert start.time().hour == 0
        assert start.time().minute == 0
        assert end.time().hour == 23
        assert end.time().minute == 59


class TestParseTradeCommand:
    """Test cases for parse_trade_command helper function."""

    def test_parse_trade_command_market_buy(self):
        """Test parsing market buy command."""
        command = "buy 0.5 btc at market price"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["side"] == "BUY"
        assert result["quantity"] == 0.5
        assert result["symbol"] == "BTC"
        assert result["order_type"] == "MARKET"
        assert result["price"] is None

    def test_parse_trade_command_market_sell(self):
        """Test parsing market sell command."""
        command = "sell 1.5 eth at market price"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["side"] == "SELL"
        assert result["quantity"] == 1.5
        assert result["symbol"] == "ETH"
        assert result["order_type"] == "MARKET"

    def test_parse_trade_command_limit_buy(self):
        """Test parsing limit buy command."""
        command = "buy 2.0 btc at limit price 50000.00"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["side"] == "BUY"
        assert result["quantity"] == 2.0
        assert result["symbol"] == "BTC"
        assert result["order_type"] == "LIMIT"
        assert result["price"] == 50000.00

    def test_parse_trade_command_limit_sell(self):
        """Test parsing limit sell command."""
        command = "sell 0.1 eth at limit price 3000.50"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["side"] == "SELL"
        assert result["quantity"] == 0.1
        assert result["symbol"] == "ETH"
        assert result["order_type"] == "LIMIT"
        assert result["price"] == 3000.50

    def test_parse_trade_command_case_insensitive(self):
        """Test that command parsing is case-insensitive."""
        command = "BUY 1.0 BTC AT MARKET PRICE"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["side"] == "BUY"
        assert result["symbol"] == "BTC"

    def test_parse_trade_command_extra_whitespace(self):
        """Test handling extra whitespace in command."""
        command = "buy   0.5   btc   at   market   price"
        result = parse_trade_command(command)
        
        assert result is not None
        assert result["quantity"] == 0.5

    def test_parse_trade_command_invalid_format(self):
        """Test parsing invalid trade command."""
        command = "this is not a valid command"
        result = parse_trade_command(command)
        
        assert result is None

    def test_parse_trade_command_partial_match(self):
        """Test that partial matches don't parse."""
        command = "buy 0.5 btc"
        result = parse_trade_command(command)
        
        assert result is None


class TestQaMainEndpoint:
    """Test cases for /qa endpoint."""

    @pytest.mark.asyncio
    async def test_qa_main_missing_question(self, mock_user):
        """Test QA endpoint with missing question."""
        from routes.qa_chatbot import qa_main
        
        with pytest.raises(HTTPException) as exc_info:
            await qa_main({}, mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Missing question" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_qa_main_trade_command_market(self, mock_user):
        """Test QA endpoint with valid market trade command."""
        with patch("routes.qa_chatbot.process_trade_task") as mock_task:
            from routes.qa_chatbot import qa_main
            
            body = {"question": "buy 0.5 btc at market price"}
            result = await qa_main(body, mock_user)
            
            assert "Order received" in result["answer"]
            assert "BUY" in result["answer"]
            assert "MARKET" in result["answer"]
            mock_task.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_qa_main_trade_command_limit(self, mock_user):
        """Test QA endpoint with valid limit trade command."""
        with patch("routes.qa_chatbot.process_trade_task") as mock_task:
            from routes.qa_chatbot import qa_main
            
            body = {"question": "sell 1.0 eth at limit price 3000.00"}
            result = await qa_main(body, mock_user)
            
            assert "Order received" in result["answer"]
            assert "SELL" in result["answer"]
            mock_task.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_qa_main_trade_command_task_payload(self, mock_user):
        """Test that trade command creates correct task payload."""
        with patch("routes.qa_chatbot.process_trade_task") as mock_task:
            from routes.qa_chatbot import qa_main
            
            body = {"question": "buy 2.5 btc at limit price 45000.00"}
            await qa_main(body, mock_user)
            
            call_args = mock_task.send.call_args[0][0]
            assert call_args["user_id"] == str(MOCK_USER_ID)
            assert call_args["symbol"] == "BTC"
            assert call_args["side"] == "BUY"
            assert call_args["order_type"] == "LIMIT"
            assert call_args["quantity"] == "2.5"
            assert call_args["price"] == "45000.0"

    @pytest.mark.asyncio
    async def test_qa_main_trade_command_error(self, mock_user):
        """Test handling error when queueing trade task."""
        with patch("routes.qa_chatbot.process_trade_task") as mock_task:
            mock_task.send.side_effect = Exception("Queue error")
            
            from routes.qa_chatbot import qa_main
            
            body = {"question": "buy 0.5 btc at market price"}
            result = await qa_main(body, mock_user)
            
            assert "error" in result
            assert "Failed to queue trade task" in result["error"]

    @pytest.mark.asyncio
    async def test_qa_main_order_history_request(self, mock_user):
        """Test QA endpoint with order history request."""
        with patch("routes.qa_chatbot.is_order_history_request", return_value=True), \
             patch("routes.qa_chatbot.get_order_history_context", new_callable=AsyncMock) as mock_context:
            mock_context.return_value = ["Order 1: BUY BTC", "Order 2: SELL ETH"]

            from routes.qa_chatbot import qa_main

            body = {"question": "show my order history"}
            result = await qa_main(body, mock_user)

            assert "answer" in result
            assert "Order 1" in result["answer"]

    @pytest.mark.asyncio
    async def test_qa_main_order_history_empty(self, mock_user):
        """Test QA endpoint with empty order history."""
        with patch("routes.qa_chatbot.is_order_history_request", return_value=True), \
             patch("routes.qa_chatbot.get_order_history_context", new_callable=AsyncMock) as mock_context:
            
            mock_context.return_value = None
            
            from routes.qa_chatbot import qa_main
            
            body = {"question": "show my orders"}
            result = await qa_main(body, mock_user)
            
            assert "error" in result
            assert "no recent orders" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_qa_main_candlestick_request(self, mock_user):
        """Test QA endpoint with candlestick data request."""
        with patch("routes.qa_chatbot.extract_symbol_and_date", return_value=("BTCUSDT", date(2025, 11, 10))), \
             patch("routes.qa_chatbot.get_candlestick_context", new_callable=AsyncMock) as mock_context, \
             patch("routes.qa_chatbot.question_answer", return_value="BTC opened at 50000"):
            
            mock_context.return_value = "BTCUSDT candle data..."
            
            from routes.qa_chatbot import qa_main
            
            body = {"question": "What was the price of BTC on November 10, 2025?"}
            result = await qa_main(body, mock_user)
            
            assert "answer" in result
            assert result["answer"] == "BTC opened at 50000"

    @pytest.mark.asyncio
    async def test_qa_main_candlestick_no_data(self, mock_user):
        """Test QA endpoint when no candlestick data found."""
        with patch("routes.qa_chatbot.extract_symbol_and_date", return_value=("BTCUSDT", date(2025, 11, 10))), \
             patch("routes.qa_chatbot.get_candlestick_context", new_callable=AsyncMock) as mock_context:
            
            mock_context.return_value = None
            
            from routes.qa_chatbot import qa_main
            
            body = {"question": "What was the price of BTC on November 10, 2025?"}
            result = await qa_main(body, mock_user)
            
            assert "error" in result
            assert "No candlestick data found" in result["error"]

    @pytest.mark.asyncio
    async def test_qa_main_unrecognized_question(self, mock_user):
        """Test QA endpoint with unrecognized question format."""
        with patch("routes.qa_chatbot.extract_symbol_and_date", return_value=(None, None)):
            from routes.qa_chatbot import qa_main
            
            body = {"question": "random question"}
            result = await qa_main(body, mock_user)
            
            assert "error" in result
            assert "couldn't understand" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_qa_main_context_snippet_truncation(self, mock_user):
        """Test that long context is truncated in response."""
        long_context = "X" * 1000
        
        with patch("routes.qa_chatbot.extract_symbol_and_date", return_value=("BTCUSDT", date(2025, 11, 10))), \
             patch("routes.qa_chatbot.get_candlestick_context", new_callable=AsyncMock) as mock_context, \
             patch("routes.qa_chatbot.question_answer", return_value="Answer"):
            
            mock_context.return_value = long_context
            
            from routes.qa_chatbot import qa_main
            
            body = {"question": "What was BTC price?"}
            result = await qa_main(body, mock_user)
            
            assert "context_snippet" in result
            assert len(result["context_snippet"]) <= 503  # 500 + "..."
