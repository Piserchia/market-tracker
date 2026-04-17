# Market Tracker

## Mission

Multi-sector investment portfolio monitoring system for a ~$115K personal
portfolio. Provides real-time market signals, rotation recommendations, and
Claude-powered research across three independent dashboards: mining/precious
metals, equities, and crypto.

## Platforms

- **Primary**: web (Flask + React, self-hosted)
- **Web serving**: native-web (the project IS a web app)
- **Web relationship**: native — no platform gap

## Web Serving

Three independent Flask servers, each with its own React frontend:

| Dashboard | Port | Subdomain path | API prefix |
|-----------|------|----------------|------------|
| Mining rotation | 8787 | `/` (root) | `/api/state`, `/api/history`, `/api/refresh` |
| Stocks (AI sector) | 8788 | `/stocks/` | `/api/ai/*` |
| Crypto | 8789 | `/crypto/` | `/api/crypto/*` |

All three are served under `market-tracker.chrispiserchia.com` via Caddy
path-based routing. The landing page at the root links to all three dashboards.

Each server is independently supervised via launchd and independently
healthchecked at `/health`.

## Architecture

**Tech stack**: Python 3, Flask, React (pre-built static), yfinance, FRED API,
CoinGecko API, APScheduler.

**Signal engine pattern**: Each dashboard has a `signal_engine.py` that
evaluates 5-10 signals, produces a composite score, and maps to a status label
(HOLD / WATCH / PREPARE / ROTATE for mining; similar for stocks/crypto).

**Data flow**:
```
External APIs (yfinance, FRED, CoinGecko)
  → signal_engine.py (evaluate + score)
  → dashboard_state.json (persist to disk)
  → Flask /api/state (serve to frontend)
  → React dashboard (render)
```

**Key directories**:
- `server.py`, `config.py`, `signal_engine.py`, `data_collector.py` — Mining
- `ai_sector/` — Stocks dashboard (own server.py, signal_engine.py, portfolio.json)
- `crypto/` — Crypto dashboard (own server.py, signal_engine.py, portfolio.json)
- `dashboard/` — React component source (JSX)
- `static/` — Built HTML (mining landing page + mining dashboard)
- `data/` — Runtime JSON state files (gitignored)

## Status

- Mining dashboard: fully operational, 10 signals, SMS alerts via Twilio
- Stocks dashboard: operational, 29 holdings, Claude research integration
- Crypto dashboard: operational, on-chain indicators partial (TODO)
- Health endpoints: added for ai-server integration
- Missing: mobile-responsive CSS, earnings calendar, full on-chain data

## Environment

Required: `FRED_API_KEY` (free from fred.stlouisfed.org)
Optional: `TWILIO_SID`, `TWILIO_AUTH`, `TWILIO_FROM`, `ALERT_PHONE` (SMS alerts)
