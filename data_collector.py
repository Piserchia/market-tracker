"""
Data Collector
==============
Fetches market data from Yahoo Finance (prices, technicals)
and FRED (rates, CPI, TIPS yields).
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from config import (
    DATA_DIR, FRED_API_KEY, FRED_SERIES, FULL_HISTORY_DAYS, TICKERS,
)

logger = logging.getLogger(__name__)


class DataCollector:
    """Collects and caches all market data needed for signal computation."""

    def __init__(self):
        self.price_cache: Dict[str, pd.DataFrame] = {}
        self.fred_cache: Dict[str, pd.Series] = {}
        self.last_update: Optional[datetime] = None
        self.snapshot: Dict[str, Any] = {}

    # ── Yahoo Finance ────────────────────────────

    def fetch_prices(self, period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for all tickers."""
        logger.info("Fetching Yahoo Finance price data...")
        all_symbols = list(TICKERS.values())

        try:
            raw = yf.download(
                all_symbols,
                period=period,
                interval=interval,
                group_by="ticker",
                threads=True,
                progress=False,
            )
        except Exception as e:
            logger.error(f"yfinance bulk download failed: {e}")
            raw = None

        results = {}
        for key, symbol in TICKERS.items():
            try:
                if raw is not None and len(TICKERS) > 1:
                    if symbol in raw.columns.get_level_values(0):
                        df = raw[symbol].dropna(how="all")
                    else:
                        df = pd.DataFrame()
                else:
                    df = raw if raw is not None else pd.DataFrame()

                if df.empty:
                    # Fallback: individual fetch
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period=period, interval=interval)

                if not df.empty:
                    # Normalize column names
                    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                    results[key] = df
                    logger.debug(f"  {key} ({symbol}): {len(df)} rows")
                else:
                    logger.warning(f"  {key} ({symbol}): no data")
            except Exception as e:
                logger.warning(f"  {key} ({symbol}): error - {e}")

        self.price_cache = results
        return results

    def get_current_price(self, key: str) -> Optional[float]:
        """Get the most recent closing price for a ticker key."""
        df = self.price_cache.get(key)
        if df is not None and not df.empty:
            close_col = "close" if "close" in df.columns else "adj_close"
            if close_col in df.columns:
                return float(df[close_col].iloc[-1])
        return None

    def get_price_series(self, key: str, col: str = "close") -> Optional[pd.Series]:
        """Get a full price series for a ticker key."""
        df = self.price_cache.get(key)
        if df is not None and not df.empty and col in df.columns:
            return df[col].dropna()
        return None

    # ── FRED ─────────────────────────────────────

    def fetch_fred_series(self, series_id: str, lookback_days: int = 365) -> Optional[pd.Series]:
        """Fetch a single FRED data series."""
        if not FRED_API_KEY:
            logger.warning("No FRED_API_KEY set; skipping FRED data")
            return None

        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}"
            f"&api_key={FRED_API_KEY}"
            f"&file_type=json"
            f"&observation_start={start.strftime('%Y-%m-%d')}"
            f"&observation_end={end.strftime('%Y-%m-%d')}"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            observations = data.get("observations", [])
            if not observations:
                return None

            dates, values = [], []
            for obs in observations:
                if obs["value"] != ".":
                    dates.append(pd.Timestamp(obs["date"]))
                    values.append(float(obs["value"]))

            series = pd.Series(values, index=dates, name=series_id)
            return series

        except Exception as e:
            logger.error(f"FRED fetch failed for {series_id}: {e}")
            return None

    def fetch_all_fred(self) -> Dict[str, pd.Series]:
        """Fetch all configured FRED series."""
        logger.info("Fetching FRED economic data...")
        results = {}
        for key, series_id in FRED_SERIES.items():
            series = self.fetch_fred_series(series_id)
            if series is not None:
                results[key] = series
                logger.debug(f"  {key} ({series_id}): {len(series)} obs")
            else:
                logger.warning(f"  {key} ({series_id}): no data")
            time.sleep(0.3)  # Respect FRED rate limits

        self.fred_cache = results
        return results

    # ── Computed Helpers ──────────────────────────

    def compute_sma(self, key: str, window: int) -> Optional[pd.Series]:
        """Compute simple moving average for a ticker."""
        series = self.get_price_series(key)
        if series is not None and len(series) >= window:
            return series.rolling(window=window).mean()
        return None

    def compute_ema(self, key: str, window: int) -> Optional[pd.Series]:
        """Compute exponential moving average for a ticker."""
        series = self.get_price_series(key)
        if series is not None and len(series) >= window:
            return series.ewm(span=window, adjust=False).mean()
        return None

    def compute_rsi(self, key: str, period: int = 14) -> Optional[float]:
        """Compute current RSI for a ticker."""
        series = self.get_price_series(key)
        if series is None or len(series) < period + 1:
            return None

        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

    def compute_macd(self, key: str) -> Optional[Dict[str, float]]:
        """Compute MACD line, signal, and histogram."""
        series = self.get_price_series(key)
        if series is None or len(series) < 35:
            return None

        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1]),
        }

    def compute_bollinger(self, key: str, window: int = 20, num_std: float = 2.0):
        """Compute Bollinger Bands."""
        series = self.get_price_series(key)
        if series is None or len(series) < window:
            return None

        sma = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()

        return {
            "upper": float((sma + num_std * std).iloc[-1]),
            "middle": float(sma.iloc[-1]),
            "lower": float((sma - num_std * std).iloc[-1]),
            "price": float(series.iloc[-1]),
            "pct_b": float((series.iloc[-1] - (sma - num_std * std).iloc[-1]) /
                          ((sma + num_std * std).iloc[-1] - (sma - num_std * std).iloc[-1]))
                     if (sma + num_std * std).iloc[-1] != (sma - num_std * std).iloc[-1] else 0.5,
        }

    def compute_ratio_slope(self, key_a: str, key_b: str, window: int = 20) -> Optional[float]:
        """Compute the slope of a ratio (e.g., GDX/GLD) over a rolling window."""
        series_a = self.get_price_series(key_a)
        series_b = self.get_price_series(key_b)

        if series_a is None or series_b is None:
            return None

        # Align indices
        combined = pd.DataFrame({"a": series_a, "b": series_b}).dropna()
        if len(combined) < window:
            return None

        ratio = combined["a"] / combined["b"]
        recent = ratio.iloc[-window:]

        # Linear regression slope
        x = np.arange(len(recent))
        coeffs = np.polyfit(x, recent.values, 1)
        return float(coeffs[0])

    def get_ratio_current(self, key_a: str, key_b: str) -> Optional[float]:
        """Get the current ratio between two tickers."""
        a = self.get_current_price(key_a)
        b = self.get_current_price(key_b)
        if a and b and b != 0:
            return a / b
        return None

    def compute_pct_change(self, key: str, days: int) -> Optional[float]:
        """Compute percentage change over N days."""
        series = self.get_price_series(key)
        if series is None or len(series) < days + 1:
            return None
        current = float(series.iloc[-1])
        past = float(series.iloc[-(days + 1)])
        if past == 0:
            return None
        return (current - past) / past * 100

    def get_price_vs_sma(self, key: str, window: int) -> Optional[Dict]:
        """Get price relative to SMA."""
        price = self.get_current_price(key)
        sma = self.compute_sma(key, window)
        if price is None or sma is None:
            return None
        sma_val = float(sma.iloc[-1])
        return {
            "price": price,
            "sma": sma_val,
            "pct_above": (price - sma_val) / sma_val * 100 if sma_val != 0 else 0,
            "above": price > sma_val,
        }

    # ── Snapshot Builder ─────────────────────────

    def build_snapshot(self) -> Dict[str, Any]:
        """Build a complete data snapshot for the signal engine."""
        logger.info("Building data snapshot...")
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "prices": {},
            "technicals": {},
            "macro": {},
            "ratios": {},
            "changes": {},
        }

        # Current prices
        for key in TICKERS:
            price = self.get_current_price(key)
            if price is not None:
                snapshot["prices"][key] = round(price, 4)

        # Technical indicators for key tickers
        for key in ["gdx", "gdxj", "gold", "silver", "copper", "gld", "dxy", "oil", "spy"]:
            techs = {}
            rsi = self.compute_rsi(key)
            if rsi is not None:
                techs["rsi"] = round(rsi, 2)

            macd = self.compute_macd(key)
            if macd:
                techs["macd"] = {k: round(v, 4) for k, v in macd.items()}

            bb = self.compute_bollinger(key)
            if bb:
                techs["bollinger"] = {k: round(v, 4) for k, v in bb.items()}

            sma50 = self.get_price_vs_sma(key, 50)
            if sma50:
                techs["sma50"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in sma50.items()}

            sma200 = self.get_price_vs_sma(key, 200)
            if sma200:
                techs["sma200"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in sma200.items()}

            if techs:
                snapshot["technicals"][key] = techs

        # Key ratios
        gdx_gld = self.get_ratio_current("gdx", "gld")
        if gdx_gld:
            snapshot["ratios"]["gdx_gld"] = round(gdx_gld, 4)
        gdx_gld_slope = self.compute_ratio_slope("gdx", "gld", 20)
        if gdx_gld_slope is not None:
            snapshot["ratios"]["gdx_gld_slope_20d"] = round(gdx_gld_slope, 6)

        gdxj_gdx = self.get_ratio_current("gdxj", "gdx")
        if gdxj_gdx:
            snapshot["ratios"]["gdxj_gdx"] = round(gdxj_gdx, 4)

        gold_spy = self.get_ratio_current("gold", "spy")
        if gold_spy:
            snapshot["ratios"]["gold_spy"] = round(gold_spy, 4)

        # Percentage changes
        for key in ["gdx", "gdxj", "gold", "silver", "copper", "oil", "dxy", "spy", "qqq"]:
            changes = {}
            for days, label in [(1, "1d"), (5, "1w"), (20, "1m"), (60, "3m")]:
                pct = self.compute_pct_change(key, days)
                if pct is not None:
                    changes[label] = round(pct, 2)
            if changes:
                snapshot["changes"][key] = changes

        # FRED / Macro data
        if self.fred_cache:
            for key, series in self.fred_cache.items():
                if len(series) > 0:
                    snapshot["macro"][key] = round(float(series.iloc[-1]), 4)

            # Compute real rate = nominal 10y - breakeven
            if "treasury_10y" in self.fred_cache and "breakeven_10y" in self.fred_cache:
                nom = float(self.fred_cache["treasury_10y"].iloc[-1])
                be = float(self.fred_cache["breakeven_10y"].iloc[-1])
                snapshot["macro"]["real_rate_10y"] = round(nom - be, 4)

        self.snapshot = snapshot
        self.last_update = datetime.now()
        return snapshot

    # ── Full Refresh ─────────────────────────────

    def refresh(self, include_fred: bool = True) -> Dict[str, Any]:
        """Full data refresh: prices + FRED + snapshot."""
        self.fetch_prices(period="1y", interval="1d")
        if include_fred:
            self.fetch_all_fred()
        return self.build_snapshot()
