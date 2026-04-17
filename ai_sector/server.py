"""
AI Sector Dashboard Server
============================
Flask API serving AI sector dashboard data.
Reads portfolio.json and stock_profiles.json dynamically on each refresh.

  GET  /api/ai/state         → Current dashboard state
  GET  /api/ai/history       → Score history
  POST /api/ai/refresh       → Force data refresh
  GET  /api/ai/portfolio      → Current portfolio.json
  PUT  /api/ai/portfolio      → Update portfolio (add/edit holdings)
  POST /api/ai/portfolio/remove → Remove a holding
  GET  /api/ai/profiles       → Current stock_profiles.json
  GET  /api/ai/suggestions    → Latest daily research suggestions
  POST /api/ai/analyze/<TICKER> → Trigger Claude analysis for a stock
  GET  /api/ai/analysis/<TICKER> → Get saved analysis for a stock
  POST /api/ai/research       → Trigger daily research workflow
"""

import json
import logging
import os
import subprocess
import threading
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from signal_engine import AISignalEngine, run_ai_update, STATE_FILE, HISTORY_FILE, PORTFOLIO_FILE, PROFILES_FILE, load_json, save_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUGGESTIONS_FILE = os.path.join(BASE_DIR, "data", "suggestions.json")
WORKFLOWS_DIR = os.path.join(BASE_DIR, "workflows")
ANALYZE_SCRIPT = os.path.join(WORKFLOWS_DIR, "analyze_stock.sh")
RESEARCH_SCRIPT = os.path.join(WORKFLOWS_DIR, "daily_research.sh")

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.route("/")
def serve_dashboard():
    return app.send_static_file("index.html")


@app.route("/health")
def health():
    """Healthcheck endpoint for the hosting layer."""
    return jsonify({"status": "ok", "service": "stocks"})


current_state = {}
state_lock = threading.Lock()
active_analyses = {}  # Track running analyses


def do_refresh():
    global current_state
    try:
        state = run_ai_update()
        with state_lock:
            current_state = state
        logger.info(f"AI sector refresh complete. Sector: {state['sector_health']['status']['label']}, "
                     f"Stocks: {len(state['stock_cards'])}")
    except Exception as e:
        logger.error(f"AI refresh failed: {e}", exc_info=True)


@app.route("/api/ai/state")
def get_state():
    with state_lock:
        if current_state:
            return jsonify(current_state)
    try:
        return jsonify(load_json(STATE_FILE))
    except:
        return jsonify({"error": "No data yet. POST /api/ai/refresh to start."}), 503


@app.route("/api/ai/history")
def get_history():
    data = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
    return jsonify(data if isinstance(data, list) else [])


@app.route("/api/ai/refresh", methods=["POST"])
def trigger_refresh():
    thread = threading.Thread(target=do_refresh)
    thread.start()
    return jsonify({"status": "refresh_started"})


@app.route("/api/ai/portfolio")
def get_portfolio():
    return jsonify(load_json(PORTFOLIO_FILE))


@app.route("/api/ai/portfolio", methods=["PUT"])
def update_portfolio():
    """Update portfolio holdings. Optionally triggers Claude analysis for new stocks."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # Full replacement
    if "holdings" in data:
        data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, data)
        return jsonify({"status": "portfolio_updated", "holdings": len(data["holdings"])})

    # Single holding add/update
    if "ticker" in data:
        portfolio = load_json(PORTFOLIO_FILE)
        holdings = portfolio.get("holdings", [])

        ticker = data["ticker"].upper()
        account = data.get("account", "trading")
        trigger_analysis = data.get("analyze", True)  # Default: analyze new stocks
        found = False
        for h in holdings:
            if h.get("ticker") == ticker and h.get("account") == account:
                h["dollars"] = data.get("dollars", h.get("dollars", 0))
                if "notes" in data:
                    h["notes"] = data["notes"]
                found = True
                break

        if not found:
            holdings.append({
                "ticker": ticker,
                "dollars": data.get("dollars", 0),
                "account": account,
                "notes": data.get("notes", "")
            })

        portfolio["holdings"] = holdings
        portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, portfolio)

        # Check if this ticker has a profile; if not, trigger Claude analysis
        profiles = load_json(PROFILES_FILE)
        has_profile = ticker in profiles.get("profiles", {})

        if not has_profile and trigger_analysis:
            _launch_analysis(ticker)
            return jsonify({
                "status": "holding_added",
                "ticker": ticker,
                "analysis_triggered": True,
                "message": f"{ticker} added to portfolio. Claude is analyzing it now — profile will be generated automatically."
            })

        # If stock exists but we're just updating dollars, trigger a data refresh
        thread = threading.Thread(target=do_refresh)
        thread.start()

        return jsonify({"status": "holding_updated", "ticker": ticker, "analysis_triggered": False})

    return jsonify({"error": "Provide 'holdings' array or single holding with 'ticker'"}), 400


@app.route("/api/ai/portfolio/remove", methods=["POST"])
def remove_holding():
    """Remove a holding by ticker + account."""
    data = request.get_json()
    ticker = data.get("ticker", "").upper()
    account = data.get("account", "trading")

    portfolio = load_json(PORTFOLIO_FILE)
    holdings = portfolio.get("holdings", [])
    portfolio["holdings"] = [h for h in holdings
                             if not (h.get("ticker") == ticker and h.get("account") == account)]
    portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(PORTFOLIO_FILE, portfolio)
    return jsonify({"status": "removed", "ticker": ticker, "account": account})


@app.route("/api/ai/profiles")
def get_profiles():
    return jsonify(load_json(PROFILES_FILE))


# ── Workflow Endpoints ────────────────────────────────

def _launch_analysis(ticker: str):
    """Launch the analyze_stock.sh workflow in background."""
    ticker = ticker.upper()
    if ticker in active_analyses:
        logger.info(f"Analysis already running for {ticker}")
        return

    def _run():
        try:
            active_analyses[ticker] = "running"
            logger.info(f"Starting Claude analysis for {ticker}...")
            result = subprocess.run(
                ["bash", ANALYZE_SCRIPT, ticker],
                capture_output=True, text=True, timeout=300,  # 5 min timeout
                cwd=WORKFLOWS_DIR,
            )
            if result.returncode == 0:
                logger.info(f"Analysis complete for {ticker}")
                active_analyses[ticker] = "complete"
                # Trigger a data refresh to pick up the new profile
                do_refresh()
            else:
                logger.error(f"Analysis failed for {ticker}: {result.stderr[:500]}")
                active_analyses[ticker] = f"error: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            logger.error(f"Analysis timed out for {ticker}")
            active_analyses[ticker] = "timeout"
        except Exception as e:
            logger.error(f"Analysis exception for {ticker}: {e}")
            active_analyses[ticker] = f"error: {str(e)}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


@app.route("/api/ai/analyze/<ticker>", methods=["POST"])
def trigger_analysis(ticker):
    """Trigger Claude Code CLI analysis for a specific stock."""
    ticker = ticker.upper()
    _launch_analysis(ticker)
    return jsonify({
        "status": "analysis_started",
        "ticker": ticker,
        "message": f"Claude is researching {ticker}. Check /api/ai/analysis/{ticker} for results."
    })


@app.route("/api/ai/analyze/<ticker>/status")
def analysis_status(ticker):
    """Check the status of a running analysis."""
    ticker = ticker.upper()
    status = active_analyses.get(ticker, "not_started")
    return jsonify({"ticker": ticker, "status": status})


@app.route("/api/ai/analysis/<ticker>")
def get_analysis(ticker):
    """Get the saved analysis for a stock."""
    ticker = ticker.upper()
    analysis_file = os.path.join(BASE_DIR, "data", f"analysis_{ticker}.json")
    if os.path.exists(analysis_file):
        return jsonify(load_json(analysis_file))
    return jsonify({"error": f"No analysis found for {ticker}"}), 404


@app.route("/api/ai/suggestions")
def get_suggestions():
    """Get the latest daily research suggestions."""
    if os.path.exists(SUGGESTIONS_FILE):
        data = load_json(SUGGESTIONS_FILE)
        return jsonify(data)
    return jsonify({
        "message": "No suggestions yet. Run daily_research.sh or POST /api/ai/research.",
        "new_suggestions": [],
        "increase_suggestions": [],
        "reduction_warnings": [],
    })


@app.route("/api/ai/research", methods=["POST"])
def trigger_research():
    """Trigger the daily research workflow."""
    def _run_research():
        try:
            logger.info("Starting daily research workflow...")
            result = subprocess.run(
                ["bash", RESEARCH_SCRIPT],
                capture_output=True, text=True, timeout=600,  # 10 min timeout
                cwd=WORKFLOWS_DIR,
            )
            if result.returncode == 0:
                logger.info("Daily research complete.")
            else:
                logger.error(f"Research failed: {result.stderr[:500]}")
        except Exception as e:
            logger.error(f"Research exception: {e}")

    thread = threading.Thread(target=_run_research, daemon=True)
    thread.start()
    return jsonify({"status": "research_started", "message": "Daily research running. Check /api/ai/suggestions when complete."})


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    logger.info("Starting AI Sector Dashboard Server on :8788")
    logger.info("Initial data load...")
    do_refresh()
    app.run(host="0.0.0.0", port=8788, debug=False)
