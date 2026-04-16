"""
Crypto Signal Engine
====================
Computes signals for crypto portfolio using free APIs:
  - CoinGecko: Prices, market caps, dominance
  - DeFiLlama: TVL, stablecoin supply
  - Alternative.me: Fear & Greed Index
  - Yahoo Finance: Price technicals (RSI, SMA, MACD)
  - Computed: Correlation, cycle position, valuation zones

Layers:
  1. Market Health (Fear & Greed, dominance, stablecoin supply, funding, correlation)
  2. Per-Asset Technicals (RSI, SMA, MACD, % from ATH, volatility)
  3. Per-Asset Fundamentals (TVL, active addresses, network revenue — where available)
  4. Profile-Based Custom Thresholds (from crypto_profiles.json)
  5. Macro Overlay (DXY, 10Y yield, oil, S&P correlation)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(BASE_DIR, "crypto_portfolio.json")
PROFILES_FILE = os.path.join(BASE_DIR, "crypto_profiles.json")
STATE_FILE = os.path.join(BASE_DIR, "data", "crypto_dashboard_state.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "crypto_signal_history.json")

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
DEFILLAMA_BASE = "https://api.llama.fi"
FEAR_GREED_URL = "https://api.alternative.me/fng/"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


class CryptoSignalEngine:

    def __init__(self):
        self.portfolio = {}
        self.profiles = {}
        self.price_data: Dict[str, pd.DataFrame] = {}
        self.market_data: Dict[str, Any] = {}

    def load_config(self):
        self.portfolio = load_json(PORTFOLIO_FILE)
        self.profiles = load_json(PROFILES_FILE)

    def get_all_symbols(self) -> List[str]:
        """Get all symbols from holdings + watchlist."""
        symbols = set()
        for h in self.portfolio.get("holdings", []):
            symbols.add(h["symbol"])
        for w in self.portfolio.get("watchlist", []):
            symbols.add(w["symbol"])
        return sorted(symbols)

    # ── API Fetchers ─────────────────────────────

    def fetch_coingecko_market(self):
        """Fetch market data for all tracked coins from CoinGecko."""
        profiles = self.profiles.get("profiles", {})
        ids = []
        for sym in self.get_all_symbols():
            p = profiles.get(sym, {})
            cg_id = p.get("coingecko_id", sym.lower())
            ids.append(cg_id)

        if not ids:
            return

        try:
            resp = requests.get(f"{COINGECKO_BASE}/coins/markets", params={
                "vs_currency": "usd",
                "ids": ",".join(ids),
                "order": "market_cap_desc",
                "sparkline": "false",
                "price_change_percentage": "1h,24h,7d,30d"
            }, timeout=15)
            resp.raise_for_status()
            for coin in resp.json():
                self.market_data[coin["symbol"].upper()] = {
                    "price": coin.get("current_price"),
                    "market_cap": coin.get("market_cap"),
                    "volume_24h": coin.get("total_volume"),
                    "change_24h": coin.get("price_change_percentage_24h"),
                    "change_7d": coin.get("price_change_percentage_7d_in_currency"),
                    "change_30d": coin.get("price_change_percentage_30d_in_currency"),
                    "ath": coin.get("ath"),
                    "ath_date": coin.get("ath_date"),
                    "atl": coin.get("atl"),
                    "circulating_supply": coin.get("circulating_supply"),
                    "total_supply": coin.get("total_supply"),
                    "market_cap_rank": coin.get("market_cap_rank"),
                }
        except Exception as e:
            logger.error(f"CoinGecko market fetch failed: {e}")

    def fetch_global_data(self):
        """Fetch global crypto market data."""
        try:
            resp = requests.get(f"{COINGECKO_BASE}/global", timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", {})
            self.market_data["_global"] = {
                "total_market_cap": data.get("total_market_cap", {}).get("usd"),
                "total_volume": data.get("total_volume", {}).get("usd"),
                "btc_dominance": data.get("market_cap_percentage", {}).get("btc"),
                "eth_dominance": data.get("market_cap_percentage", {}).get("eth"),
                "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd"),
                "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            }
        except Exception as e:
            logger.error(f"CoinGecko global fetch failed: {e}")

    def fetch_fear_greed(self):
        """Fetch Fear & Greed Index."""
        try:
            resp = requests.get(FEAR_GREED_URL, params={"limit": 30}, timeout=10)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            if data:
                latest = data[0]
                self.market_data["_fear_greed"] = {
                    "value": int(latest["value"]),
                    "classification": latest["value_classification"],
                    "timestamp": latest["timestamp"],
                    "history": [{"value": int(d["value"]), "date": d["timestamp"]} for d in data[:30]]
                }
        except Exception as e:
            logger.error(f"Fear & Greed fetch failed: {e}")

    def fetch_defi_tvl(self):
        """Fetch TVL data from DeFiLlama."""
        for chain in ["Ethereum", "Solana", "Avalanche"]:
            try:
                resp = requests.get(f"{DEFILLAMA_BASE}/v2/historicalChainTvl/{chain}", timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data:
                    latest = data[-1] if isinstance(data, list) else None
                    prev_30d = data[-31] if isinstance(data, list) and len(data) > 31 else None
                    symbol = {"Ethereum": "ETH", "Solana": "SOL", "Avalanche": "AVAX"}.get(chain)
                    if symbol and latest:
                        tvl_now = latest.get("tvl", 0)
                        tvl_30d = prev_30d.get("tvl", tvl_now) if prev_30d else tvl_now
                        growth = ((tvl_now - tvl_30d) / tvl_30d * 100) if tvl_30d > 0 else 0
                        self.market_data.setdefault(symbol, {})["tvl"] = round(tvl_now)
                        self.market_data[symbol]["tvl_30d_growth"] = round(growth, 1)
            except Exception as e:
                logger.warning(f"DeFiLlama TVL fetch failed for {chain}: {e}")

    def fetch_stablecoin_supply(self):
        """Fetch total stablecoin supply from DeFiLlama."""
        try:
            resp = requests.get(f"{DEFILLAMA_BASE}/stablecoins", timeout=10)
            resp.raise_for_status()
            data = resp.json().get("peggedAssets", [])
            total = sum(
                s.get("circulating", {}).get("peggedUSD", 0)
                for s in data
                if s.get("symbol") in ("USDT", "USDC", "DAI", "FDUSD")
            )
            self.market_data["_stablecoins"] = {"total_supply": round(total)}
        except Exception as e:
            logger.warning(f"Stablecoin supply fetch failed: {e}")

    def fetch_price_history(self):
        """Fetch 1-year daily price history via Yahoo Finance for technicals."""
        profiles = self.profiles.get("profiles", {})
        symbols = []
        for sym in self.get_all_symbols():
            p = profiles.get(sym, {})
            yf_sym = p.get("yahoo_symbol", f"{sym}-USD")
            symbols.append((sym, yf_sym))

        # Add macro tickers
        macro = [("SPY", "SPY"), ("DXY", "DX-Y.NYB"), ("TNX", "^TNX"), ("OIL", "BZ=F")]
        all_yf = [s[1] for s in symbols + macro]

        try:
            raw = yf.download(all_yf, period="1y", interval="1d",
                              group_by="ticker", threads=True, progress=False)
        except Exception as e:
            logger.error(f"Yahoo download failed: {e}")
            raw = None

        for orig_sym, yf_sym in symbols + macro:
            try:
                if raw is not None and len(all_yf) > 1:
                    if yf_sym in raw.columns.get_level_values(0):
                        df = raw[yf_sym].dropna(how="all")
                    else:
                        df = pd.DataFrame()
                else:
                    df = raw if raw is not None else pd.DataFrame()

                if df.empty:
                    df = yf.Ticker(yf_sym).history(period="1y", interval="1d")

                if not df.empty:
                    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                    self.price_data[orig_sym] = df
            except Exception as e:
                logger.warning(f"  {orig_sym} ({yf_sym}): {e}")

    # ── Technical Computations ───────────────────

    def _series(self, sym, col="close"):
        df = self.price_data.get(sym)
        if df is not None and col in df.columns:
            return df[col].dropna()
        return None

    def _rsi(self, sym, period=14):
        s = self._series(sym)
        if s is None or len(s) < period + 1:
            return None
        d = s.diff()
        g = d.where(d > 0, 0.0).rolling(period).mean()
        l = (-d).where(d < 0, 0.0).rolling(period).mean()
        rs = g / l
        rsi = 100 - (100 / (1 + rs))
        v = rsi.iloc[-1]
        return round(float(v), 1) if not pd.isna(v) else None

    def _sma(self, sym, w):
        s = self._series(sym)
        if s is None or len(s) < w:
            return None
        return round(float(s.rolling(w).mean().iloc[-1]), 2)

    def _macd(self, sym):
        s = self._series(sym)
        if s is None or len(s) < 35:
            return None
        e12 = s.ewm(span=12).mean()
        e26 = s.ewm(span=26).mean()
        m = e12 - e26
        sig = m.ewm(span=9).mean()
        h = m - sig
        return {"macd": round(float(m.iloc[-1]), 4), "signal": round(float(sig.iloc[-1]), 4),
                "histogram": round(float(h.iloc[-1]), 4)}

    def _pct_change(self, sym, days):
        s = self._series(sym)
        if s is None or len(s) < days + 1:
            return None
        c = float(s.iloc[-1])
        p = float(s.iloc[-(days + 1)])
        return round((c - p) / p * 100, 2) if p != 0 else None

    def _price(self, sym):
        s = self._series(sym)
        return float(s.iloc[-1]) if s is not None and len(s) > 0 else None

    def _volatility_30d(self, sym):
        s = self._series(sym)
        if s is None or len(s) < 31:
            return None
        returns = s.pct_change().dropna().iloc[-30:]
        return round(float(returns.std() * np.sqrt(365) * 100), 1)

    def _correlation(self, sym_a, sym_b, window=30):
        sa = self._series(sym_a)
        sb = self._series(sym_b)
        if sa is None or sb is None:
            return None
        df = pd.DataFrame({"a": sa, "b": sb}).dropna()
        if len(df) < window:
            return None
        corr = df["a"].pct_change().iloc[-window:].corr(df["b"].pct_change().iloc[-window:])
        return round(float(corr), 3) if not pd.isna(corr) else None

    # ── Signal Computation ───────────────────────

    def compute_market_signals(self) -> List[Dict]:
        """Layer 1: Market-wide health signals."""
        signals = []

        # Fear & Greed
        fg = self.market_data.get("_fear_greed", {})
        if fg.get("value") is not None:
            v = fg["value"]
            score = 1.0 if v < 20 else (0.5 if v < 35 else (0.0 if v < 65 else (-0.5 if v < 80 else -1.0)))
            signals.append({
                "name": "Fear & Greed Index", "layer": 1, "value": v,
                "score": score,
                "status": "bullish" if v < 25 else ("neutral" if v < 65 else "bearish"),
                "detail": f"F&G: {v} ({fg.get('classification', '?')}) — {'extreme fear = contrarian buy' if v < 20 else ('greedy = caution' if v > 75 else 'moderate')}",
                "source": "Alternative.me", "frequency": "Daily"
            })

        # BTC Dominance
        glob = self.market_data.get("_global", {})
        dom = glob.get("btc_dominance")
        if dom:
            signals.append({
                "name": "BTC Dominance", "layer": 1, "value": round(dom, 1),
                "score": 0.0,
                "status": "neutral" if 45 < dom < 65 else ("bearish" if dom > 65 else "bullish"),
                "detail": f"BTC dominance {dom:.1f}% — {'BTC season, alts lagging' if dom > 55 else 'alt season potential' if dom < 45 else 'balanced'}",
                "source": "CoinGecko", "frequency": "Real-time"
            })

        # Stablecoin supply
        sc = self.market_data.get("_stablecoins", {})
        if sc.get("total_supply"):
            supply_b = sc["total_supply"] / 1e9
            signals.append({
                "name": "Stablecoin Supply", "layer": 1, "value": round(supply_b, 1),
                "score": 0.25,
                "status": "neutral",
                "detail": f"${supply_b:.0f}B in stablecoins — dry powder available",
                "source": "DeFiLlama", "frequency": "Daily"
            })

        # BTC/S&P correlation
        corr = self._correlation("BTC", "SPY")
        if corr is not None:
            signals.append({
                "name": "BTC/S&P 500 Correlation", "layer": 1, "value": corr,
                "score": -0.25 if corr > 0.7 else 0.25,
                "status": "bearish" if corr > 0.7 else "neutral",
                "detail": f"30-day correlation: {corr:.2f} — {'high: macro drives crypto' if corr > 0.7 else 'moderate: crypto has some independence'}",
                "source": "Computed (Yahoo Finance)", "frequency": "Daily"
            })

        # DXY
        dxy = self._price("DXY")
        if dxy:
            score = 0.5 if dxy < 100 else (0.0 if dxy < 105 else -0.5)
            signals.append({
                "name": "US Dollar (DXY)", "layer": 1, "value": round(dxy, 1),
                "score": score,
                "status": "bullish" if dxy < 100 else ("neutral" if dxy < 105 else "bearish"),
                "detail": f"DXY {dxy:.1f} — {'weak dollar supports crypto' if dxy < 100 else 'strong dollar headwind' if dxy > 105 else 'neutral'}",
                "source": "Yahoo Finance", "frequency": "Real-time"
            })

        return signals

    def compute_asset_signals(self, symbol: str) -> Dict:
        """Layer 2+3+4: Per-asset signals."""
        cg = self.market_data.get(symbol, {})
        price = cg.get("price") or self._price(symbol)
        profile = self.profiles.get("profiles", {}).get(symbol, self.profiles.get("default_profile", {}))

        result = {
            "symbol": symbol,
            "name": profile.get("name", cg.get("name", symbol)),
            "price": price,
            "category": profile.get("category", "altcoin"),
            "risk_tier": profile.get("risk_tier", "speculative"),
            "thesis": profile.get("thesis", ""),
            "signals": [],
            "technicals": {},
            "market": {},
            "changes": {},
            "sell_triggers": profile.get("sell_triggers", []),
            "buy_signals": profile.get("buy_signals", []),
        }

        # Market data from CoinGecko
        if cg:
            result["market"] = {
                "market_cap": cg.get("market_cap"),
                "volume_24h": cg.get("volume_24h"),
                "market_cap_rank": cg.get("market_cap_rank"),
                "ath": cg.get("ath"),
                "circulating_supply": cg.get("circulating_supply"),
            }
            for k in ["change_24h", "change_7d", "change_30d"]:
                if cg.get(k) is not None:
                    result["changes"][k.replace("change_", "")] = round(cg[k], 1)

        # % from ATH
        ath = cg.get("ath") or profile.get("cycle_info", {}).get("ath")
        if ath and price:
            pct_from_ath = (price - ath) / ath * 100
            result["market"]["pct_from_ath"] = round(pct_from_ath, 1)
            score = 0.5 if pct_from_ath < -50 else (0.0 if pct_from_ath < -20 else -0.25)
            result["signals"].append({
                "name": "% from ATH", "layer": 2, "value": round(pct_from_ath, 1),
                "score": score,
                "status": "bullish" if pct_from_ath < -50 else ("neutral" if pct_from_ath < -20 else "bearish"),
                "detail": f"{pct_from_ath:.0f}% from ATH (${ath:,.0f}) — {'deep discount' if pct_from_ath < -50 else 'moderate pullback' if pct_from_ath < -20 else 'near highs'}",
            })

        # RSI
        rsi = self._rsi(symbol)
        if rsi is not None:
            result["technicals"]["rsi"] = rsi
            result["signals"].append({
                "name": "RSI (14-day)", "layer": 2, "value": rsi,
                "score": 0.5 if rsi < 30 else (-0.5 if rsi > 70 else 0.0),
                "status": "bullish" if rsi < 30 else ("bearish" if rsi > 70 else "neutral"),
                "detail": f"RSI {rsi:.0f} — {'oversold' if rsi < 30 else ('overbought' if rsi > 70 else 'neutral')}",
            })

        # SMA positioning
        sma50 = self._sma(symbol, 50)
        sma200 = self._sma(symbol, 200)
        if sma200 and price:
            pct_vs_200 = (price - sma200) / sma200 * 100
            result["technicals"]["sma50"] = sma50
            result["technicals"]["sma200"] = sma200
            result["technicals"]["pct_vs_200sma"] = round(pct_vs_200, 1)
            result["signals"].append({
                "name": "Trend (200-SMA)", "layer": 2, "value": round(pct_vs_200, 1),
                "score": 0.5 if pct_vs_200 > 0 else -0.75,
                "status": "bullish" if pct_vs_200 > 0 else "bearish",
                "detail": f"{'Above' if pct_vs_200 > 0 else 'BELOW'} 200-SMA by {abs(pct_vs_200):.1f}%",
            })

        # MACD
        macd = self._macd(symbol)
        if macd:
            result["technicals"]["macd"] = macd
            result["signals"].append({
                "name": "MACD", "layer": 2, "value": macd["histogram"],
                "score": 0.25 if macd["histogram"] > 0 else -0.25,
                "status": "bullish" if macd["histogram"] > 0 else "bearish",
                "detail": f"MACD histogram {'positive' if macd['histogram'] > 0 else 'negative'}",
            })

        # 30-day volatility
        vol = self._volatility_30d(symbol)
        if vol:
            result["technicals"]["volatility_30d"] = vol

        # TVL (if available)
        tvl = self.market_data.get(symbol, {}).get("tvl")
        tvl_growth = self.market_data.get(symbol, {}).get("tvl_30d_growth")
        if tvl:
            result["market"]["tvl"] = tvl
            result["market"]["tvl_30d_growth"] = tvl_growth
            if tvl_growth is not None:
                result["signals"].append({
                    "name": "TVL Growth (30d)", "layer": 3, "value": tvl_growth,
                    "score": 0.5 if tvl_growth > 10 else (0.0 if tvl_growth > -5 else -0.5),
                    "status": "bullish" if tvl_growth > 10 else ("neutral" if tvl_growth > -5 else "bearish"),
                    "detail": f"TVL ${tvl/1e9:.1f}B ({tvl_growth:+.1f}% 30d) — {'growing' if tvl_growth > 0 else 'declining'}",
                })

        # Composite
        scores = [s["score"] for s in result["signals"]]
        result["composite_score"] = round(sum(scores), 2) if scores else 0
        n_bull = sum(1 for s in result["signals"] if s["status"] == "bullish")
        n_bear = sum(1 for s in result["signals"] if s["status"] == "bearish")
        result["signal_summary"] = {"bullish": n_bull, "bearish": n_bear, "total": len(scores)}

        cs = result["composite_score"]
        if cs > 1:
            result["status"] = "ACCUMULATE"
            result["status_color"] = "green"
        elif cs > -0.5:
            result["status"] = "HOLD"
            result["status_color"] = "yellow"
        elif cs > -2:
            result["status"] = "CAUTION"
            result["status_color"] = "orange"
        else:
            result["status"] = "REDUCE"
            result["status_color"] = "red"

        return result

    # ── Full Dashboard Build ─────────────────────

    def build_dashboard(self) -> Dict:
        self.load_config()
        logger.info("Fetching crypto data...")
        self.fetch_coingecko_market()
        self.fetch_global_data()
        self.fetch_fear_greed()
        self.fetch_defi_tvl()
        self.fetch_stablecoin_supply()
        self.fetch_price_history()

        # Portfolio summary
        holdings = self.portfolio.get("holdings", [])
        total_value = sum(h.get("dollars", 0) for h in holdings)

        # Market signals
        market_signals = self.compute_market_signals()
        market_score = sum(s["score"] for s in market_signals)

        if market_score >= 1.5:
            market_status = {"label": "BULLISH", "color": "green", "message": "Crypto market conditions are favorable. Consider accumulating."}
        elif market_score >= 0:
            market_status = {"label": "NEUTRAL", "color": "yellow", "message": "Mixed signals. Hold positions, wait for clarity."}
        elif market_score >= -1.5:
            market_status = {"label": "CAUTIOUS", "color": "orange", "message": "Headwinds building. Tighten risk management."}
        else:
            market_status = {"label": "BEARISH", "color": "red", "message": "Multiple bearish signals. Consider reducing exposure."}

        # Per-asset signals
        asset_cards = {}
        all_symbols = self.get_all_symbols()
        for sym in all_symbols:
            card = self.compute_asset_signals(sym)
            # Attach holding info
            for h in holdings:
                if h["symbol"] == sym:
                    card["dollars"] = h.get("dollars", 0)
                    card["amount"] = h.get("amount", 0)
                    card["exchange"] = h.get("exchange", "")
                    card["is_held"] = True
                    break
            else:
                card["is_held"] = False
                card["dollars"] = 0
            asset_cards[sym] = card

        # Halving cycle info
        halving_date = datetime(2024, 4, 20)
        days_since = (datetime.now() - halving_date).days
        next_halving = datetime(2028, 4, 1)
        days_until = (next_halving - datetime.now()).days

        state = {
            "timestamp": datetime.now().isoformat(),
            "portfolio": {"total_value": total_value, "holdings": holdings, "watchlist": self.portfolio.get("watchlist", [])},
            "market_health": {"score": round(market_score, 2), "status": market_status, "signals": market_signals},
            "asset_cards": asset_cards,
            "global": self.market_data.get("_global", {}),
            "fear_greed": self.market_data.get("_fear_greed", {}),
            "cycle": {"days_since_halving": days_since, "days_until_next": days_until, "halving_date": "2024-04-20", "next_halving": "2028-04-01"},
        }

        save_json(STATE_FILE, state)

        # History
        try:
            hist = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
            if not isinstance(hist, list):
                hist = []
            hist.append({"timestamp": state["timestamp"], "market_score": market_score,
                         "btc_price": asset_cards.get("BTC", {}).get("price"),
                         "fear_greed": self.market_data.get("_fear_greed", {}).get("value")})
            save_json(HISTORY_FILE, hist[-500:])
        except Exception as e:
            logger.error(f"History save: {e}")

        return state


def run_crypto_update() -> Dict:
    engine = CryptoSignalEngine()
    return engine.build_dashboard()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    state = run_crypto_update()
    print(f"\nMarket: {state['market_health']['status']['label']} (score: {state['market_health']['score']})")
    fg = state.get("fear_greed", {})
    print(f"Fear & Greed: {fg.get('value', '?')} ({fg.get('classification', '?')})")
    print(f"Cycle: {state['cycle']['days_since_halving']} days since halving")
    for sym, card in sorted(state["asset_cards"].items()):
        held = "💰" if card.get("is_held") else "👀"
        print(f"  {held} {sym:5} | {card['status']:10} | score: {card['composite_score']:+.1f} | ${card.get('price', 0):>10,.2f}")
