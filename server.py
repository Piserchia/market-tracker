"""
Dashboard Server
================
Flask API serving:
  - GET /api/state      → Current dashboard state JSON
  - GET /api/history    → Signal score history
  - POST /api/refresh   → Force data refresh
  - GET /               → Dashboard UI (static)
"""

import json
import logging
import os
import threading
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import DATA_DIR, HOST, PORT, STATE_FILE, HISTORY_FILE
from data_collector import DataCollector
from signal_engine import SignalEngine
from alert_system import AlertSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

# Global state
collector = DataCollector()
alert_system = AlertSystem()
current_state = {}
state_lock = threading.Lock()


def load_history() -> list:
    """Load score history from disk."""
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_history(history: list):
    """Save score history to disk."""
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-500:], f)  # Keep last 500 entries
    except Exception as e:
        logger.error(f"Failed to save history: {e}")


def run_update(include_fred: bool = False):
    """Run a full data update cycle."""
    global current_state
    logger.info("Running data update...")

    try:
        # Collect data
        snapshot = collector.refresh(include_fred=include_fred)

        # Load previous score for trend calc
        previous_score = None
        with state_lock:
            if current_state:
                previous_score = current_state.get("composite_score")

        # Compute signals
        engine = SignalEngine(snapshot)
        state = engine.build_dashboard_state(previous_score=previous_score)

        # Check alerts
        alerts = alert_system.check_and_alert(state)
        state["alerts_sent"] = alerts

        with state_lock:
            current_state = state

        # Save state
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)

        # Append to history
        history = load_history()
        history.append({
            "timestamp": state["timestamp"],
            "composite_score": state["composite_score"],
            "composite_status": state["composite_status"],
            "alert_level": state["alert_level"],
            "prices": {
                k: state["prices"].get(k)
                for k in ["gold", "silver", "copper", "oil", "gdx", "gdxj", "dxy"]
            },
        })
        save_history(history)

        logger.info(
            f"Update complete. Score: {state['composite_score']:+.2f} "
            f"Status: {state['composite_status']} "
            f"Level: {state['alert_level']}"
        )

    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)


# ── API Routes ────────────────────────────────

@app.route("/health")
def health():
    """Healthcheck endpoint for the hosting layer."""
    return jsonify({"status": "ok", "service": "mining"})


@app.route("/api/state")
def get_state():
    """Return current dashboard state."""
    with state_lock:
        if current_state:
            return jsonify(current_state)
    # Try loading from disk
    try:
        with open(STATE_FILE, "r") as f:
            return jsonify(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"error": "No data yet. Trigger a refresh."}), 503


@app.route("/api/history")
def get_history():
    """Return score history."""
    history = load_history()
    return jsonify(history)


@app.route("/api/refresh", methods=["POST"])
def trigger_refresh():
    """Force a data refresh."""
    include_fred = request.args.get("fred", "false").lower() == "true"
    thread = threading.Thread(target=run_update, args=(include_fred,))
    thread.start()
    return jsonify({"status": "refresh_started", "include_fred": include_fred})


@app.route("/api/force-alert", methods=["POST"])
def force_alert():
    """Send a test alert."""
    alert_system.force_alert("🧪 TEST ALERT: Mining Rotation Monitor is working.")
    return jsonify({"status": "alert_sent"})


@app.route("/")
def serve_dashboard():
    """Serve the dashboard HTML."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory(app.static_folder, path)


# ── Startup ───────────────────────────────────

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    # Initial data load
    logger.info("Initial data load...")
    run_update(include_fred=True)
    # Start server
    logger.info(f"Starting server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False)
