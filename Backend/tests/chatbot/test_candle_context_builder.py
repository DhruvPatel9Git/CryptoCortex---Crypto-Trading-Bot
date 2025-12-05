import pytest
from types import SimpleNamespace

import importlib

# import the module under test (Backend is test cwd per pytest.ini)
import chatbot.candle_context_builder as ccb

class FakeQuery:
    def __init__(self, result):
        self._result = result
    def sort(self, *args, **kwargs):
        return self
    async def to_list(self):
        return self._result

class FakeCandle:
    @staticmethod
    def find(query):
        # default placeholder, tests will monkeypatch by replacing this method
        return FakeQuery([])

@pytest.mark.asyncio
async def test_get_candlestick_context_returns_none_when_no_candles(monkeypatch):
    # Arrange
    monkeypatch.setattr(ccb, 'Candle', FakeCandle)
    monkeypatch.setattr(FakeCandle, 'find', staticmethod(lambda q: FakeQuery([])))

    # Act
    res = await ccb.get_candlestick_context('BTCUSDT', '2020-01-01', '2020-01-02')

    # Assert
    assert res is None

@pytest.mark.asyncio
async def test_get_candlestick_context_formats_candles(monkeypatch):
    # Arrange: create a fake candle object with the expected attributes
    candle = SimpleNamespace(
        symbol='BTCUSDT',
        candle_time=SimpleNamespace(strftime=lambda fmt: '2020-01-01'),
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=123.45,
    )

    monkeypatch.setattr(ccb, 'Candle', FakeCandle)
    monkeypatch.setattr(FakeCandle, 'find', staticmethod(lambda q: FakeQuery([candle])))

    # Act
    res = await ccb.get_candlestick_context('BTCUSDT', '2020-01-01', '2020-01-02')

    # Assert
    assert isinstance(res, str)
    assert 'BTCUSDT' in res
    assert 'Open: 100.0' in res
    assert 'Volume: 123.45' in res
