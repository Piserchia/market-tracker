"""
AI Sector Signal Engine
========================
Reads portfolio.json and stock_profiles.json to compute:
  - Layer 1: Sector-wide health signals
  - Layer 2: Per-stock technical + valuation signals (universal, auto-computed)
  - Layer 3: Per-stock custom thresholds from profiles (context-aware)

Any ticker in portfolio.json gets Layer 2 signals automatically.
Tickers with a profile in stock_profiles.json also get Layer 3 custom signals.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")
PROFILES_FILE = os.path.join(BASE_DIR, "stock_profiles.json")
STATE_FILE = os.path.join(BASE_DIR, "data", "ai_dashboard_state.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "ai_signal_history.json")

# Sector-wide tickers to always fetch
SECTOR_TICKERS = {
    "sox": "^SOX",
    "vix": "^VIX",
    "spy": "SPY",
    "qqq": "QQQ",
    "smh": "SMH",
    "treasury_10y_proxy": "^TNX",
    "oil": "BZ=F",
    "dxy": "DX-Y.NYB",
}


def load_json(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load {path}: {e}")
        return {}


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


class AISignalEngine:

    def __init__(self):
        self.portfolio = {}
        self.profiles = {}
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.stock_info: Dict[str, dict] = {}
        self.snapshot: Dict[str, Any] = {}

    # ── Data Loading ─────────────────────────────

    def load_config(self):
        """Load portfolio and profiles from JSON files."""
        self.portfolio = load_json(PORTFOLIO_FILE)
        self.profiles = load_json(PROFILES_FILE)
        logger.info(f"Loaded {len(self.portfolio.get('holdings', []))} holdings, "
                     f"{len(self.profiles.get('profiles', {}))} stock profiles")

    def get_all_tickers(self) -> List[str]:
        """Get unique tickers from portfolio (excluding mutual funds)."""
        holdings = self.portfolio.get("holdings", [])
        mutual_fund_suffixes = ("FDGFX", "FSPTX")  # Mutual funds don't have yfinance data
        tickers = set()
        for h in holdings:
            t = h.get("ticker", "")
            if t and t not in mutual_fund_suffixes:
                tickers.add(t)
        return sorted(tickers)

    def get_portfolio_summary(self) -> Dict:
        """Compute portfolio summary stats."""
        holdings = self.portfolio.get("holdings", [])
        total = sum(h.get("dollars", 0) for h in holdings)
        by_account = {}
        by_category = {}

        for h in holdings:
            acct = h.get("account", "trading")
            ticker = h.get("ticker", "")
            dollars = h.get("dollars", 0)
            profile = self.profiles.get("profiles", {}).get(ticker, self.profiles.get("default_profile", {}))
            cat = profile.get("category", "unclassified")

            by_account[acct] = by_account.get(acct, 0) + dollars
            by_category[cat] = by_category.get(cat, 0) + dollars

        return {
            "total_value": total,
            "by_account": by_account,
            "by_category": by_category,
            "holding_count": len(holdings),
        }

    # ── Data Fetching ────────────────────────────

    def fetch_all_data(self):
        """Fetch price data for all portfolio tickers + sector tickers."""
        tickers = self.get_all_tickers()
        all_symbols = tickers + list(SECTOR_TICKERS.values())
        all_symbols = list(set(all_symbols))

        logger.info(f"Fetching data for {len(all_symbols)} symbols...")

        # Bulk download
        try:
            raw = yf.download(all_symbols, period="1y", interval="1d",
                              group_by="ticker", threads=True, progress=False)
        except Exception as e:
            logger.error(f"Bulk download failed: {e}")
            raw = None

        for symbol in all_symbols:
            try:
                if raw is not None and len(all_symbols) > 1:
                    if symbol in raw.columns.get_level_values(0):
                        df = raw[symbol].dropna(how="all")
                    else:
                        df = pd.DataFrame()
                else:
                    df = raw if raw is not None else pd.DataFrame()

                if df.empty:
                    ticker_obj = yf.Ticker(symbol)
                    df = ticker_obj.history(period="1y", interval="1d")

                if not df.empty:
                    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                    self.price_data[symbol] = df
            except Exception as e:
                logger.warning(f"  {symbol}: {e}")

        # Fetch stock info for fundamental data
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.fast_info
                full_info = t.info if hasattr(t, 'info') else {}
                self.stock_info[ticker] = {
                    "market_cap": getattr(info, "market_cap", None),
                    "forward_pe": full_info.get("forwardPE"),
                    "trailing_pe": full_info.get("trailingPE"),
                    "peg_ratio": full_info.get("pegRatio"),
                    "price_to_book": full_info.get("priceToBook"),
                    "forward_eps": full_info.get("forwardEps"),
                    "trailing_eps": full_info.get("trailingEps"),
                    "revenue_growth": full_info.get("revenueGrowth"),
                    "earnings_growth": full_info.get("earningsGrowth"),
                    "gross_margins": full_info.get("grossMargins"),
                    "operating_margins": full_info.get("operatingMargins"),
                    "free_cashflow": full_info.get("freeCashflow"),
                    "target_mean_price": full_info.get("targetMeanPrice"),
                    "target_high_price": full_info.get("targetHighPrice"),
                    "target_low_price": full_info.get("targetLowPrice"),
                    "recommendation": full_info.get("recommendationKey"),
                    "short_ratio": full_info.get("shortRatio"),
                    "short_percent": full_info.get("shortPercentOfFloat"),
                    "current_price": full_info.get("currentPrice") or getattr(info, "last_price", None),
                    "fifty_two_week_high": full_info.get("fiftyTwoWeekHigh"),
                    "fifty_two_week_low": full_info.get("fiftyTwoWeekLow"),
                    "beta": full_info.get("beta"),
                    "dividend_yield": full_info.get("dividendYield"),
                    "sector": full_info.get("sector"),
                    "industry": full_info.get("industry"),
                    "name": full_info.get("shortName", ticker),
                }
            except Exception as e:
                logger.warning(f"  Info fetch failed for {ticker}: {e}")

        logger.info(f"Fetched data for {len(self.price_data)} symbols, "
                     f"info for {len(self.stock_info)} stocks")

    # ── Technical Computations ───────────────────

    def _get_series(self, symbol: str, col: str = "close") -> Optional[pd.Series]:
        df = self.price_data.get(symbol)
        if df is not None and col in df.columns:
            return df[col].dropna()
        return None

    def _compute_rsi(self, symbol: str, period: int = 14) -> Optional[float]:
        s = self._get_series(symbol)
        if s is None or len(s) < period + 1:
            return None
        delta = s.diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = (-delta).where(delta < 0, 0.0).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        v = rsi.iloc[-1]
        return float(v) if not pd.isna(v) else None

    def _compute_sma(self, symbol: str, window: int) -> Optional[float]:
        s = self._get_series(symbol)
        if s is None or len(s) < window:
            return None
        return float(s.rolling(window).mean().iloc[-1])

    def _compute_macd(self, symbol: str) -> Optional[Dict]:
        s = self._get_series(symbol)
        if s is None or len(s) < 35:
            return None
        ema12 = s.ewm(span=12).mean()
        ema26 = s.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        hist = macd - signal
        return {"macd": round(float(macd.iloc[-1]), 4),
                "signal": round(float(signal.iloc[-1]), 4),
                "histogram": round(float(hist.iloc[-1]), 4)}

    def _compute_pct_change(self, symbol: str, days: int) -> Optional[float]:
        s = self._get_series(symbol)
        if s is None or len(s) < days + 1:
            return None
        cur = float(s.iloc[-1])
        prev = float(s.iloc[-(days + 1)])
        return round((cur - prev) / prev * 100, 2) if prev != 0 else None

    def _current_price(self, symbol: str) -> Optional[float]:
        s = self._get_series(symbol)
        if s is not None and len(s) > 0:
            return float(s.iloc[-1])
        return None

    # ── Layer 1: Sector Health ───────────────────

    def compute_sector_signals(self) -> List[Dict]:
        """Compute sector-wide health signals."""
        signals = []

        # SOX vs 200-SMA
        sox_price = self._current_price("^SOX")
        sox_sma200 = self._compute_sma("^SOX", 200)
        if sox_price and sox_sma200:
            pct_above = (sox_price - sox_sma200) / sox_sma200 * 100
            above = sox_price > sox_sma200
            signals.append({
                "name": "SOX Index Trend",
                "layer": 1,
                "value": round(sox_price, 1),
                "score": 1.0 if above and pct_above < 30 else (0.5 if above else -1.0),
                "status": "bullish" if above else "bearish",
                "detail": f"SOX at {sox_price:.0f}, {pct_above:+.1f}% vs 200-SMA — {'uptrend' if above else 'DOWNTREND'}",
                "affects": ["chip_designer", "chip_fabricator", "server_infra"],
                "source": "Yahoo Finance (^SOX)", "frequency": "15 min"
            })

        # VIX
        vix = self._current_price("^VIX")
        if vix:
            score = 1.0 if vix < 18 else (0.0 if vix < 25 else (-0.5 if vix < 35 else -1.0))
            signals.append({
                "name": "VIX Fear Gauge",
                "layer": 1, "value": round(vix, 1),
                "score": score,
                "status": "bullish" if vix < 18 else ("neutral" if vix < 25 else "bearish"),
                "detail": f"VIX at {vix:.1f} — {'low fear, risk-on' if vix < 18 else ('elevated' if vix < 25 else 'high fear, growth selling off')}",
                "affects": ["all"],
                "source": "Yahoo Finance (^VIX)", "frequency": "15 min"
            })

        # 10Y Treasury (via ^TNX which is yield * 10)
        tnx = self._current_price("^TNX")
        if tnx:
            yield_10y = tnx  # ^TNX is already in percent
            score = 1.0 if yield_10y < 3.5 else (0.0 if yield_10y < 4.5 else -1.0)
            signals.append({
                "name": "10Y Treasury Yield",
                "layer": 1, "value": round(yield_10y, 2),
                "score": score,
                "status": "bullish" if yield_10y < 3.5 else ("neutral" if yield_10y < 4.5 else "bearish"),
                "detail": f"10Y at {yield_10y:.2f}% — {'low rates support growth' if yield_10y < 3.5 else ('moderate' if yield_10y < 4.5 else 'high rates compress multiples')}",
                "affects": ["all"],
                "source": "Yahoo Finance (^TNX)", "frequency": "15 min"
            })

        # DXY
        dxy = self._current_price("DX-Y.NYB")
        if dxy:
            score = 0.5 if dxy < 100 else (0.0 if dxy < 105 else -0.5)
            signals.append({
                "name": "US Dollar (DXY)",
                "layer": 1, "value": round(dxy, 1),
                "score": score,
                "status": "bullish" if dxy < 100 else ("neutral" if dxy < 105 else "bearish"),
                "detail": f"DXY at {dxy:.1f} — {'weak dollar helps overseas earners' if dxy < 100 else ('moderate' if dxy < 105 else 'strong dollar headwind')}",
                "affects": ["chip_designer", "ai_monetizer"],
                "source": "Yahoo Finance (DX-Y.NYB)", "frequency": "15 min"
            })

        # Oil (data center energy cost)
        oil = self._current_price("BZ=F")
        if oil:
            score = 0.5 if oil < 75 else (0.0 if oil < 95 else -0.5)
            signals.append({
                "name": "Oil / Energy Cost",
                "layer": 1, "value": round(oil, 1),
                "score": score,
                "status": "bullish" if oil < 75 else ("neutral" if oil < 95 else "bearish"),
                "detail": f"Brent at ${oil:.0f} — {'low energy = cheap data centers' if oil < 75 else ('elevated' if oil < 95 else 'high energy costs hit margins')}",
                "affects": ["cloud_platform", "chip_fabricator"],
                "source": "Yahoo Finance (BZ=F)", "frequency": "15 min"
            })

        # SMH momentum (semiconductor ETF)
        smh_1m = self._compute_pct_change("SMH", 20)
        spy_1m = self._compute_pct_change("SPY", 20)
        if smh_1m is not None and spy_1m is not None:
            spread = smh_1m - spy_1m
            score = 1.0 if spread > 5 else (0.0 if spread > -5 else -1.0)
            signals.append({
                "name": "Semis vs Broad Market",
                "layer": 1, "value": round(spread, 1),
                "score": score,
                "status": "bullish" if spread > 5 else ("neutral" if spread > -5 else "bearish"),
                "detail": f"SMH {smh_1m:+.1f}% vs SPY {spy_1m:+.1f}% (1M) — spread {spread:+.1f}%",
                "affects": ["chip_designer", "chip_fabricator", "server_infra"],
                "source": "Yahoo Finance (SMH, SPY)", "frequency": "15 min"
            })

        return signals

    # ── Layer 2: Per-Stock Universal Signals ──────

    def compute_stock_signals(self, ticker: str) -> Dict:
        """Compute universal signals for any ticker."""
        info = self.stock_info.get(ticker, {})
        price = info.get("current_price") or self._current_price(ticker)
        result = {"ticker": ticker, "price": price, "signals": [], "valuation": {}, "technicals": {}, "changes": {}}

        if price is None:
            return result

        # -- Technicals --
        rsi = self._compute_rsi(ticker)
        if rsi is not None:
            result["technicals"]["rsi"] = round(rsi, 1)
            status = "bearish" if rsi > 75 else ("bullish" if rsi < 30 else "neutral")
            result["signals"].append({
                "name": "RSI (14-day)", "layer": 2, "value": round(rsi, 1),
                "score": -0.5 if rsi > 75 else (0.5 if rsi < 30 else 0.0),
                "status": status,
                "detail": f"RSI {rsi:.0f} — {'overbought' if rsi > 75 else ('oversold' if rsi < 30 else 'neutral')}",
            })

        sma50 = self._compute_sma(ticker, 50)
        sma200 = self._compute_sma(ticker, 200)
        if sma50 and sma200:
            golden = sma50 > sma200
            result["technicals"]["sma50"] = round(sma50, 2)
            result["technicals"]["sma200"] = round(sma200, 2)
            result["technicals"]["golden_cross"] = golden
            if price and sma200:
                pct_vs_200 = (price - sma200) / sma200 * 100
                result["technicals"]["pct_vs_200sma"] = round(pct_vs_200, 1)
                result["signals"].append({
                    "name": "Trend (200-SMA)", "layer": 2, "value": round(pct_vs_200, 1),
                    "score": 0.5 if pct_vs_200 > 0 else -1.0,
                    "status": "bullish" if pct_vs_200 > 0 else "bearish",
                    "detail": f"{'Above' if pct_vs_200 > 0 else 'BELOW'} 200-SMA by {abs(pct_vs_200):.1f}%",
                })

        macd = self._compute_macd(ticker)
        if macd:
            result["technicals"]["macd"] = macd
            result["signals"].append({
                "name": "MACD", "layer": 2, "value": macd["histogram"],
                "score": 0.25 if macd["histogram"] > 0 else -0.25,
                "status": "bullish" if macd["histogram"] > 0 else "bearish",
                "detail": f"MACD histogram {'positive' if macd['histogram'] > 0 else 'negative'} ({macd['histogram']:.3f})",
            })

        # Changes
        for days, label in [(1, "1d"), (5, "1w"), (20, "1m"), (60, "3m")]:
            pct = self._compute_pct_change(ticker, days)
            if pct is not None:
                result["changes"][label] = pct

        # -- Valuation --
        fwd_pe = info.get("forward_pe")
        if fwd_pe and fwd_pe > 0:
            result["valuation"]["forward_pe"] = round(fwd_pe, 1)

        peg = info.get("peg_ratio")
        if peg and peg > 0:
            result["valuation"]["peg_ratio"] = round(peg, 2)
            result["signals"].append({
                "name": "PEG Ratio", "layer": 2, "value": round(peg, 2),
                "score": 1.0 if peg < 1.0 else (0.0 if peg < 2.0 else -0.5),
                "status": "bullish" if peg < 1.0 else ("neutral" if peg < 2.0 else "bearish"),
                "detail": f"PEG {peg:.2f} — {'undervalued vs growth' if peg < 1.0 else ('fair' if peg < 2.0 else 'expensive vs growth')}",
            })

        # FCF yield
        fcf = info.get("free_cashflow")
        mcap = info.get("market_cap")
        if fcf and mcap and mcap > 0:
            fcf_yield = (fcf / mcap) * 100
            result["valuation"]["fcf_yield"] = round(fcf_yield, 2)
            result["signals"].append({
                "name": "FCF Yield", "layer": 2, "value": round(fcf_yield, 2),
                "score": 0.5 if fcf_yield > 3 else (0.0 if fcf_yield > 0 else -0.5),
                "status": "bullish" if fcf_yield > 3 else ("neutral" if fcf_yield > 0 else "bearish"),
                "detail": f"FCF yield {fcf_yield:.1f}% — {'attractive' if fcf_yield > 3 else ('positive' if fcf_yield > 0 else 'negative cash flow')}",
            })

        # Price vs analyst target
        target = info.get("target_mean_price")
        if target and price:
            upside = (target - price) / price * 100
            result["valuation"]["analyst_target"] = round(target, 2)
            result["valuation"]["analyst_upside"] = round(upside, 1)
            result["signals"].append({
                "name": "vs Analyst Target", "layer": 2, "value": round(upside, 1),
                "score": 0.5 if upside > 15 else (0.0 if upside > 0 else -0.5),
                "status": "bullish" if upside > 15 else ("neutral" if upside > 0 else "bearish"),
                "detail": f"Target ${target:.0f} ({upside:+.0f}% {'upside' if upside > 0 else 'downside'})",
            })

        # Revenue growth
        rev_growth = info.get("revenue_growth")
        if rev_growth is not None:
            rev_pct = rev_growth * 100
            result["valuation"]["revenue_growth"] = round(rev_pct, 1)

        # Gross margins
        gm = info.get("gross_margins")
        if gm is not None:
            result["valuation"]["gross_margin"] = round(gm * 100, 1)

        # Short interest
        short_pct = info.get("short_percent")
        if short_pct:
            result["valuation"]["short_percent"] = round(short_pct * 100, 1)

        # 52-week position
        hi52 = info.get("fifty_two_week_high")
        lo52 = info.get("fifty_two_week_low")
        if hi52 and lo52 and price:
            position = (price - lo52) / (hi52 - lo52) * 100 if hi52 != lo52 else 50
            result["valuation"]["52w_position"] = round(position, 0)

        return result

    # ── Layer 3: Profile-Based Custom Signals ────

    def compute_profile_signals(self, ticker: str, stock_data: Dict) -> List[Dict]:
        """Compute signals from stock_profiles.json custom thresholds."""
        profiles = self.profiles.get("profiles", {})
        profile = profiles.get(ticker)
        if not profile:
            return []

        signals = []
        thresholds = profile.get("fundamental_thresholds", {})
        info = self.stock_info.get(ticker, {})

        for key, thresh in thresholds.items():
            threshold_val = thresh.get("value")
            severity = thresh.get("severity", "medium")
            desc = thresh.get("description", "")

            # Match threshold key to available data
            actual_val = None
            if "gross_margin" in key and info.get("gross_margins"):
                actual_val = info["gross_margins"] * 100
            elif "forward_pe" in key and info.get("forward_pe"):
                actual_val = info["forward_pe"]
            elif "forward_peg" in key and info.get("peg_ratio"):
                actual_val = info["peg_ratio"]
            elif "revenue_growth" in key and info.get("revenue_growth"):
                actual_val = info["revenue_growth"] * 100

            if actual_val is not None and threshold_val is not None:
                # Determine if this is a floor or ceiling
                is_floor = "floor" in key or "target" in key
                is_ceiling = "ceiling" in key

                if is_floor:
                    breached = actual_val < threshold_val
                elif is_ceiling:
                    breached = actual_val > threshold_val
                else:
                    breached = False

                if breached:
                    signals.append({
                        "name": f"⚠ {key.replace('_', ' ').title()}",
                        "layer": 3, "value": round(actual_val, 2),
                        "score": -1.0 if severity == "high" else -0.5,
                        "status": "bearish",
                        "detail": f"THRESHOLD BREACHED: {actual_val:.1f} vs {threshold_val} — {desc}",
                        "severity": severity,
                    })

        return signals

    # ── Full Dashboard Build ─────────────────────

    def build_dashboard(self) -> Dict:
        """Build complete dashboard state."""
        self.load_config()
        self.fetch_all_data()

        # Portfolio summary
        portfolio_summary = self.get_portfolio_summary()

        # Layer 1: Sector signals
        sector_signals = self.compute_sector_signals()

        # Per-stock data
        holdings = self.portfolio.get("holdings", [])
        stock_cards = {}

        for h in holdings:
            ticker = h.get("ticker", "")
            if not ticker or ticker in ("FDGFX", "FSPTX"):
                continue

            # Compute Layer 2 universal signals
            stock_data = self.compute_stock_signals(ticker)

            # Compute Layer 3 profile signals
            profile_signals = self.compute_profile_signals(ticker, stock_data)
            stock_data["signals"].extend(profile_signals)

            # Attach portfolio context
            profile = self.profiles.get("profiles", {}).get(ticker, self.profiles.get("default_profile", {}))
            stock_data["dollars"] = h.get("dollars", 0)
            stock_data["account"] = h.get("account", "trading")
            stock_data["notes"] = h.get("notes", "")
            stock_data["category"] = profile.get("category", "unclassified")
            stock_data["risk_tier"] = profile.get("risk_tier", "unclassified")
            stock_data["value_chain"] = profile.get("value_chain_position", "")
            stock_data["sell_triggers"] = profile.get("sell_triggers", [])
            stock_data["buy_signals"] = profile.get("buy_signals", [])
            stock_data["name"] = (self.stock_info.get(ticker, {}).get("name")
                                  or profile.get("name", ticker))

            # Compute composite score for this stock
            all_scores = [s.get("score", 0) for s in stock_data["signals"]]
            stock_data["composite_score"] = round(sum(all_scores), 2) if all_scores else 0
            n_bullish = sum(1 for s in stock_data["signals"] if s.get("status") == "bullish")
            n_bearish = sum(1 for s in stock_data["signals"] if s.get("status") == "bearish")
            stock_data["signal_summary"] = {"bullish": n_bullish, "bearish": n_bearish, "total": len(all_scores)}

            # Determine stock-level status
            cs = stock_data["composite_score"]
            if n_bearish >= 3 or any(s.get("severity") == "immediate" for s in stock_data["signals"]):
                stock_data["status"] = "SELL"
                stock_data["status_color"] = "red"
            elif cs < -1:
                stock_data["status"] = "WATCH"
                stock_data["status_color"] = "orange"
            elif cs > 1:
                stock_data["status"] = "HOLD"
                stock_data["status_color"] = "green"
            else:
                stock_data["status"] = "NEUTRAL"
                stock_data["status_color"] = "yellow"

            # Aggregate into card (handle duplicate tickers across accounts)
            card_key = f"{ticker}_{h.get('account', 'trading')}"
            stock_cards[card_key] = stock_data

        # Sector health composite
        sector_score = sum(s.get("score", 0) for s in sector_signals)
        if sector_score >= 2:
            sector_status = {"label": "HEALTHY", "color": "green", "message": "AI cycle indicators are bullish. Sector tailwinds support holdings."}
        elif sector_score >= 0:
            sector_status = {"label": "MIXED", "color": "yellow", "message": "Some crosscurrents in sector signals. Monitor closely."}
        elif sector_score >= -2:
            sector_status = {"label": "CAUTION", "color": "orange", "message": "Sector headwinds building. Review high-risk positions."}
        else:
            sector_status = {"label": "DANGER", "color": "red", "message": "Multiple sector signals bearish. Consider reducing exposure."}

        state = {
            "timestamp": datetime.now().isoformat(),
            "portfolio_summary": portfolio_summary,
            "sector_health": {
                "score": round(sector_score, 2),
                "status": sector_status,
                "signals": sector_signals,
            },
            "stock_cards": stock_cards,
            "config_files": {
                "portfolio": PORTFOLIO_FILE,
                "profiles": PROFILES_FILE,
            }
        }

        # Save state
        save_json(STATE_FILE, state)

        # Append history
        try:
            history = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
            if not isinstance(history, list):
                history = []
            history.append({
                "timestamp": state["timestamp"],
                "sector_score": sector_score,
                "stock_scores": {k: v.get("composite_score", 0) for k, v in stock_cards.items()},
            })
            save_json(HISTORY_FILE, history[-500:])
        except Exception as e:
            logger.error(f"History save failed: {e}")

        return state


# ── Server Integration ───────────────────────

def run_ai_update() -> Dict:
    """Entry point for scheduler/server to trigger an update."""
    engine = AISignalEngine()
    return engine.build_dashboard()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    state = run_ai_update()
    print(f"\nSector score: {state['sector_health']['score']}")
    print(f"Sector status: {state['sector_health']['status']['label']}")
    print(f"Stocks analyzed: {len(state['stock_cards'])}")
    for key, card in sorted(state["stock_cards"].items()):
        print(f"  {card['ticker']:6} | {card['status']:8} | score: {card['composite_score']:+.1f} | "
              f"${card.get('price', 0):>8.2f} | {card.get('category', '?')}")
