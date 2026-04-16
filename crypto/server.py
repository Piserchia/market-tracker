"""
Crypto Dashboard Server — Flask API on :8789
Same architecture as AI sector: portfolio CRUD + Claude workflow triggers
"""
import json, logging, os, subprocess, threading
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from signal_engine import run_crypto_update, STATE_FILE, HISTORY_FILE, PORTFOLIO_FILE, PROFILES_FILE, SUGGESTIONS_FILE, load_json, save_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYZE_SCRIPT = os.path.join(BASE_DIR, "workflows", "analyze_coin.sh")
RESEARCH_SCRIPT = os.path.join(BASE_DIR, "workflows", "daily_research.sh")

app = Flask(__name__)
CORS(app)
current_state = {}; state_lock = threading.Lock(); active_analyses = {}

def do_refresh():
    global current_state
    try:
        state = run_crypto_update()
        with state_lock: current_state = state
        logger.info(f"Crypto refresh: {state['market_health']['status']['label']}, {len(state['coin_cards'])} coins")
    except Exception as e: logger.error(f"Refresh failed: {e}", exc_info=True)

@app.route("/api/crypto/state")
def get_state():
    with state_lock:
        if current_state: return jsonify(current_state)
    try: return jsonify(load_json(STATE_FILE))
    except: return jsonify({"error":"No data. POST /api/crypto/refresh"}), 503

@app.route("/api/crypto/history")
def get_history():
    d = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
    return jsonify(d if isinstance(d,list) else [])

@app.route("/api/crypto/refresh", methods=["POST"])
def trigger_refresh():
    threading.Thread(target=do_refresh).start()
    return jsonify({"status":"refresh_started"})

@app.route("/api/crypto/portfolio")
def get_portfolio(): return jsonify(load_json(PORTFOLIO_FILE))

@app.route("/api/crypto/portfolio", methods=["PUT"])
def update_portfolio():
    data = request.get_json()
    if not data: return jsonify({"error":"No JSON"}), 400

    if "holdings" in data:
        data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, data)
        return jsonify({"status":"updated","count":len(data["holdings"])})

    if "coin_id" in data:
        portfolio = load_json(PORTFOLIO_FILE)
        holdings = portfolio.get("holdings",[])
        coin_id = data["coin_id"].lower()
        found = False
        for h in holdings:
            if h.get("coin_id") == coin_id:
                h["dollars"] = data.get("dollars", h.get("dollars",0))
                if "symbol" in data: h["symbol"] = data["symbol"].upper()
                if "notes" in data: h["notes"] = data["notes"]
                if "quantity" in data: h["quantity"] = data["quantity"]
                found = True; break
        if not found:
            holdings.append({"coin_id":coin_id,"symbol":data.get("symbol","").upper(),
                "dollars":data.get("dollars",0),"quantity":data.get("quantity"),
                "notes":data.get("notes","")})
        portfolio["holdings"] = holdings
        portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        save_json(PORTFOLIO_FILE, portfolio)

        # Trigger analysis if no profile exists
        profiles = load_json(PROFILES_FILE)
        has_profile = coin_id in profiles.get("profiles",{})
        if not has_profile and data.get("analyze", True):
            _launch_analysis(coin_id, data.get("symbol",""))
            return jsonify({"status":"added","coin_id":coin_id,"analysis_triggered":True})
        threading.Thread(target=do_refresh).start()
        return jsonify({"status":"updated","coin_id":coin_id,"analysis_triggered":False})

    return jsonify({"error":"Provide 'holdings' or 'coin_id'"}), 400

@app.route("/api/crypto/portfolio/remove", methods=["POST"])
def remove_holding():
    data = request.get_json()
    coin_id = data.get("coin_id","").lower()
    portfolio = load_json(PORTFOLIO_FILE)
    portfolio["holdings"] = [h for h in portfolio.get("holdings",[]) if h.get("coin_id")!=coin_id]
    portfolio["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(PORTFOLIO_FILE, portfolio)
    return jsonify({"status":"removed","coin_id":coin_id})

@app.route("/api/crypto/profiles")
def get_profiles(): return jsonify(load_json(PROFILES_FILE))

@app.route("/api/crypto/suggestions")
def get_suggestions():
    if os.path.exists(SUGGESTIONS_FILE): return jsonify(load_json(SUGGESTIONS_FILE))
    return jsonify({"message":"No suggestions yet. Run daily research.","new_suggestions":[],"warnings":[]})

# ── Workflow Triggers ────────────────────────────

def _launch_analysis(coin_id, symbol=""):
    if coin_id in active_analyses: return
    def _run():
        try:
            active_analyses[coin_id] = "running"
            result = subprocess.run(["bash", ANALYZE_SCRIPT, coin_id, symbol],
                capture_output=True, text=True, timeout=300, cwd=os.path.join(BASE_DIR,"workflows"))
            active_analyses[coin_id] = "complete" if result.returncode==0 else f"error"
            if result.returncode==0: do_refresh()
        except Exception as e: active_analyses[coin_id] = f"error: {e}"
    threading.Thread(target=_run, daemon=True).start()

@app.route("/api/crypto/analyze/<coin_id>", methods=["POST"])
def trigger_analysis(coin_id):
    _launch_analysis(coin_id.lower(), request.args.get("symbol",""))
    return jsonify({"status":"started","coin_id":coin_id})

@app.route("/api/crypto/analyze/<coin_id>/status")
def analysis_status(coin_id):
    return jsonify({"coin_id":coin_id,"status":active_analyses.get(coin_id.lower(),"not_started")})

@app.route("/api/crypto/analysis/<coin_id>")
def get_analysis(coin_id):
    f = os.path.join(BASE_DIR,"data",f"analysis_{coin_id.lower()}.json")
    if os.path.exists(f): return jsonify(load_json(f))
    return jsonify({"error":f"No analysis for {coin_id}"}), 404

@app.route("/api/crypto/research", methods=["POST"])
def trigger_research():
    def _run():
        try:
            subprocess.run(["bash",RESEARCH_SCRIPT], capture_output=True, text=True, timeout=600,
                cwd=os.path.join(BASE_DIR,"workflows"))
        except Exception as e: logger.error(f"Research failed: {e}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status":"research_started"})

if __name__=="__main__":
    os.makedirs(os.path.join(BASE_DIR,"data"), exist_ok=True)
    logger.info("Starting Crypto Dashboard on :8789")
    do_refresh()
    app.run(host="0.0.0.0", port=8789, debug=False)
