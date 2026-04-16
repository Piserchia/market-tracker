"""
AI Sector Dashboard Server
============================
Flask API serving AI sector dashboard data.
Reads portfolio.json and stock_profiles.json dynamically on each refresh.

  GET  /api/ai/state        → Current dashboard state
  GET  /api/ai/history      → Score history
  POST /api/ai/refresh      → Force data refresh
  GET  /api/ai/portfolio     → Current portfolio.json
  PUT  /api/ai/portfolio     → Update portfolio.json (add/edit/remove holdings)
  GET  /api/ai/profiles      → Current stock_profiles.json
"""

import json
import logging
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from signal_engine import AISignalEngine, run_ai_update, STATE_FILE, HISTORY_FILE, PORTFOLIO_FILE, PROFILES_FILE, load_json, save_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../dashboard")
CORS(app)

current_state = {}
state_lock = threading.Lock()


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
    """Update portfolio holdings. Expects full portfolio JSON or partial update."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # Full replacement
    if "holdings" in data:
        data["last_updated"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, data)
        return jsonify({"status": "portfolio_updated", "holdings": len(data["holdings"])})

    # Single holding add/update
    if "ticker" in data:
        portfolio = load_json(PORTFOLIO_FILE)
        holdings = portfolio.get("holdings", [])

        # Find existing
        ticker = data["ticker"].upper()
        account = data.get("account", "trading")
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
        portfolio["last_updated"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, portfolio)
        return jsonify({"status": "holding_updated", "ticker": ticker})

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
    portfolio["last_updated"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    save_json(PORTFOLIO_FILE, portfolio)
    return jsonify({"status": "removed", "ticker": ticker, "account": account})


@app.route("/api/ai/profiles")
def get_profiles():
    return jsonify(load_json(PROFILES_FILE))


if __name__ == "__main__":
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    logger.info("Starting AI Sector Dashboard Server on :8788")
    logger.info("Initial data load...")
    do_refresh()
    app.run(host="0.0.0.0", port=8788, debug=False)
