# Mining Sector Rotation Monitor

A real-time dashboard and alert system that tracks 10 macro, technical, and fundamental indicators to signal when to rotate out of precious metals/mining positions — and what to rotate into.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Mac Mini Server                     │
│                                                        │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │ Scheduler    │───▶│ Data         │───▶│ Signal   │ │
│  │ (APScheduler)│    │ Collector    │    │ Engine   │ │
│  │              │    │              │    │          │ │
│  │ • 15m prices │    │ • yfinance   │    │ • 10     │ │
│  │ • 2h full    │    │ • FRED API   │    │   signals│ │
│  │ • EOD summary│    │ • technicals │    │ • scoring│ │
│  └──────────────┘    └──────────────┘    └────┬─────┘ │
│                                                │       │
│                    ┌──────────────┐    ┌───────▼─────┐│
│                    │ Alert System │◀───│ Flask API   ││
│                    │              │    │ Server      ││
│                    │ • Twilio SMS │    │             ││
│                    │ • Email      │    │ :8787       ││
│                    └──────────────┘    └───────┬─────┘│
│                                                │       │
└────────────────────────────────────────────────┼───────┘
                                                 │
                                    ┌────────────▼──────┐
                                    │ React Dashboard   │
                                    │ (Browser)         │
                                    └───────────────────┘
```

## Signals Tracked

| # | Signal | Category | What It Measures | Bearish For Metals When |
|---|--------|----------|------------------|------------------------|
| 1 | Oil / Geopolitical Risk | Macro | Brent crude price | Oil drops below $70 (calm markets) |
| 2 | Real Interest Rate | Macro | 10Y TIPS yield | Real rate exceeds 2.0% |
| 3 | US Dollar Index (DXY) | Macro | Dollar strength | DXY rises above 105 |
| 4 | GDX/GLD Ratio Trend | Technical | Miner leverage | 20-day slope turns negative |
| 5 | AISC Margin Proxy | Fundamental | Gold price vs mining costs | Gold drops below $3,500 |
| 6 | GDX RSI | Technical | Momentum | RSI above 85 (exhaustion) |
| 7 | GDX vs 200-SMA | Technical | Trend health | Price drops below 200-SMA |
| 8 | Gold 50/200 SMA | Technical | Gold trend | Death cross forms |
| 9 | Gold/Silver Ratio | Fundamental | Relative value | Ratio drops below 60 |
| 10 | Sector Flow | Technical | GDX vs SPY relative | GDX underperforms SPY by >10% |

## Composite Score

Each signal scores **-1 to +1**, weighted by importance. The composite sum determines the status:

- **≥ +2** → `HOLD` (green) — Macro supports mining position
- **-1 to +1** → `WATCH` (yellow) — Mixed signals, monitor closely
- **≤ -1** → `PREPARE` (orange) — Tighten stops, identify rotation targets
- **≤ -3** → `ROTATE` (red) — Exit mining, move to highest-scoring sector

## Rotation Targets

When signals deteriorate, the system scores potential rotation sectors based on the current macro regime:

| Sector | Favored When |
|--------|-------------|
| AI / Tech Infrastructure | Oil falling, rates cutting, DXY falling |
| Rate-Sensitive Growth | Fed cutting, real rates falling |
| Consumer Discretionary | Oil falling, real wages improving |
| Energy | Oil rising, inflation sticky |
| Broad Market (SPY) | Volatility falling, growth stable |

## Setup (Mac Mini)

### 1. Clone & Setup
```bash
# Copy project to your Mac Mini
git clone <your-repo> ~/mining-rotation-monitor
cd ~/mining-rotation-monitor
chmod +x setup.sh
./setup.sh
```

### 2. Configure API Keys
```bash
nano .env

# Required: FRED API key (free)
# https://fred.stlouisfed.org/docs/api/api_key.html
FRED_API_KEY="your-key-here"

# Optional: Twilio SMS alerts
TWILIO_SID="..."
TWILIO_AUTH="..."
TWILIO_FROM="+1..."
ALERT_PHONE="+1..."

# Optional: Email alerts
SMTP_USER="you@gmail.com"
SMTP_PASS="app-password"
ALERT_EMAIL="you@gmail.com"
```

### 3. Run Manually
```bash
# Terminal 1: API server + dashboard
./start.sh
# → Dashboard at http://localhost:8787

# Terminal 2: Scheduler (optional, for auto-updates + alerts)
./start-scheduler.sh
```

### 4. Auto-Start on Boot
```bash
# Register as macOS services
./register-services.sh

# Check status
launchctl list | grep mining

# Stop services
./unregister-services.sh
```

## Dashboard

The React dashboard connects to `http://localhost:8787/api/state` and displays:
- **Price ticker strip** — Gold, Silver, Copper, GDX, GDXJ, Oil, DXY, SPY
- **Composite score gauge** — Visual meter from ROTATE to HOLD
- **10 individual signal cards** — Color-coded with details
- **Rotation target rankings** — Scored by current regime
- **Score history chart** — 30-day trend
- **Period returns table** — 1D/1W/1M/3M across all tickers
- **Macro indicator sidebar** — TIPS yield, Treasury, breakeven, Fed funds
- **Rotation trigger checklist** — 6 binary checks, 3+ red = rotate

The dashboard runs in demo mode with sample data when the API is unreachable, and switches to live mode automatically when connected.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state` | GET | Current dashboard state (all signals, prices, scores) |
| `/api/history` | GET | Score history (last 500 data points) |
| `/api/refresh` | POST | Force data refresh (`?fred=true` includes FRED) |
| `/api/force-alert` | POST | Send test alert |

## File Structure

```
mining-rotation-monitor/
├── config.py           # Thresholds, tickers, API keys, rotation sectors
├── data_collector.py   # Yahoo Finance + FRED data fetching
├── signal_engine.py    # 10-signal evaluation + composite scoring
├── alert_system.py     # Twilio SMS + email alerts
├── server.py           # Flask API server
├── scheduler.py        # APScheduler for auto-updates
├── requirements.txt    # Python dependencies
├── setup.sh            # Mac Mini one-time setup
├── start.sh            # Manual start script
├── start-scheduler.sh  # Scheduler start script
├── register-services.sh   # launchd auto-start
├── unregister-services.sh # launchd cleanup
├── .env                # API keys (created by setup.sh)
├── static/             # Dashboard HTML (serve from Flask)
└── data/               # Runtime data (auto-created)
    ├── dashboard_state.json
    ├── signal_history.json
    └── alert_log.json
```

## Tuning

Edit `config.py` to adjust:
- Signal thresholds (oil levels, DXY levels, RSI bands, etc.)
- Update frequency
- Rotation sector definitions
- Alert sensitivity

The AISC estimate ($1,800/oz) should be updated quarterly based on actual earnings reports from the top miners.
