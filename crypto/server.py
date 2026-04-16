"""
Crypto Dashboard Server — Port 8789
"""
import json, logging, os, subprocess, threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from signal_engine import run_crypto_update, load_json, save_json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(BASE_DIR, "crypto_portfolio.json")
PROFILES_FILE = os.path.join(BASE_DIR, "crypto_profiles.json")
STATE_FILE = os.path.join(BASE_DIR, "data", "crypto_dashboard_state.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "crypto_signal_history.json")
SUGGESTIONS_FILE = os.path.join(BASE_DIR, "data", "crypto_suggestions.json")
ANALYZE_SCRIPT = os.path.join(BASE_DIR, "workflows", "analyze_coin.sh")
RESEARCH_SCRIPT = os.path.join(BASE_DIR, "workflows", "daily_crypto_research.sh")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
app = Flask(__name__)
CORS(app)
current_state = {}
state_lock = threading.Lock()

def do_refresh():
    global current_state
    try:
        state = run_crypto_update()
        with state_lock:
            current_state = state
        logger.info(f"Crypto refresh done. Market: {state['market_health']['status']['label']}")
    except Exception as e:
        logger.error(f"Crypto refresh failed: {e}", exc_info=True)

@app.route("/api/crypto/state")
def get_state():
    with state_lock:
        if current_state: return jsonify(current_state)
    try: return jsonify(load_json(STATE_FILE))
    except: return jsonify({"error": "No data. POST /api/crypto/refresh"}), 503

@app.route("/api/crypto/history")
def get_history():
    d = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
    return jsonify(d if isinstance(d, list) else [])

@app.route("/api/crypto/refresh", methods=["POST"])
def trigger_refresh():
    threading.Thread(target=do_refresh, daemon=True).start()
    return jsonify({"status": "refresh_started"})

@app.route("/api/crypto/portfolio")
def get_portfolio():
    return jsonify(load_json(PORTFOLIO_FILE))

@app.route("/api/crypto/portfolio", methods=["PUT"])
def update_portfolio():
    data = request.get_json()
    if not data: return jsonify({"error": "No JSON"}), 400
    portfolio = load_json(PORTFOLIO_FILE)

    if "symbol" in data:
        sym = data["symbol"].upper()
        holdings = portfolio.get("holdings", [])
        found = False
        for h in holdings:
            if h["symbol"] == sym:
                h["dollars"] = data.get("dollars", h.get("dollars", 0))
                h["amount"] = data.get("amount", h.get("amount", 0))
                if "exchange" in data: h["exchange"] = data["exchange"]
                if "notes" in data: h["notes"] = data["notes"]
                found = True; break
        if not found:
            holdings.append({"symbol": sym, "name": data.get("name", sym),
                             "dollars": data.get("dollars", 0), "amount": data.get("amount", 0),
                             "exchange": data.get("exchange", "coinbase"), "notes": data.get("notes", "")})
        # Remove from watchlist if it was there
        portfolio["watchlist"] = [w for w in portfolio.get("watchlist", []) if w["symbol"] != sym]
        portfolio["holdings"] = holdings
        portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, portfolio)

        # Trigger analysis if no profile exists
        profiles = load_json(PROFILES_FILE)
        if sym not in profiles.get("profiles", {}) and os.path.exists(ANALYZE_SCRIPT):
            def _analyze():
                try:
                    subprocess.run(["bash", ANALYZE_SCRIPT, sym], capture_output=True, timeout=300,
                                   cwd=os.path.join(BASE_DIR, "workflows"))
                    do_refresh()
                except Exception as e:
                    logger.error(f"Coin analysis failed: {e}")
            threading.Thread(target=_analyze, daemon=True).start()
            return jsonify({"status": "added", "symbol": sym, "analysis_triggered": True})

        threading.Thread(target=do_refresh, daemon=True).start()
        return jsonify({"status": "updated", "symbol": sym})
    return jsonify({"error": "Provide 'symbol'"}), 400

@app.route("/api/crypto/portfolio/remove", methods=["POST"])
def remove_holding():
    data = request.get_json()
    sym = data.get("symbol", "").upper()
    portfolio = load_json(PORTFOLIO_FILE)
    portfolio["holdings"] = [h for h in portfolio.get("holdings", []) if h["symbol"] != sym]
    portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(PORTFOLIO_FILE, portfolio)
    return jsonify({"status": "removed", "symbol": sym})

@app.route("/api/crypto/suggestions")
def get_suggestions():
    if os.path.exists(SUGGESTIONS_FILE): return jsonify(load_json(SUGGESTIONS_FILE))
    return jsonify({"message": "No suggestions yet. Run daily_crypto_research.sh."})

@app.route("/api/crypto/profiles")
def get_profiles():
    return jsonify(load_json(PROFILES_FILE))

@app.route("/api/crypto/analyze/<symbol>", methods=["POST"])
def trigger_analysis(symbol):
    symbol = symbol.upper()
    if os.path.exists(ANALYZE_SCRIPT):
        def _run():
            subprocess.run(["bash", ANALYZE_SCRIPT, symbol], capture_output=True, timeout=300,
                           cwd=os.path.join(BASE_DIR, "workflows"))
        threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "analysis_started", "symbol": symbol})

if __name__ == "__main__":
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    logger.info("Starting Crypto Dashboard Server on :8789")
    do_refresh()
    app.run(host="0.0.0.0", port=8789, debug=False)
