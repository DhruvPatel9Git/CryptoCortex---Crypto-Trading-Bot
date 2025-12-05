import pytest
from types import SimpleNamespace

import chatbot.order_context_builder as ocb

class FakeQuery:
    def __init__(self, result):
        self._result = result
    def sort(self, *args, **kwargs):
        return self
    def limit(self, *args, **kwargs):
        return self
    async def to_list(self):
        return self._result

class FakeOrder:
    # Provide a `user.id` attribute so calling `Order.user.id` in query expressions
    # does not raise AttributeError during tests. The value is unused by our fake
    # find implementation which accepts any expression.
    user = __import__('types').SimpleNamespace(id=None)

    @staticmethod
    def find(expr):
        return FakeQuery([])

@pytest.mark.asyncio
async def test_get_order_history_context_returns_none_when_no_orders(monkeypatch):
    monkeypatch.setattr(ocb, 'Order', FakeOrder)
    monkeypatch.setattr(FakeOrder, 'find', staticmethod(lambda e: FakeQuery([])))

    user = SimpleNamespace(id='user1')
    res = await ocb.get_order_history_context(user)
    assert res is None

@pytest.mark.asyncio
async def test_get_order_history_context_returns_lines(monkeypatch):
    # create fake order objects
    order1 = SimpleNamespace(symbol='BTCUSDT', quantity=1.23, price=100.0)
    order2 = SimpleNamespace(symbol='ETHUSDT', quantity=2.0, price=200.0)

    monkeypatch.setattr(ocb, 'Order', FakeOrder)
    monkeypatch.setattr(FakeOrder, 'find', staticmethod(lambda e: FakeQuery([order1, order2])))

    user = SimpleNamespace(id='u')
    res = await ocb.get_order_history_context(user)

    assert isinstance(res, list)
    assert any('BTCUSDT' in s for s in res)
    assert any('ETHUSDT' in s for s in res)

def test_is_order_history_request_positive():
    assert ocb.is_order_history_request('Can you show my order history?')
    assert ocb.is_order_history_request('What are my past orders')

def test_is_order_history_request_negative():
    assert not ocb.is_order_history_request('What is the price of BTC?')
