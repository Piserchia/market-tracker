import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8787";
const DEMO_MODE = typeof window !== "undefined" && !window.location.port;

// ── Demo data for artifact preview ──────────
const DEMO_STATE = {
  timestamp: new Date().toISOString(),
  composite_score: 3.25,
  composite_status: "HOLD",
  alert_level: "green",
  alert_message: "✅ HOLD: Macro and technical signals support mining position.",
  score_trend: "stable",
  previous_score: 3.0,
  prices: {
    gold: 4728, silver: 73.66, copper: 6.01, oil: 87.2,
    gdx: 97.49, gdxj: 121.24, gld: 437.13, dxy: 99.8,
    spy: 568.2, qqq: 492.1, smh: 245.3, slv: 69.08
  },
  changes: {
    gold: { "1d": -0.04, "1w": 1.5, "1m": 3.2, "3m": 12.4 },
    silver: { "1d": 0.41, "1w": 2.1, "1m": -6.4, "3m": -15.2 },
    copper: { "1d": 0.56, "1w": 3.8, "1m": 5.1, "3m": 18.7 },
    gdx: { "1d": 3.38, "1w": 5.2, "1m": -2.1, "3m": 22.5 },
    gdxj: { "1d": 3.32, "1w": 6.1, "1m": -1.8, "3m": 28.3 },
    oil: { "1d": -1.2, "1w": -3.4, "1m": 15.2, "3m": 22.8 },
    dxy: { "1d": -0.24, "1w": -1.1, "1m": -2.3, "3m": -4.8 },
    spy: { "1d": -0.3, "1w": 1.2, "1m": -3.9, "3m": -2.1 },
    qqq: { "1d": -0.27, "1w": 1.5, "1m": -4.2, "3m": -1.8 }
  },
  ratios: { gdx_gld: 0.2230, gdx_gld_slope_20d: 0.0012, gdxj_gdx: 1.243, gold_spy: 8.32 },
  macro: { tips_10y: 0.42, treasury_10y: 4.29, breakeven_10y: 3.87, fed_funds: 3.625, real_rate_10y: 0.42 },
  signals: [
    { name: "Oil / Geopolitical Risk", category: "macro", score: 1.0, value: 87.2, status: "bullish", detail: "Brent at $87 — elevated geopolitical risk supports metals", threshold_info: "Bullish >85 | Bearish <70", weight: 1.5 },
    { name: "Real Interest Rate (10Y TIPS)", category: "macro", score: 1.0, value: 0.42, status: "bullish", detail: "Real rate at 0.42% — deeply negative, very bullish gold", threshold_info: "Bullish <0.5% | Bearish >2.0%", weight: 1.5 },
    { name: "US Dollar Index (DXY)", category: "macro", score: 1.0, value: 99.8, status: "bullish", detail: "DXY at 99.8 — weak dollar, strong tailwind for metals", threshold_info: "Bullish <100 | Bearish >105", weight: 1.0 },
    { name: "GDX/GLD Ratio Trend", category: "technical", score: 1.0, value: 0.0012, status: "bullish", detail: "GDX/GLD slope 0.00120 — miners outperforming metal", threshold_info: "Bullish: positive slope | Bearish: slope < -0.001", weight: 1.25 },
    { name: "AISC Margin Proxy", category: "fundamental", score: 1.0, value: 62, status: "bullish", detail: "Gold at $4728 — est. margin $2928/oz (62%) = extreme profitability", threshold_info: "Gold >4000 = healthy | <3500 = danger", weight: 1.0 },
    { name: "GDX RSI (14-day)", category: "technical", score: 0.0, value: 53.8, status: "neutral", detail: "GDX RSI at 53.8 — neutral range", threshold_info: "Overbought >75 | Oversold <30", weight: 0.75 },
    { name: "GDX vs 200-Day SMA", category: "technical", score: 0.5, value: 21.7, status: "bullish", detail: "GDX 21.7% above 200-SMA — strong trend", threshold_info: "Above 200-SMA = bullish | Below = bearish", weight: 1.0 },
    { name: "Gold Price Trend (50/200 SMA)", category: "technical", score: 0.5, value: 420, status: "bullish", detail: "Gold 50-SMA > 200-SMA — golden cross, bullish trend", threshold_info: "Golden cross = bullish | Death cross = bearish", weight: 1.0 },
    { name: "Gold/Silver Ratio", category: "fundamental", score: 0.0, value: 64.2, status: "neutral", detail: "Gold/Silver ratio at 64.2 — normal range", threshold_info: "High (>90) = silver undervalued | Low (<60) = overextended", weight: 0.5 },
    { name: "Sector Flow (GDX vs SPY)", category: "technical", score: 0.0, value: 1.8, status: "neutral", detail: "GDX 1M: -2.1% vs SPY -3.9% — roughly in line", threshold_info: "GDX outperforming SPY = bullish", weight: 0.75 }
  ],
  rotation_targets: [
    { name: "Energy", sector_key: "energy", score: 0.5, tickers: ["XLE"], rationale: "Benefits from sustained high energy prices", momentum: { XLE: { "1d": 0.8, "1w": 2.1, "1m": 8.5 } } },
    { name: "AI / Tech Infrastructure", sector_key: "ai_tech", score: 0.33, tickers: ["SMH", "XLK", "QQQ"], rationale: "Semiconductors, cloud, data center buildout", momentum: { SMH: { "1d": -0.5, "1w": 1.8, "1m": -5.2 }, QQQ: { "1d": -0.27, "1w": 1.5, "1m": -4.2 } } },
    { name: "Broad Market (S&P 500)", sector_key: "broad_market", score: 0.0, tickers: ["SPY"], rationale: "Default risk-on allocation", momentum: { SPY: { "1d": -0.3, "1w": 1.2, "1m": -3.9 } } },
    { name: "Rate-Sensitive Growth", sector_key: "rate_sensitive_growth", score: 0.0, tickers: ["ARKK", "XHB", "XLF"], rationale: "Fintech, homebuilders — benefits from rate cuts", momentum: {} },
    { name: "Consumer Discretionary", sector_key: "consumer", score: 0.0, tickers: ["XLY"], rationale: "Rebounds when energy costs drop", momentum: {} }
  ]
};

const DEMO_HISTORY = Array.from({ length: 30 }, (_, i) => ({
  timestamp: new Date(Date.now() - (29 - i) * 86400000).toISOString(),
  composite_score: 2.5 + Math.sin(i / 5) * 2 + Math.random() * 0.5,
  alert_level: i > 25 ? "green" : i > 20 ? "yellow" : "green",
  prices: { gold: 4400 + i * 12 + Math.random() * 50, gdx: 85 + i * 0.5 }
}));

// ── Utility ─────────────────────────────────
const fmt = (n, d = 2) => n != null ? Number(n).toFixed(d) : "—";
const fmtPct = (n) => n != null ? `${n >= 0 ? "+" : ""}${Number(n).toFixed(1)}%` : "—";
const fmtPrice = (n) => n != null ? (n > 100 ? `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` : `$${fmt(n)}`) : "—";

const LEVEL_COLORS = {
  green: "#00e676",
  yellow: "#ffd600",
  orange: "#ff9100",
  red: "#ff1744"
};

const STATUS_CONFIG = {
  HOLD: { color: "#00e676", bg: "rgba(0,230,118,0.08)", icon: "✅", label: "HOLD POSITION" },
  WATCH: { color: "#ffd600", bg: "rgba(255,214,0,0.08)", icon: "👀", label: "WATCH CLOSELY" },
  PREPARE: { color: "#ff9100", bg: "rgba(255,145,0,0.08)", icon: "⚠️", label: "PREPARE TO ROTATE" },
  ROTATE: { color: "#ff1744", bg: "rgba(255,23,68,0.08)", icon: "⛔", label: "ROTATE NOW" }
};

// ── Components ──────────────────────────────

function ScoreGauge({ score, status, trend }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.WATCH;
  const normalized = Math.max(-8, Math.min(8, score));
  const pct = ((normalized + 8) / 16) * 100;
  const trendIcon = trend === "improving" ? "↑" : trend === "deteriorating" ? "↓" : "→";

  return (
    <div style={{ textAlign: "center", padding: "24px 0" }}>
      <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "3px", color: "#8a8f98", marginBottom: "12px", fontFamily: "'JetBrains Mono', monospace" }}>
        Composite Rotation Score
      </div>
      <div style={{ fontSize: "72px", fontWeight: 800, color: cfg.color, lineHeight: 1, fontFamily: "'Space Grotesk', sans-serif" }}>
        {score >= 0 ? "+" : ""}{fmt(score, 1)}
      </div>
      <div style={{ margin: "16px auto", width: "100%", maxWidth: "400px", height: "8px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", position: "relative", overflow: "hidden" }}>
        <div style={{
          position: "absolute", left: 0, top: 0, height: "100%",
          width: `${pct}%`,
          borderRadius: "4px",
          background: `linear-gradient(90deg, #ff1744, #ff9100, #ffd600, #00e676)`,
          transition: "width 0.8s ease"
        }} />
        <div style={{
          position: "absolute", top: "-4px",
          left: `calc(${pct}% - 8px)`,
          width: "16px", height: "16px", borderRadius: "50%",
          background: cfg.color, border: "2px solid #0d1117",
          transition: "left 0.8s ease"
        }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", maxWidth: "400px", margin: "4px auto 0", fontSize: "10px", color: "#555", fontFamily: "monospace" }}>
        <span>ROTATE</span><span>PREPARE</span><span>WATCH</span><span>HOLD</span>
      </div>
      <div style={{
        display: "inline-block", marginTop: "16px",
        padding: "8px 24px", borderRadius: "6px",
        background: cfg.bg, border: `1px solid ${cfg.color}30`,
        color: cfg.color, fontSize: "14px", fontWeight: 700,
        letterSpacing: "2px", fontFamily: "'JetBrains Mono', monospace"
      }}>
        {cfg.icon} {cfg.label}
        {trend && <span style={{ marginLeft: "12px", opacity: 0.7 }}>{trendIcon} {trend}</span>}
      </div>
    </div>
  );
}

function PriceTicker({ label, price, change, prefix = "$" }) {
  const c = change != null ? (change >= 0 ? "#00e676" : "#ff1744") : "#8a8f98";
  return (
    <div style={{ padding: "10px 16px", borderRight: "1px solid #1a1f2e", minWidth: "120px" }}>
      <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "4px", fontFamily: "monospace" }}>{label}</div>
      <div style={{ fontSize: "18px", fontWeight: 700, color: "#e1e4e8", fontFamily: "'Space Grotesk', sans-serif" }}>{fmtPrice(price)}</div>
      <div style={{ fontSize: "12px", color: c, fontFamily: "monospace" }}>{fmtPct(change)}</div>
    </div>
  );
}

function SignalCard({ signal }) {
  const colors = { bullish: "#00e676", neutral: "#ffd600", bearish: "#ff1744" };
  const color = colors[signal.status] || "#8a8f98";
  const scoreBg = signal.score > 0 ? "rgba(0,230,118,0.1)" : signal.score < 0 ? "rgba(255,23,68,0.1)" : "rgba(255,214,0,0.1)";

  return (
    <div style={{
      background: "#0d1117", border: `1px solid #1a1f2e`,
      borderLeft: `3px solid ${color}`,
      borderRadius: "8px", padding: "16px", marginBottom: "8px",
      transition: "border-color 0.3s"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "14px", fontWeight: 700, color: "#e1e4e8" }}>{signal.name}</span>
          <span style={{
            fontSize: "9px", padding: "2px 6px", borderRadius: "3px",
            background: "rgba(255,255,255,0.05)", color: "#8a8f98",
            textTransform: "uppercase", letterSpacing: "1px", fontFamily: "monospace"
          }}>{signal.category}</span>
        </div>
        <div style={{
          fontSize: "16px", fontWeight: 800, color,
          padding: "2px 10px", borderRadius: "4px", background: scoreBg,
          fontFamily: "'JetBrains Mono', monospace"
        }}>
          {signal.score >= 0 ? "+" : ""}{fmt(signal.score, 1)}
        </div>
      </div>
      <div style={{ fontSize: "12px", color: "#8a8f98", lineHeight: 1.5 }}>{signal.detail}</div>
      <div style={{ fontSize: "10px", color: "#444", marginTop: "6px", fontFamily: "monospace" }}>{signal.threshold_info}</div>
    </div>
  );
}

function RotationCard({ target, rank }) {
  const barWidth = Math.max(5, target.score * 100);
  const isTop = rank === 0 && target.score > 0;

  return (
    <div style={{
      background: isTop ? "rgba(0,230,118,0.04)" : "#0d1117",
      border: `1px solid ${isTop ? "rgba(0,230,118,0.2)" : "#1a1f2e"}`,
      borderRadius: "8px", padding: "16px", marginBottom: "8px"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isTop && <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "3px", background: "rgba(0,230,118,0.15)", color: "#00e676", fontWeight: 700 }}>TOP PICK</span>}
          <span style={{ fontSize: "14px", fontWeight: 700, color: "#e1e4e8" }}>{target.name}</span>
        </div>
        <span style={{ fontSize: "14px", fontWeight: 700, color: target.score > 0.3 ? "#00e676" : "#8a8f98", fontFamily: "monospace" }}>
          {(target.score * 100).toFixed(0)}%
        </span>
      </div>
      <div style={{ height: "4px", borderRadius: "2px", background: "rgba(255,255,255,0.05)", marginBottom: "8px" }}>
        <div style={{ height: "100%", borderRadius: "2px", width: `${barWidth}%`, background: target.score > 0.3 ? "#00e676" : "#444", transition: "width 0.5s" }} />
      </div>
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "6px" }}>
        {target.tickers.map(t => (
          <span key={t} style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "4px", background: "rgba(255,255,255,0.06)", color: "#b0b3b8", fontFamily: "monospace", fontWeight: 600 }}>{t}</span>
        ))}
      </div>
      <div style={{ fontSize: "11px", color: "#666" }}>{target.rationale}</div>
      {target.momentum && Object.keys(target.momentum).length > 0 && (
        <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
          {Object.entries(target.momentum).map(([ticker, changes]) => (
            <div key={ticker} style={{ fontSize: "10px", color: "#8a8f98", fontFamily: "monospace" }}>
              {ticker}: <span style={{ color: (changes["1m"] || 0) >= 0 ? "#00e676" : "#ff1744" }}>{fmtPct(changes["1m"])} 1M</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MacroRow({ label, value, format, thresholds }) {
  let color = "#e1e4e8";
  if (thresholds) {
    const v = Number(value);
    if (thresholds.bullishBelow != null && v < thresholds.bullishBelow) color = "#00e676";
    else if (thresholds.bearishAbove != null && v > thresholds.bearishAbove) color = "#ff1744";
    else if (thresholds.warnAbove != null && v > thresholds.warnAbove) color = "#ffd600";
  }
  const formatted = format === "pct" ? `${fmt(value)}%` : format === "dollar" ? fmtPrice(value) : fmt(value);

  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #1a1f2e" }}>
      <span style={{ fontSize: "12px", color: "#8a8f98" }}>{label}</span>
      <span style={{ fontSize: "13px", fontWeight: 600, color, fontFamily: "monospace" }}>{formatted}</span>
    </div>
  );
}

function MiniChart({ history }) {
  if (!history || history.length < 2) return null;
  const scores = history.map(h => h.composite_score);
  const min = Math.min(...scores) - 1;
  const max = Math.max(...scores) + 1;
  const range = max - min || 1;
  const w = 400;
  const h = 80;
  const points = scores.map((s, i) => {
    const x = (i / (scores.length - 1)) * w;
    const y = h - ((s - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");

  const latest = scores[scores.length - 1];
  const latestColor = latest >= 2 ? "#00e676" : latest >= -1 ? "#ffd600" : latest >= -3 ? "#ff9100" : "#ff1744";

  return (
    <div style={{ padding: "16px", background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e" }}>
      <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontFamily: "monospace" }}>
        Score History (30 days)
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "80px" }}>
        <line x1="0" y1={h - ((-3 - min) / range) * h} x2={w} y2={h - ((-3 - min) / range) * h} stroke="#ff174433" strokeDasharray="4" />
        <line x1="0" y1={h - ((2 - min) / range) * h} x2={w} y2={h - ((2 - min) / range) * h} stroke="#00e67633" strokeDasharray="4" />
        <line x1="0" y1={h - ((0 - min) / range) * h} x2={w} y2={h - ((0 - min) / range) * h} stroke="#ffffff11" strokeDasharray="2" />
        <polyline points={points} fill="none" stroke={latestColor} strokeWidth="2" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

// ── Main App ────────────────────────────────

export default function MiningRotationDashboard() {
  const [state, setState] = useState(DEMO_STATE);
  const [history, setHistory] = useState(DEMO_HISTORY);
  const [loading, setLoading] = useState(false);
  const [lastFetch, setLastFetch] = useState(null);
  const [liveMode, setLiveMode] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [stateRes, histRes] = await Promise.all([
        fetch(`${API_BASE}/api/state`),
        fetch(`${API_BASE}/api/history`)
      ]);
      if (stateRes.ok) {
        const data = await stateRes.json();
        if (!data.error) {
          setState(data);
          setLiveMode(true);
        }
      }
      if (histRes.ok) {
        const hist = await histRes.json();
        if (Array.isArray(hist) && hist.length > 0) setHistory(hist);
      }
      setLastFetch(new Date());
    } catch (e) {
      if (!liveMode) setError(null); // Silently stay in demo
    } finally {
      setLoading(false);
    }
  }, [liveMode]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const triggerRefresh = async () => {
    try {
      await fetch(`${API_BASE}/api/refresh?fred=true`, { method: "POST" });
      setTimeout(fetchData, 5000);
    } catch {}
  };

  const s = state;
  const statusCfg = STATUS_CONFIG[s.composite_status] || STATUS_CONFIG.WATCH;

  return (
    <div style={{
      minHeight: "100vh", background: "#080b12", color: "#e1e4e8",
      fontFamily: "'Instrument Sans', 'SF Pro Display', -apple-system, sans-serif"
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700;800&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ background: "#0d1117", borderBottom: `2px solid ${statusCfg.color}30`, padding: "12px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ fontSize: "16px", fontWeight: 700, letterSpacing: "1px", fontFamily: "'Space Grotesk', sans-serif" }}>
            <span style={{ color: statusCfg.color }}>◆</span> MINING ROTATION MONITOR
          </div>
          <div style={{
            fontSize: "10px", padding: "3px 8px", borderRadius: "4px",
            background: liveMode ? "rgba(0,230,118,0.1)" : "rgba(255,214,0,0.1)",
            color: liveMode ? "#00e676" : "#ffd600",
            fontFamily: "monospace", fontWeight: 600
          }}>
            {liveMode ? "● LIVE" : "◌ DEMO"}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span style={{ fontSize: "11px", color: "#555", fontFamily: "monospace" }}>
            {s.timestamp ? new Date(s.timestamp).toLocaleString() : ""}
          </span>
          <button
            onClick={triggerRefresh}
            disabled={loading}
            style={{
              background: "rgba(255,255,255,0.06)", border: "1px solid #1a1f2e",
              color: "#8a8f98", padding: "6px 14px", borderRadius: "6px",
              cursor: loading ? "wait" : "pointer", fontSize: "11px",
              fontFamily: "monospace"
            }}
          >
            {loading ? "⟳ Updating..." : "⟳ Refresh"}
          </button>
        </div>
      </div>

      {/* Price Ticker Strip */}
      <div style={{ display: "flex", overflowX: "auto", background: "#0a0e16", borderBottom: "1px solid #1a1f2e" }}>
        <PriceTicker label="Gold" price={s.prices?.gold} change={s.changes?.gold?.["1d"]} />
        <PriceTicker label="Silver" price={s.prices?.silver} change={s.changes?.silver?.["1d"]} />
        <PriceTicker label="Copper" price={s.prices?.copper} change={s.changes?.copper?.["1d"]} />
        <PriceTicker label="GDX" price={s.prices?.gdx} change={s.changes?.gdx?.["1d"]} />
        <PriceTicker label="GDXJ" price={s.prices?.gdxj} change={s.changes?.gdxj?.["1d"]} />
        <PriceTicker label="Brent Oil" price={s.prices?.oil} change={s.changes?.oil?.["1d"]} />
        <PriceTicker label="DXY" price={s.prices?.dxy} change={s.changes?.dxy?.["1d"]} />
        <PriceTicker label="S&P 500" price={s.prices?.spy} change={s.changes?.spy?.["1d"]} />
      </div>

      <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "24px" }}>
        {/* Score Gauge */}
        <div style={{ background: "#0d1117", borderRadius: "12px", border: "1px solid #1a1f2e", padding: "8px 24px", marginBottom: "24px" }}>
          <ScoreGauge score={s.composite_score} status={s.composite_status} trend={s.score_trend} />
        </div>

        {/* Alert Banner */}
        {s.alert_message && (
          <div style={{
            padding: "12px 20px", borderRadius: "8px", marginBottom: "24px",
            background: statusCfg.bg, border: `1px solid ${statusCfg.color}30`,
            fontSize: "13px", color: statusCfg.color, fontWeight: 500
          }}>
            {s.alert_message}
          </div>
        )}

        {/* Main Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 340px", gap: "24px" }}>

          {/* Column 1: Signals */}
          <div>
            <div style={{ fontSize: "11px", color: "#555", textTransform: "uppercase", letterSpacing: "2px", marginBottom: "12px", fontFamily: "monospace" }}>
              Signal Dashboard ({s.signals?.length || 0} indicators)
            </div>
            {s.signals?.sort((a, b) => Math.abs(b.score * b.weight) - Math.abs(a.score * a.weight)).map((sig, i) => (
              <SignalCard key={i} signal={sig} />
            ))}
          </div>

          {/* Column 2: Rotation Targets + History */}
          <div>
            <div style={{ fontSize: "11px", color: "#555", textTransform: "uppercase", letterSpacing: "2px", marginBottom: "12px", fontFamily: "monospace" }}>
              Rotation Targets
            </div>
            {s.rotation_targets?.map((t, i) => (
              <RotationCard key={i} target={t} rank={i} />
            ))}

            <div style={{ marginTop: "24px" }}>
              <MiniChart history={history} />
            </div>

            {/* Performance Grid */}
            <div style={{ marginTop: "16px", background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e", padding: "16px" }}>
              <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontFamily: "monospace" }}>
                Period Returns
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: "11px", borderCollapse: "collapse", fontFamily: "monospace" }}>
                  <thead>
                    <tr style={{ color: "#555" }}>
                      <th style={{ textAlign: "left", padding: "4px 8px" }}></th>
                      <th style={{ textAlign: "right", padding: "4px 8px" }}>1D</th>
                      <th style={{ textAlign: "right", padding: "4px 8px" }}>1W</th>
                      <th style={{ textAlign: "right", padding: "4px 8px" }}>1M</th>
                      <th style={{ textAlign: "right", padding: "4px 8px" }}>3M</th>
                    </tr>
                  </thead>
                  <tbody>
                    {["gdx", "gdxj", "gold", "silver", "copper", "spy", "qqq", "oil", "dxy"].map(key => {
                      const ch = s.changes?.[key];
                      if (!ch) return null;
                      return (
                        <tr key={key} style={{ borderTop: "1px solid #1a1f2e" }}>
                          <td style={{ padding: "4px 8px", color: "#8a8f98", fontWeight: 600 }}>{key.toUpperCase()}</td>
                          {["1d", "1w", "1m", "3m"].map(p => (
                            <td key={p} style={{ textAlign: "right", padding: "4px 8px", color: (ch[p] || 0) >= 0 ? "#00e676" : "#ff1744" }}>
                              {fmtPct(ch[p])}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Column 3: Macro Sidebar */}
          <div>
            <div style={{ background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e", padding: "16px", marginBottom: "16px" }}>
              <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontFamily: "monospace" }}>
                Macro Indicators
              </div>
              <MacroRow label="10Y TIPS Yield (Real Rate)" value={s.macro?.tips_10y || s.macro?.real_rate_10y} format="pct" thresholds={{ bullishBelow: 0.5, warnAbove: 1.5, bearishAbove: 2.0 }} />
              <MacroRow label="10Y Treasury" value={s.macro?.treasury_10y} format="pct" />
              <MacroRow label="10Y Breakeven Inflation" value={s.macro?.breakeven_10y} format="pct" />
              <MacroRow label="Fed Funds Rate" value={s.macro?.fed_funds} format="pct" />
            </div>

            <div style={{ background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e", padding: "16px", marginBottom: "16px" }}>
              <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontFamily: "monospace" }}>
                Key Ratios
              </div>
              <MacroRow label="GDX/GLD Ratio" value={s.ratios?.gdx_gld} format="" />
              <MacroRow label="GDX/GLD 20d Slope" value={s.ratios?.gdx_gld_slope_20d} format="" />
              <MacroRow label="GDXJ/GDX Ratio" value={s.ratios?.gdxj_gdx} format="" />
              <MacroRow label="Gold/SPY Ratio" value={s.ratios?.gold_spy} format="" />
            </div>

            <div style={{ background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e", padding: "16px", marginBottom: "16px" }}>
              <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", fontFamily: "monospace" }}>
                AISC Margin Estimate
              </div>
              {(() => {
                const gold = s.prices?.gold || 0;
                const aisc = 1800;
                const margin = gold - aisc;
                const pct = gold > 0 ? (margin / gold) * 100 : 0;
                return (
                  <>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <span style={{ fontSize: "11px", color: "#8a8f98" }}>Gold Price</span>
                      <span style={{ fontSize: "13px", fontWeight: 600, fontFamily: "monospace" }}>{fmtPrice(gold)}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                      <span style={{ fontSize: "11px", color: "#8a8f98" }}>Est. AISC</span>
                      <span style={{ fontSize: "13px", fontWeight: 600, fontFamily: "monospace" }}>{fmtPrice(aisc)}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "8px", borderTop: "1px solid #1a1f2e" }}>
                      <span style={{ fontSize: "11px", color: "#8a8f98" }}>Margin/oz</span>
                      <span style={{ fontSize: "16px", fontWeight: 700, color: margin > 2500 ? "#00e676" : margin > 1500 ? "#ffd600" : "#ff1744", fontFamily: "'JetBrains Mono', monospace" }}>
                        {fmtPrice(margin)} ({fmt(pct, 0)}%)
                      </span>
                    </div>
                  </>
                );
              })()}
            </div>

            <div style={{ background: "#0d1117", borderRadius: "8px", border: "1px solid #1a1f2e", padding: "16px" }}>
              <div style={{ fontSize: "10px", color: "#555", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "12px", fontFamily: "monospace" }}>
                Rotation Trigger Checklist
              </div>
              {[
                { label: "Hormuz resolves / Oil <$75", check: (s.prices?.oil || 90) < 75 },
                { label: "Real rates >2.0%", check: (s.macro?.tips_10y || s.macro?.real_rate_10y || 0) > 2.0 },
                { label: "DXY >105", check: (s.prices?.dxy || 100) > 105 },
                { label: "GDX/GLD slope negative", check: (s.ratios?.gdx_gld_slope_20d || 0) < -0.001 },
                { label: "AISC rising + gold stalling", check: (s.prices?.gold || 5000) < 3500 },
                { label: "GDX below 200-SMA", check: s.signals?.find(x => x.name.includes("200-Day"))?.status === "bearish" }
              ].map((item, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0", borderBottom: "1px solid #0a0e16", fontSize: "12px" }}>
                  <span style={{ fontSize: "14px" }}>{item.check ? "🔴" : "⚪"}</span>
                  <span style={{ color: item.check ? "#ff1744" : "#555" }}>{item.label}</span>
                </div>
              ))}
              <div style={{ marginTop: "12px", fontSize: "10px", color: "#444", fontStyle: "italic" }}>
                3+ red = strong rotation signal
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: "32px", padding: "16px 0", borderTop: "1px solid #1a1f2e", display: "flex", justifyContent: "space-between", fontSize: "10px", color: "#333", fontFamily: "monospace" }}>
          <span>Mining Rotation Monitor v1.0 — Not financial advice</span>
          <span>Data: Yahoo Finance, FRED | Updates every 15m during market hours</span>
        </div>
      </div>
    </div>
  );
}
