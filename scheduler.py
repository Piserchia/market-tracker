"""
Scheduler
=========
Runs the data update loop on a configurable schedule.
  - Every 15 min during market hours: price-only refresh
  - Every 2 hours: full refresh including FRED data
  - Daily at 6 PM ET: end-of-day summary alert
"""

import logging
import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import MARKET_CLOSE_HOUR, MARKET_OPEN_HOUR, UPDATE_INTERVAL_MINUTES
from server import run_update, alert_system, current_state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()


def market_hours_update():
    """Quick price update during market hours."""
    now = datetime.now()
    # Only run during US market hours (weekdays)
    if now.weekday() >= 5:  # Skip weekends
        return
    if not (MARKET_OPEN_HOUR <= now.hour < MARKET_CLOSE_HOUR):
        return

    logger.info("Market hours update (prices only)")
    run_update(include_fred=False)


def full_update():
    """Full refresh including FRED data."""
    logger.info("Full update (prices + FRED)")
    run_update(include_fred=True)


def end_of_day_summary():
    """Send end-of-day summary alert."""
    if not current_state:
        return

    score = current_state.get("composite_score", 0)
    status = current_state.get("composite_status", "UNKNOWN")
    level = current_state.get("alert_level", "unknown")

    # Build signal summary
    bullish = [s for s in current_state.get("signals", []) if s["status"] == "bullish"]
    bearish = [s for s in current_state.get("signals", []) if s["status"] == "bearish"]

    prices = current_state.get("prices", {})
    changes = current_state.get("changes", {})

    msg_parts = [
        f"📊 END OF DAY — Mining Rotation Monitor",
        f"Status: {status} | Score: {score:+.1f} | Level: {level.upper()}",
        "",
        f"Gold: ${prices.get('gold', 0):,.0f} ({changes.get('gold', {}).get('1d', 0):+.1f}% today)",
        f"Silver: ${prices.get('silver', 0):.2f} ({changes.get('silver', {}).get('1d', 0):+.1f}%)",
        f"Copper: ${prices.get('copper', 0):.2f} ({changes.get('copper', {}).get('1d', 0):+.1f}%)",
        f"GDX: ${prices.get('gdx', 0):.2f} ({changes.get('gdx', {}).get('1d', 0):+.1f}%)",
        f"DXY: {prices.get('dxy', 0):.1f} | Oil: ${prices.get('oil', 0):.1f}",
        "",
        f"Bullish signals ({len(bullish)}): {', '.join(s['name'] for s in bullish) or 'None'}",
        f"Bearish signals ({len(bearish)}): {', '.join(s['name'] for s in bearish) or 'None'}",
    ]

    # Add rotation targets if score is negative
    if score < 0:
        targets = current_state.get("rotation_targets", [])[:2]
        if targets:
            msg_parts.append("")
            msg_parts.append("Top rotation candidates:")
            for t in targets:
                msg_parts.append(f"  → {t['name']} ({', '.join(t['tickers'])})")

    alert_system._send_alert("\n".join(msg_parts), urgent=(level == "red"))
    logger.info("End-of-day summary sent")


def graceful_shutdown(signum, frame):
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    logger.info("Starting Mining Rotation Monitor Scheduler")
    logger.info(f"  Market hours updates: every {UPDATE_INTERVAL_MINUTES} min ({MARKET_OPEN_HOUR}:00-{MARKET_CLOSE_HOUR}:00 ET)")
    logger.info("  Full updates: every 2 hours")
    logger.info("  EOD summary: daily at 18:00 ET")

    # Initial full load
    run_update(include_fred=True)

    # Schedule jobs
    scheduler.add_job(
        market_hours_update,
        IntervalTrigger(minutes=UPDATE_INTERVAL_MINUTES),
        id="market_hours",
        name="Market hours price update",
    )

    scheduler.add_job(
        full_update,
        IntervalTrigger(hours=2),
        id="full_update",
        name="Full update with FRED",
    )

    scheduler.add_job(
        end_of_day_summary,
        CronTrigger(hour=18, minute=0, timezone="US/Eastern"),
        id="eod_summary",
        name="End-of-day summary alert",
    )

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    scheduler.start()
