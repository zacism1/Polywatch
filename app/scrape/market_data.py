import logging
from datetime import datetime
from typing import Optional
import requests
from flask import current_app


logger = logging.getLogger("politracker")


def get_price_change(symbol: str, start_date, end_date) -> Optional[float]:
    if not symbol:
        return None

    provider = current_app.config.get("MARKET_DATA_PROVIDER", "yahoo")
    if provider == "alpha_vantage":
        return _alpha_vantage_change(symbol, start_date, end_date)
    return _yahoo_change(symbol, start_date, end_date)


def _yahoo_change(symbol: str, start_date, end_date) -> Optional[float]:
    try:
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end_date, datetime.min.time()).timestamp())
    except Exception:
        return None

    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?period1={start_ts}&period2={end_ts}&interval=1d"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None
        return (closes[-1] - closes[0]) / closes[0]
    except Exception as exc:
        logger.warning("Yahoo price fetch failed for %s: %s", symbol, exc)
        return None


def _alpha_vantage_change(symbol: str, start_date, end_date) -> Optional[float]:
    api_key = current_app.config.get("ALPHA_VANTAGE_API_KEY", "")
    if not api_key:
        return None

    url = (
        "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED"
        f"&symbol={symbol}&apikey={api_key}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("Time Series (Daily)", {})
        dates = sorted(data.keys())
        if not dates:
            return None

        start_key = max([d for d in dates if d <= start_date.isoformat()], default=None)
        end_key = max([d for d in dates if d <= end_date.isoformat()], default=None)
        if not start_key or not end_key:
            return None

        start_close = float(data[start_key]["4. close"])
        end_close = float(data[end_key]["4. close"])
        return (end_close - start_close) / start_close
    except Exception as exc:
        logger.warning("Alpha Vantage price fetch failed for %s: %s", symbol, exc)
        return None
