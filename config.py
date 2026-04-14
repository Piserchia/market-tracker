"""
Mining Sector Rotation Monitor - Configuration
================================================
All thresholds, tickers, API keys, and alert settings.
Edit this file to tune your rotation signals.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List

# ──────────────────────────────────────────────
# API KEYS (set via environment variables)
# ──────────────────────────────────────────────
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")          # https://fred.stlouisfed.org/docs/api/api_key.html
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")             # Your Twilio number
ALERT_PHONE = os.environ.get("ALERT_PHONE", "")             # Your cell
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")

# ──────────────────────────────────────────────
# TICKERS & DATA SOURCES
# ──────────────────────────────────────────────

# Core mining / metals tickers (Yahoo Finance)
TICKERS = {
    # Metals
    "gold":     "GC=F",      # Gold futures
    "silver":   "SI=F",      # Silver futures
    "copper":   "HG=F",      # Copper futures
    "oil":      "BZ=F",      # Brent crude futures

    # Mining ETFs
    "gdx":      "GDX",       # Senior gold miners
    "gdxj":     "GDXJ",      # Junior gold miners
    "gld":      "GLD",       # Physical gold ETF
    "slv":      "SLV",       # Physical silver ETF
    "copx":     "COPX",      # Copper miners
    "sil":      "SIL",       # Silver miners

    # Macro
    "dxy":      "DX-Y.NYB",  # US Dollar Index
    "spy":      "SPY",       # S&P 500
    "qqq":      "QQQ",       # Nasdaq 100
    "tlt":      "TLT",       # Long-term treasuries
    "tip":      "TIP",       # TIPS ETF

    # Rotation targets
    "smh":      "SMH",       # Semiconductor ETF
    "xlk":      "XLK",       # Tech sector
    "xly":      "XLY",       # Consumer discretionary
    "xle":      "XLE",       # Energy
    "xlf":      "XLF",       # Financials
    "xhb":      "XHB",       # Homebuilders
    "arkk":     "ARKK",      # Innovation/growth
}

# FRED series IDs
FRED_SERIES = {
    "tips_10y":     "DFII10",      # 10-Year TIPS yield (real rate)
    "treasury_10y": "DGS10",       # 10-Year Treasury yield
    "cpi_yoy":      "CPIAUCSL",    # CPI (needs YoY calc)
    "fed_funds":    "FEDFUNDS",    # Fed funds rate
    "breakeven_10y":"T10YIE",      # 10-Year breakeven inflation
}

# ──────────────────────────────────────────────
# SIGNAL THRESHOLDS
# ──────────────────────────────────────────────

@dataclass
class Thresholds:
    """Rotation signal thresholds. Each signal scores -1 (bearish for metals)
    to +1 (bullish for metals). Dashboard aggregates into composite score."""

    # 1. Oil / Hormuz proxy
    oil_bullish_floor: float = 85.0     # Oil above this = geopolitical fear = bullish metals
    oil_bearish_ceiling: float = 70.0   # Oil below this = calm = bearish metals

    # 2. Real interest rates (10Y TIPS yield)
    real_rate_warning: float = 1.5      # Yellow flag for metals
    real_rate_danger: float = 2.0       # Red flag — strong bearish
    real_rate_bullish: float = 0.5      # Below this = very bullish metals

    # 3. US Dollar Index (DXY)
    dxy_bearish_metals: float = 105.0   # DXY above = headwind
    dxy_bullish_metals: float = 100.0   # DXY below = tailwind
    dxy_strong_bearish: float = 108.0   # DXY above = strong headwind

    # 4. GDX/GLD ratio (miner leverage)
    # Tracked as rolling 20-day slope; negative slope = miners underperforming
    gdx_gld_slope_warning: float = -0.001   # Slight underperformance
    gdx_gld_slope_danger: float = -0.003    # Strong underperformance

    # 5. AISC margin proxy (gold price vs historical AISC trend)
    # We approximate since real AISC is quarterly; use gold price level as proxy
    gold_aisc_floor: float = 3500.0     # Below this, margins compress dangerously
    gold_aisc_comfort: float = 4000.0   # Above this, margins very healthy

    # 6. Technical: RSI
    rsi_overbought: float = 75.0        # GDX RSI above this = caution
    rsi_extreme_overbought: float = 85.0
    rsi_oversold: float = 30.0          # Potential buy signal

    # 7. Technical: 200-day MA
    # Signal based on price vs 200-day SMA of GDX

    # 8. Gold price momentum (50-day vs 200-day)
    # Golden cross / death cross on gold itself

    # 9. Composite rotation trigger
    bearish_threshold: int = -3          # Composite score at or below = ROTATE OUT
    warning_threshold: int = -1          # Composite score at or below = WATCH CLOSELY
    bullish_threshold: int = 2           # Composite score at or above = HOLD / ADD


THRESHOLDS = Thresholds()

# ──────────────────────────────────────────────
# ROTATION TARGET SCORING
# ──────────────────────────────────────────────

# When rotation signal fires, these sectors get scored
# based on the macro regime that triggered the rotation
ROTATION_SECTORS = {
    "ai_tech": {
        "name": "AI / Tech Infrastructure",
        "tickers": ["SMH", "XLK", "QQQ"],
        "favored_when": ["oil_falling", "rates_cutting", "dxy_falling"],
        "description": "Semiconductors, cloud, data center buildout"
    },
    "rate_sensitive_growth": {
        "name": "Rate-Sensitive Growth",
        "tickers": ["ARKK", "XHB", "XLF"],
        "favored_when": ["rates_cutting", "real_rates_falling"],
        "description": "Fintech, homebuilders, innovation — benefits from rate cuts"
    },
    "consumer": {
        "name": "Consumer Discretionary",
        "tickers": ["XLY"],
        "favored_when": ["oil_falling", "wages_rising", "consumer_confidence_up"],
        "description": "Rebounds when energy costs drop and real wages improve"
    },
    "energy": {
        "name": "Energy",
        "tickers": ["XLE"],
        "favored_when": ["oil_rising", "inflation_sticky"],
        "description": "Benefits from sustained high energy prices"
    },
    "broad_market": {
        "name": "Broad Market (S&P 500)",
        "tickers": ["SPY"],
        "favored_when": ["volatility_falling", "growth_stable"],
        "description": "Default risk-on allocation"
    },
}

# ──────────────────────────────────────────────
# SCHEDULING
# ──────────────────────────────────────────────
UPDATE_INTERVAL_MINUTES = 15        # How often to refresh data during market hours
MARKET_OPEN_HOUR = 9                # ET
MARKET_CLOSE_HOUR = 17              # ET (5 PM to catch after-hours)
FULL_HISTORY_DAYS = 365             # Days of history to fetch for technical calcs

# ──────────────────────────────────────────────
# FILE PATHS
# ──────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STATE_FILE = os.path.join(DATA_DIR, "dashboard_state.json")
HISTORY_FILE = os.path.join(DATA_DIR, "signal_history.json")
ALERT_LOG = os.path.join(DATA_DIR, "alert_log.json")

# Server
HOST = "0.0.0.0"
PORT = 8787
