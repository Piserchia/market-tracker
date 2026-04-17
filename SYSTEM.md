# Market Tracker — System Documentation
## Everything a Future Claude Session (or Chris) Needs to Know
### Last Updated: April 16, 2026

---

## 1. WHAT THIS SYSTEM IS

A multi-dashboard market monitoring system built for Chris Piserchia's ~$115K investment portfolio. Three dashboards track different sectors, each with the same architecture: Python backend → Flask API → React frontend → Claude Code CLI workflows for AI-powered research.

**Goal**: Help Chris grow the portfolio toward $1M by providing data-driven signals for when to hold, buy, sell, or rotate capital between sectors. The system is *informational* — it surfaces signals and context so Chris can make informed decisions, not automated trading.

**Deployed on**: Mac Mini home server via Docker. Claude Code CLI is installed for AI research workflows.

---

## 2. THE THREE DASHBOARDS

### Mining Rotation Monitor (:8787)
**Purpose**: Track 10 signals that indicate when to rotate OUT of precious metals/mining positions ($10K allocation) and INTO other sectors.
**Status**: COMPLETE (backend + frontend)
**Key files**: `config.py`, `data_collector.py`, `signal_engine.py`, `server.py`, `alert_system.py`, `scheduler.py`, `dashboard/MiningRotationDashboard.jsx`
**Data sources**: Yahoo Finance (prices, technicals), FRED API (rates, CPI, TIPS)
**Unique features**: Twilio SMS + email alerts, APScheduler for auto-updates, comprehensive info tooltips on every indicator

### Stocks Dashboard (:8788) — formerly AI Sector
**Purpose**: Monitor ALL of Chris's equity holdings (AI/tech + non-tech) with per-stock signal cards, valuation scoring, sector filter tabs, and Claude-powered daily research.
**Status**: Backend COMPLETE, frontend COMPLETE with info tooltips
**Key files**: `ai_sector/portfolio.json`, `ai_sector/stock_profiles.json`, `ai_sector/signal_engine.py`, `ai_sector/server.py`, `ai_sector/workflows/`, `dashboard/StocksDashboard.jsx`
**Data sources**: Yahoo Finance (prices, fundamentals, technicals), FRED API
**Portfolio**: 29 holdings across trading account + Roth IRA (see portfolio.json)
**Profiles**: 14+ stocks profiled with custom sell triggers and thresholds
**Categories**: chip_designer, cloud_platform, ai_monetizer, server_infra, connectivity, speculative, financial, consumer, non_tech
**Note**: Directory is still named `ai_sector/` for backwards compat, but dashboard is named "Stocks". API routes are still `/api/ai/*`. Rename is purely UI-level.

### Crypto Dashboard (:8789)
**Purpose**: Monitor crypto holdings (currently $16.3K SOL) with on-chain indicators, market cycle signals, and Claude-powered research.
**Status**: Backend COMPLETE, frontend COMPLETE with info tooltips
**Key files**: `crypto/portfolio.json`, `crypto/crypto_profiles.json`, `crypto/signal_engine.py`, `crypto/server.py`, `crypto/workflows/`, `dashboard/CryptoDashboard.jsx`
**Data sources**: CoinGecko API, DeFiLlama API, Alternative.me (Fear & Greed), Yahoo Finance (DXY, yields)
**Portfolio**: SOL ($16.3K held), BTC/ETH/LINK/XRP/AVAX on watchlist

---

## 3. CHRIS'S PORTFOLIO CONTEXT

### Trading Account (~$73K)
**AI/Tech**: AAPL $5K, AMD $8.6K, AMZN $9.3K, BBAI $938, BIDU $2.5K, INTC $6.8K, META $2.7K, MSFT $2.5K, NVDA $4.16K, SMCI $994, NOW $2.5K, LPTH $373, CRM $1.8K
**Connectivity/Other Tech**: ASTS $3.9K, FLY $1.1K, NOK $1K, OPTX $1.1K
**Non-Tech**: COF $9K, CELH $1.5K, HNST $1K, MA $2K, NKE $1.3K, NXXT $815, SOFI $1.2K
**Mining**: ~$10K (tracked by mining dashboard)

### Roth IRA (~$42K) — Long-term holds
AMZN $15K, FSPTX $12.8K, VDE $6.1K, FDGFX $5.2K, VGT $3.2K

### Crypto (Exchange — direct holdings)
SOL: $16,300

### Key Investment Beliefs (from conversation)
- AMZN and META are long-term core holds
- Willing to rotate between sectors when conditions change
- New to crypto beyond BTC/ETH/SOL — wants to learn
- Prefers data-driven decisions over fear/greed
- Goal: grow $115K to $1M through active but informed trading
- Likes short, direct answers (pushed back on verbose responses)

---

## 4. ARCHITECTURE DECISIONS

### Why Three Separate Servers (Not One)
Each dashboard can be developed, deployed, and restarted independently. Different data sources with different rate limits. Different update frequencies (mining every 15 min, AI sector every 15 min, crypto could be more frequent). Keeps codebases clean.

### Why Claude Code CLI (Not Anthropic API)
Chris has Claude Code CLI installed on his Mac Mini. He prefers it over managing API keys/billing. CLI uses his existing Claude subscription. Workflows pipe prompts to `claude -p --output-format text` and parse JSON output.

### Why JSON Files (Not a Database)
Simplicity. Chris edits `portfolio.json` directly or through the API. No database setup, no migrations, no ORM. The data is small enough that JSON read/write is instant. Files are human-readable and version-controlled in git.

### Signal Architecture (Three Layers)
- **Layer 1**: Sector-wide health signals. Always computed. Tells you "is this sector working?"
- **Layer 2**: Per-asset universal signals. Auto-computed for any ticker/coin in portfolio. RSI, SMA, MACD, valuation metrics. No config needed.
- **Layer 3**: Per-asset custom signals. Requires a profile in stock_profiles.json / crypto_profiles.json. Custom thresholds, sell triggers, buy signals. Claude auto-generates these via the analyze workflow when a new asset is added.

### Portfolio Update Flow
1. User adds stock/coin via dashboard UI form
2. Frontend PUTs to API (e.g., `/api/ai/portfolio`)
3. Server saves to portfolio.json
4. Server checks if profile exists in profiles JSON
5. If NO profile → auto-launches Claude analysis workflow (analyze_stock.sh / analyze_coin.sh)
6. Workflow invokes `claude -p` with structured prompt
7. Claude returns JSON with full analysis + profile
8. Workflow writes profile to stock_profiles.json / crypto_profiles.json
9. Server triggers data refresh
10. Dashboard shows new asset with full signal card

---

## 5. WHAT'S INCOMPLETE / TODO

### High Priority
- [x] ~~React frontends for AI sector and crypto~~ — COMPLETE with info tooltips
- [x] ~~Dashboard UI portfolio management forms~~ — Add/edit forms live in both dashboards
- [x] ~~Suggestions panel~~ — Displaying Claude daily research on dashboards
- [x] ~~Unified landing page~~ — at localhost:8787 linking to all three
- [ ] **Info tooltips rollout complete** — Stocks + Crypto have (i) hover tooltips. Mining dashboard already had this. All three consistent.

### Medium Priority
- [ ] **AI sector: earnings calendar integration** — per-stock next earnings date, auto-refresh after earnings
- [ ] **Crypto: on-chain data** — MVRV Z-Score, NUPL, Puell Multiple, exchange reserves, funding rates. These are the most important crypto-specific indicators. Currently NOT in the signal engine because free API access to on-chain data is limited. Options:
  - CryptoQuant (has free tier with some endpoints)
  - Glassnode (paid, $29/mo for basic)
  - Scrape from Bitcoin Magazine Pro / LookIntoBitcoin public charts
  - Build a manual input system where Chris can enter MVRV readings from free chart sites
- [ ] **Crypto: ETF flow tracking** — BTC/ETH ETF daily net flows. SoSoValue has an API but needs evaluation. Could also be manual input.
- [ ] **Crypto: funding rates** — CoinGlass API (free tier available). Would add a Layer 1 signal for leverage/sentiment.
- [ ] **Mining dashboard: central bank buying data** — World Gold Council quarterly. Currently not tracked.
- [ ] **Alert system for AI sector and crypto** — Mining dashboard has Twilio/email alerts. The other two don't yet. Should be straightforward to port.
- [ ] **Historical signal tracking** — currently saves score history. Should also save signal state changes (e.g., "GDX RSI crossed above 75 on date X") for backtesting.

### Low Priority / Nice-to-Have
- [ ] **Remote access** — Cloudflare Tunnel or Tailscale for accessing dashboards from phone/work. Chris said "both — local for now, remote later."
- [ ] **Mobile-responsive dashboards** — Current React dashboards are desktop-optimized. Would need responsive CSS for phone access.
- [ ] **Portfolio performance tracking** — Track actual P&L over time. Requires storing entry prices and dates, which portfolio.json doesn't currently capture.
- [ ] **Cross-dashboard signals** — e.g., mining gold strength → impacts crypto (gold correlation), or oil spike → impacts both AI stocks and crypto. Currently each dashboard is independent.
- [ ] **Non-tech stock dashboard** — Chris has COF $9K, CELH, NKE, MA, SOFI etc. These are in the AI sector portfolio.json but don't have proper signal profiles. Could be a fourth dashboard or integrated into the AI sector one with "non-tech" category filtering.

---

## 6. DATA SOURCE DETAILS

### Yahoo Finance (yfinance library)
- **Used by**: Mining, AI Sector
- **Rate limits**: ~2000 requests/hour (unofficial, no API key needed)
- **Data**: OHLCV daily prices, fundamental data (P/E, PEG, FCF, margins, analyst targets, short interest)
- **Gotcha**: `yf.download()` with many tickers can timeout. Fallback to individual `Ticker.history()` calls.
- **Gotcha**: Some tickers (mutual funds like FDGFX, FSPTX) don't have full data in yfinance.

### FRED API
- **Used by**: Mining, AI Sector (macro indicators)
- **Rate limits**: 120 requests/minute with API key
- **Series**: DFII10 (10Y TIPS), DGS10 (10Y Treasury), T10YIE (breakeven), FEDFUNDS
- **Setup**: Free API key at https://fred.stlouisfed.org/docs/api/api_key.html
- **Required**: Set `FRED_API_KEY` environment variable

### CoinGecko API
- **Used by**: Crypto
- **Rate limits**: 10-30 calls/minute (free tier, no key needed)
- **Data**: Prices, market data, historical charts, global market stats
- **Gotcha**: Rate limiting is aggressive. Engine uses `time.sleep(1-1.5)` between calls.
- **Gotcha**: `market_chart` endpoint returns daily data for period >90 days. Use `interval=daily`.

### DeFiLlama API
- **Used by**: Crypto (stablecoin supply, TVL)
- **Rate limits**: Generous, no key needed
- **Endpoints**: `/stablecoins` (supply), `/v2/chains` (TVL by chain)

### Alternative.me
- **Used by**: Crypto (Fear & Greed Index)
- **Rate limits**: Very generous
- **Endpoint**: `https://api.alternative.me/fng/?limit=30`

### Twilio
- **Used by**: Mining (SMS alerts)
- **Setup**: Requires TWILIO_SID, TWILIO_AUTH, TWILIO_FROM, ALERT_PHONE env vars
- **Status**: Configured in mining alert_system.py. Not yet in AI sector or crypto.

---

## 7. SELL TRIGGER REFERENCE

### Mining Dashboard — Rotation Triggers
1. Hormuz resolves / Oil < $75
2. Real rates > 2.0% (10Y TIPS)
3. DXY > 105
4. GDX/GLD 20-day slope turns negative
5. Gold drops below $3,500 (AISC margin compression)
6. GDX closes below 200-day SMA

**Rule: 3+ triggers firing simultaneously = high-confidence rotation signal**

### AI Sector — Per-Stock (see stock_profiles.json for full list)
- NVDA: Gross margin < 70% for 2 qtrs
- AMD: Data center revenue growth < 20% YoY
- INTC: Forward P/E > 80x without revenue acceleration
- AMZN: AWS growth < 15% for 2 qtrs
- META: DAU decline for 2 consecutive quarters
- SMCI: Any new governance scandal (IMMEDIATE exit signal)

### Crypto — Per-Coin (see crypto_profiles.json for full list)
- BTC: MVRV Z-Score > 7 (cycle top indicator)
- SOL: Major network outage or DeFi exploit > $100M
- ETH: ETH/BTC ratio breaks below 0.02

---

## 8. RESEARCH DOCUMENTS

Two comprehensive research documents are in the repo root:
- `AI_SECTOR_RESEARCH.md` — Full analysis of all AI/tech holdings, sell signal framework, undervaluation indicators, adjacent play recommendations
- `CRYPTO_RESEARCH.md` — Market state, on-chain indicator framework, BTC/ETH/SOL comparison, overpriced/underpriced framework, data source catalog

These contain the analytical reasoning behind every signal and threshold in the system. If a future Claude session needs to understand *why* a threshold is set at a specific value, these documents explain it.

---

## 9. ENVIRONMENT SETUP

### Required Environment Variables
```bash
# FRED API (required for mining + AI sector macro data)
export FRED_API_KEY="..."

# Twilio SMS (optional, mining alerts only)
export TWILIO_SID="..."
export TWILIO_AUTH="..."
export TWILIO_FROM="+1..."
export ALERT_PHONE="+1..."

# Email alerts (optional)
export SMTP_USER="..."
export SMTP_PASS="..."
export ALERT_EMAIL="..."
```

### Python Dependencies
```bash
pip install yfinance pandas numpy requests flask flask-cors apscheduler twilio
```

### Running All Three Dashboards
```bash
# Terminal 1 (or Docker container 1)
cd market-tracker && python server.py                    # Mining :8787

# Terminal 2 (or Docker container 2)
cd market-tracker/ai_sector && python server.py          # AI Sector :8788

# Terminal 3 (or Docker container 3)
cd market-tracker/crypto && python server.py             # Crypto :8789
```

### Docker Scheduler Cron Entries
```
# Mining: price updates every 15 min during market hours (handled by scheduler.py)
# AI sector: daily Claude research at 5:30 PM ET
30 17 * * 1-5 /path/to/ai_sector/workflows/daily_research.sh
# Crypto: daily Claude research at 6:00 PM ET
0 18 * * * /path/to/crypto/workflows/daily_research.sh
```

---

## 10. GITHUB

**Repo**: https://github.com/Piserchia/market-tracker
**Branch**: main
**Auth**: Fine-grained personal access token (should be revoked after each session)

---

*This document should be the first thing any future Claude session reads. It contains all the context needed to continue development.*
