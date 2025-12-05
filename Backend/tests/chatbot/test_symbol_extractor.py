import datetime
from chatbot.symbol_extractor import extract_symbol_and_date

def test_extract_iso_date_and_symbol():
    q = 'What happened to BTCUSDT on 2025-06-15'
    symbol, date = extract_symbol_and_date(q)
    assert symbol == 'BTCUSDT'
    assert date == datetime.date(2025,6,15)

def test_extract_month_name_without_year_uses_default_year():
    q = 'Show me BTCUSDT on June 15'
    symbol, date = extract_symbol_and_date(q)
    assert symbol == 'BTCUSDT'
    assert date.year == 2025
    assert date.month == 6
    assert date.day == 15

def test_extract_no_date_returns_none_for_date():
    q = 'What is BTCUSDT price?'
    symbol, date = extract_symbol_and_date(q)
    assert symbol == 'BTCUSDT'
    assert date is None

def test_no_symbol_returns_none_symbol():
    q = 'Price on June 15 2025'
    symbol, date = extract_symbol_and_date(q)
    assert symbol is None
    assert date == datetime.date(2025,6,15)
