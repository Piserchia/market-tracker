"""
Signal Engine
=============
Evaluates all rotation signals and produces a composite score.

Score range per signal: -1 (bearish metals) to +1 (bullish metals)
Composite score: sum of all signals
  >= +2  → HOLD / ADD to metals position
  -1 to +1 → WATCH (mixed signals)
  <= -2  → PREPARE TO ROTATE
  <= -3  → ROTATE NOW
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import THRESHOLDS, ROTATION_SECTORS

logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """A single rotation signal."""
    name: str
    category: str               # "macro", "technical", "fundamental"
    score: float                # -1 to +1
    value: Optional[float]      # The underlying metric value
    threshold_info: str          # Human-readable threshold context
    status: str                  # "bullish", "neutral", "bearish"
    detail: str                  # Explanation
    weight: float = 1.0          # Signal importance weight


@dataclass
class RotationTarget:
    """A potential sector to rotate into."""
    name: str
    sector_key: str
    score: float                 # How favored given current regime
    tickers: List[str]
    rationale: str
    momentum: Optional[Dict] = None  # Recent performance data


@dataclass
class DashboardState:
    """Complete dashboard state for rendering."""
    timestamp: str
    composite_score: float
    composite_status: str        # "HOLD", "WATCH", "PREPARE", "ROTATE"
    signals: List[Dict]
    rotation_targets: List[Dict]
    prices: Dict[str, float]
    changes: Dict
    alert_level: str             # "green", "yellow", "orange", "red"
    alert_message: str
    previous_score: Optional[float] = None
    score_trend: Optional[str] = None  # "improving", "stable", "deteriorating"


class SignalEngine:
    """Computes all rotation signals from a data snapshot."""

    def __init__(self, snapshot: Dict[str, Any]):
        self.snap = snapshot
        self.signals: List[Signal] = []

    def evaluate_all(self) -> List[Signal]:
        """Run all signal evaluations."""
        self.signals = []

        self._eval_oil_geopolitical()
        self._eval_real_rates()
        self._eval_dxy()
        self._eval_gdx_gld_ratio()
        self._eval_gold_margin_proxy()
        self._eval_gdx_rsi()
        self._eval_gdx_200sma()
        self._eval_gold_trend()
        self._eval_silver_gold_ratio()
        self._eval_sector_rotation_flow()

        return self.signals

    # ── Signal 1: Oil / Geopolitical ──────────────

    def _eval_oil_geopolitical(self):
        oil = self.snap.get("prices", {}).get("oil")
        if oil is None:
            return

        if oil >= THRESHOLDS.oil_bullish_floor:
            score = 1.0
            status = "bullish"
            detail = f"Brent at ${oil:.0f} — elevated geopolitical risk supports metals"
        elif oil <= THRESHOLDS.oil_bearish_ceiling:
            score = -1.0
            status = "bearish"
            detail = f"Brent at ${oil:.0f} — calm markets, risk-on favored over havens"
        else:
            score = 0.0
            status = "neutral"
            detail = f"Brent at ${oil:.0f} — moderate range, no strong signal"

        self.signals.append(Signal(
            name="Oil / Geopolitical Risk",
            category="macro",
            score=score,
            value=oil,
            threshold_info=f"Bullish >{THRESHOLDS.oil_bullish_floor} | Bearish <{THRESHOLDS.oil_bearish_ceiling}",
            status=status,
            detail=detail,
            weight=1.5,  # High weight — dominant near-term driver
        ))

    # ── Signal 2: Real Interest Rates ─────────────

    def _eval_real_rates(self):
        real_rate = self.snap.get("macro", {}).get("real_rate_10y")
        tips = self.snap.get("macro", {}).get("tips_10y")

        rate = real_rate if real_rate is not None else tips
        if rate is None:
            return

        if rate >= THRESHOLDS.real_rate_danger:
            score = -1.0
            status = "bearish"
            detail = f"Real rate at {rate:.2f}% — strongly negative for gold"
        elif rate >= THRESHOLDS.real_rate_warning:
            score = -0.5
            status = "bearish"
            detail = f"Real rate at {rate:.2f}% — headwind building for metals"
        elif rate <= THRESHOLDS.real_rate_bullish:
            score = 1.0
            status = "bullish"
            detail = f"Real rate at {rate:.2f}% — deeply negative, very bullish gold"
        else:
            score = 0.0
            status = "neutral"
            detail = f"Real rate at {rate:.2f}% — moderate, no strong directional signal"

        self.signals.append(Signal(
            name="Real Interest Rate (10Y TIPS)",
            category="macro",
            score=score,
            value=rate,
            threshold_info=f"Bullish <{THRESHOLDS.real_rate_bullish}% | Bearish >{THRESHOLDS.real_rate_danger}%",
            status=status,
            detail=detail,
            weight=1.5,
        ))

    # ── Signal 3: US Dollar Index ─────────────────

    def _eval_dxy(self):
        dxy = self.snap.get("prices", {}).get("dxy")
        if dxy is None:
            return

        if dxy >= THRESHOLDS.dxy_strong_bearish:
            score = -1.0
            status = "bearish"
            detail = f"DXY at {dxy:.1f} — strong dollar, major headwind for metals"
        elif dxy >= THRESHOLDS.dxy_bearish_metals:
            score = -0.5
            status = "bearish"
            detail = f"DXY at {dxy:.1f} — firming dollar, headwind building"
        elif dxy <= THRESHOLDS.dxy_bullish_metals:
            score = 1.0
            status = "bullish"
            detail = f"DXY at {dxy:.1f} — weak dollar, strong tailwind for metals"
        else:
            score = 0.0
            status = "neutral"
            detail = f"DXY at {dxy:.1f} — moderate range"

        self.signals.append(Signal(
            name="US Dollar Index (DXY)",
            category="macro",
            score=score,
            value=dxy,
            threshold_info=f"Bullish <{THRESHOLDS.dxy_bullish_metals} | Bearish >{THRESHOLDS.dxy_bearish_metals}",
            status=status,
            detail=detail,
            weight=1.0,
        ))

    # ── Signal 4: GDX/GLD Ratio Trend ─────────────

    def _eval_gdx_gld_ratio(self):
        slope = self.snap.get("ratios", {}).get("gdx_gld_slope_20d")
        ratio = self.snap.get("ratios", {}).get("gdx_gld")
        if slope is None:
            return

        if slope <= THRESHOLDS.gdx_gld_slope_danger:
            score = -1.0
            status = "bearish"
            detail = f"GDX/GLD slope {slope:.5f} — miners strongly underperforming metal"
        elif slope <= THRESHOLDS.gdx_gld_slope_warning:
            score = -0.5
            status = "bearish"
            detail = f"GDX/GLD slope {slope:.5f} — miners starting to lag"
        elif slope > 0:
            score = 1.0
            status = "bullish"
            detail = f"GDX/GLD slope {slope:.5f} — miners outperforming metal (leverage working)"
        else:
            score = 0.0
            status = "neutral"
            detail = f"GDX/GLD slope {slope:.5f} — roughly tracking"

        self.signals.append(Signal(
            name="GDX/GLD Ratio Trend",
            category="technical",
            score=score,
            value=slope,
            threshold_info=f"Bullish: positive slope | Bearish: slope < {THRESHOLDS.gdx_gld_slope_warning}",
            status=status,
            detail=detail + (f" | Ratio: {ratio:.4f}" if ratio else ""),
            weight=1.25,
        ))

    # ── Signal 5: Gold Price / AISC Margin Proxy ──

    def _eval_gold_margin_proxy(self):
        gold = self.snap.get("prices", {}).get("gold")
        if gold is None:
            return

        # AISC estimate: ~$1,800/oz midpoint guidance for 2026
        aisc_est = 1800
        margin = gold - aisc_est
        margin_pct = (margin / gold) * 100

        if gold <= THRESHOLDS.gold_aisc_floor:
            score = -1.0
            status = "bearish"
            detail = f"Gold at ${gold:.0f} — margin compression risk (est. margin ${margin:.0f}/oz, {margin_pct:.0f}%)"
        elif gold >= THRESHOLDS.gold_aisc_comfort:
            score = 1.0
            status = "bullish"
            detail = f"Gold at ${gold:.0f} — est. margin ${margin:.0f}/oz ({margin_pct:.0f}%) = extreme profitability"
        else:
            score = 0.0
            status = "neutral"
            detail = f"Gold at ${gold:.0f} — est. margin ${margin:.0f}/oz ({margin_pct:.0f}%)"

        self.signals.append(Signal(
            name="AISC Margin Proxy",
            category="fundamental",
            score=score,
            value=margin_pct,
            threshold_info=f"Gold >{THRESHOLDS.gold_aisc_comfort} = healthy | <{THRESHOLDS.gold_aisc_floor} = danger",
            status=status,
            detail=detail,
            weight=1.0,
        ))

    # ── Signal 6: GDX RSI ─────────────────────────

    def _eval_gdx_rsi(self):
        rsi = self.snap.get("technicals", {}).get("gdx", {}).get("rsi")
        if rsi is None:
            return

        if rsi >= THRESHOLDS.rsi_extreme_overbought:
            score = -0.75
            status = "bearish"
            detail = f"GDX RSI at {rsi:.1f} — extremely overbought, high pullback risk"
        elif rsi >= THRESHOLDS.rsi_overbought:
            score = -0.25
            status = "bearish"
            detail = f"GDX RSI at {rsi:.1f} — overbought, momentum may be peaking"
        elif rsi <= THRESHOLDS.rsi_oversold:
            score = 0.75
            status = "bullish"
            detail = f"GDX RSI at {rsi:.1f} — oversold, potential bounce setup"
        else:
            score = 0.0
            status = "neutral"
            detail = f"GDX RSI at {rsi:.1f} — neutral range"

        self.signals.append(Signal(
            name="GDX RSI (14-day)",
            category="technical",
            score=score,
            value=rsi,
            threshold_info=f"Overbought >{THRESHOLDS.rsi_overbought} | Oversold <{THRESHOLDS.rsi_oversold}",
            status=status,
            detail=detail,
            weight=0.75,
        ))

    # ── Signal 7: GDX vs 200-day SMA ─────────────

    def _eval_gdx_200sma(self):
        sma_data = self.snap.get("technicals", {}).get("gdx", {}).get("sma200")
        if sma_data is None:
            return

        above = sma_data.get("above", True)
        pct = sma_data.get("pct_above", 0)

        if not above:
            score = -1.0
            status = "bearish"
            detail = f"GDX {pct:.1f}% below 200-SMA — trend broken, bearish"
        elif pct > 50:
            score = -0.25
            status = "bearish"
            detail = f"GDX {pct:.1f}% above 200-SMA — extremely extended"
        elif pct > 20:
            score = 0.25
            status = "bullish"
            detail = f"GDX {pct:.1f}% above 200-SMA — strong trend"
        else:
            score = 0.5
            status = "bullish"
            detail = f"GDX {pct:.1f}% above 200-SMA — healthy trend"

        self.signals.append(Signal(
            name="GDX vs 200-Day SMA",
            category="technical",
            score=score,
            value=pct,
            threshold_info="Above 200-SMA = bullish trend | Below = bearish",
            status=status,
            detail=detail,
            weight=1.0,
        ))

    # ── Signal 8: Gold Trend (50 vs 200 SMA) ─────

    def _eval_gold_trend(self):
        sma50 = self.snap.get("technicals", {}).get("gold", {}).get("sma50")
        sma200 = self.snap.get("technicals", {}).get("gold", {}).get("sma200")

        if sma50 is None or sma200 is None:
            return

        sma50_val = sma50.get("sma", 0)
        sma200_val = sma200.get("sma", 0)

        if sma200_val == 0:
            return

        if sma50_val > sma200_val:
            score = 0.5
            status = "bullish"
            detail = f"Gold 50-SMA (${sma50_val:.0f}) > 200-SMA (${sma200_val:.0f}) — golden cross, bullish trend"
        else:
            score = -1.0
            status = "bearish"
            detail = f"Gold 50-SMA (${sma50_val:.0f}) < 200-SMA (${sma200_val:.0f}) — death cross, bearish"

        self.signals.append(Signal(
            name="Gold Price Trend (50/200 SMA)",
            category="technical",
            score=score,
            value=sma50_val - sma200_val,
            threshold_info="Golden cross (50 > 200) = bullish | Death cross = bearish",
            status=status,
            detail=detail,
            weight=1.0,
        ))

    # ── Signal 9: Silver/Gold Ratio ───────────────

    def _eval_silver_gold_ratio(self):
        gold = self.snap.get("prices", {}).get("gold")
        silver = self.snap.get("prices", {}).get("silver")
        if gold is None or silver is None or silver == 0:
            return

        ratio = gold / silver  # Gold/Silver ratio

        if ratio > 90:
            score = 0.5
            status = "bullish"
            detail = f"Gold/Silver ratio at {ratio:.1f} — silver undervalued, room to catch up"
        elif ratio < 60:
            score = -0.5
            status = "bearish"
            detail = f"Gold/Silver ratio at {ratio:.1f} — silver overextended vs gold"
        else:
            score = 0.0
            status = "neutral"
            detail = f"Gold/Silver ratio at {ratio:.1f} — normal range"

        self.signals.append(Signal(
            name="Gold/Silver Ratio",
            category="fundamental",
            score=score,
            value=ratio,
            threshold_info="High (>90) = silver undervalued | Low (<60) = silver overextended",
            status=status,
            detail=detail,
            weight=0.5,
        ))

    # ── Signal 10: Sector Rotation Flow ───────────

    def _eval_sector_rotation_flow(self):
        """Compare GDX momentum vs SPY/QQQ momentum."""
        gdx_1m = self.snap.get("changes", {}).get("gdx", {}).get("1m")
        spy_1m = self.snap.get("changes", {}).get("spy", {}).get("1m")

        if gdx_1m is None or spy_1m is None:
            return

        spread = gdx_1m - spy_1m

        if spread > 10:
            score = 0.75
            status = "bullish"
            detail = f"GDX 1M: {gdx_1m:+.1f}% vs SPY {spy_1m:+.1f}% — miners dominating broad market"
        elif spread < -10:
            score = -0.75
            status = "bearish"
            detail = f"GDX 1M: {gdx_1m:+.1f}% vs SPY {spy_1m:+.1f}% — money rotating out of miners"
        elif spread < -5:
            score = -0.25
            status = "bearish"
            detail = f"GDX 1M: {gdx_1m:+.1f}% vs SPY {spy_1m:+.1f}% — miners lagging"
        else:
            score = 0.0
            status = "neutral"
            detail = f"GDX 1M: {gdx_1m:+.1f}% vs SPY {spy_1m:+.1f}% — roughly in line"

        self.signals.append(Signal(
            name="Sector Flow (GDX vs SPY)",
            category="technical",
            score=score,
            value=spread,
            threshold_info="GDX outperforming SPY 1M = bullish | Underperforming = bearish",
            status=status,
            detail=detail,
            weight=0.75,
        ))

    # ── Composite Score ───────────────────────────

    def compute_composite(self) -> tuple:
        """Compute weighted composite score and status."""
        if not self.signals:
            self.evaluate_all()

        weighted_sum = sum(s.score * s.weight for s in self.signals)
        total_weight = sum(s.weight for s in self.signals)
        composite = weighted_sum / total_weight * len(self.signals) if total_weight > 0 else 0

        # Normalize to roughly -10 to +10 range
        composite = round(weighted_sum, 2)

        if composite <= THRESHOLDS.bearish_threshold:
            status = "ROTATE"
            alert_level = "red"
            alert_msg = "⛔ ROTATION SIGNAL: Multiple bearish indicators firing. Consider exiting mining positions."
        elif composite <= THRESHOLDS.warning_threshold:
            status = "PREPARE"
            alert_level = "orange"
            alert_msg = "⚠️ WARNING: Signals deteriorating. Tighten stops, identify rotation targets."
        elif composite >= THRESHOLDS.bullish_threshold:
            status = "HOLD"
            alert_level = "green"
            alert_msg = "✅ HOLD: Macro and technical signals support mining position."
        else:
            status = "WATCH"
            alert_level = "yellow"
            alert_msg = "👀 MIXED: Some signals shifting. Monitor closely."

        return composite, status, alert_level, alert_msg

    # ── Rotation Targets ──────────────────────────

    def score_rotation_targets(self) -> List[RotationTarget]:
        """Score potential rotation sectors based on current regime."""
        targets = []
        regime_flags = self._identify_regime()

        for key, sector in ROTATION_SECTORS.items():
            match_count = sum(1 for cond in sector["favored_when"] if cond in regime_flags)
            total_cond = len(sector["favored_when"])
            sector_score = match_count / total_cond if total_cond > 0 else 0

            # Add momentum data if available
            momentum = {}
            for ticker in sector["tickers"]:
                t_lower = ticker.lower()
                changes = self.snap.get("changes", {}).get(t_lower, {})
                if changes:
                    momentum[ticker] = changes

            targets.append(RotationTarget(
                name=sector["name"],
                sector_key=key,
                score=round(sector_score, 2),
                tickers=sector["tickers"],
                rationale=sector["description"],
                momentum=momentum if momentum else None,
            ))

        targets.sort(key=lambda t: t.score, reverse=True)
        return targets

    def _identify_regime(self) -> List[str]:
        """Identify current macro regime flags for rotation scoring."""
        flags = []
        prices = self.snap.get("prices", {})
        macro = self.snap.get("macro", {})

        oil = prices.get("oil", 80)
        if oil < 75:
            flags.append("oil_falling")
        if oil > 90:
            flags.append("oil_rising")

        dxy = prices.get("dxy", 103)
        if dxy < 100:
            flags.append("dxy_falling")

        real_rate = macro.get("real_rate_10y", macro.get("tips_10y", 1.0))
        if real_rate is not None:
            if real_rate < 1.0:
                flags.append("rates_cutting")
                flags.append("real_rates_falling")

        fed = macro.get("fed_funds")
        if fed is not None and fed < 4.0:
            flags.append("rates_cutting")

        # Simple volatility check
        spy_1m = self.snap.get("changes", {}).get("spy", {}).get("1m", 0)
        if spy_1m > 0:
            flags.append("growth_stable")
            flags.append("volatility_falling")
        if spy_1m > 3:
            flags.append("wages_rising")  # Proxy: strong market = strong economy
            flags.append("consumer_confidence_up")

        if macro.get("cpi_yoy") and macro["cpi_yoy"] > 3.0:
            flags.append("inflation_sticky")

        return flags

    # ── Build Full Dashboard State ────────────────

    def build_dashboard_state(self, previous_score: Optional[float] = None) -> Dict:
        """Build the complete dashboard state object."""
        signals = self.evaluate_all()
        composite, status, alert_level, alert_msg = self.compute_composite()
        targets = self.score_rotation_targets()

        # Score trend
        score_trend = None
        if previous_score is not None:
            diff = composite - previous_score
            if diff > 0.5:
                score_trend = "improving"
            elif diff < -0.5:
                score_trend = "deteriorating"
            else:
                score_trend = "stable"

        state = {
            "timestamp": self.snap.get("timestamp", datetime.now().isoformat()),
            "composite_score": composite,
            "composite_status": status,
            "alert_level": alert_level,
            "alert_message": alert_msg,
            "previous_score": previous_score,
            "score_trend": score_trend,
            "signals": [
                {
                    "name": s.name,
                    "category": s.category,
                    "score": s.score,
                    "value": s.value,
                    "threshold_info": s.threshold_info,
                    "status": s.status,
                    "detail": s.detail,
                    "weight": s.weight,
                }
                for s in signals
            ],
            "rotation_targets": [
                {
                    "name": t.name,
                    "sector_key": t.sector_key,
                    "score": t.score,
                    "tickers": t.tickers,
                    "rationale": t.rationale,
                    "momentum": t.momentum,
                }
                for t in targets
            ],
            "prices": self.snap.get("prices", {}),
            "changes": self.snap.get("changes", {}),
            "ratios": self.snap.get("ratios", {}),
            "macro": self.snap.get("macro", {}),
            "technicals": self.snap.get("technicals", {}),
        }

        return state
