"""
Alert System
============
Sends SMS (Twilio) and/or email alerts when:
  - Composite score crosses a threshold
  - A signal flips from bullish to bearish (or vice versa)
  - Score trend deteriorates
"""

import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Dict, List, Optional

from config import (
    ALERT_EMAIL, ALERT_LOG, ALERT_PHONE,
    SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER,
    TWILIO_AUTH, TWILIO_FROM, TWILIO_SID,
)

logger = logging.getLogger(__name__)


class AlertSystem:

    def __init__(self):
        self.last_alert_level: Optional[str] = None
        self.last_signal_states: Dict[str, str] = {}
        self._load_state()

    def _load_state(self):
        """Load previous alert state from disk."""
        try:
            with open(ALERT_LOG, "r") as f:
                data = json.load(f)
                self.last_alert_level = data.get("last_alert_level")
                self.last_signal_states = data.get("last_signal_states", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        """Persist alert state to disk."""
        try:
            with open(ALERT_LOG, "w") as f:
                json.dump({
                    "last_alert_level": self.last_alert_level,
                    "last_signal_states": self.last_signal_states,
                    "updated": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alert state: {e}")

    def check_and_alert(self, dashboard_state: Dict) -> List[str]:
        """Check dashboard state and send alerts if warranted.
        Returns list of alert messages sent."""
        alerts_sent = []
        current_level = dashboard_state.get("alert_level", "green")
        composite = dashboard_state.get("composite_score", 0)
        status = dashboard_state.get("composite_status", "WATCH")
        signals = dashboard_state.get("signals", [])

        # ── 1. Composite level change ──────────
        level_priority = {"green": 0, "yellow": 1, "orange": 2, "red": 3}
        current_pri = level_priority.get(current_level, 0)
        last_pri = level_priority.get(self.last_alert_level, 0)

        if current_pri > last_pri:
            # Escalation — always alert
            msg = self._build_escalation_alert(dashboard_state)
            self._send_alert(msg, urgent=(current_level in ("orange", "red")))
            alerts_sent.append(msg)

        elif current_pri < last_pri and self.last_alert_level in ("orange", "red"):
            # De-escalation from warning — send relief alert
            msg = (
                f"🟢 MINING ROTATION MONITOR — DE-ESCALATION\n"
                f"Status: {status} (was {self.last_alert_level.upper()})\n"
                f"Score: {composite:+.1f}\n"
                f"Conditions improving. Review dashboard for details."
            )
            self._send_alert(msg, urgent=False)
            alerts_sent.append(msg)

        # ── 2. Individual signal flips ─────────
        flipped = []
        for sig in signals:
            name = sig["name"]
            current_status = sig["status"]
            prev_status = self.last_signal_states.get(name)

            if prev_status and prev_status != current_status:
                if prev_status == "bullish" and current_status == "bearish":
                    flipped.append(f"  ⬇️ {name}: {prev_status} → {current_status}")
                elif prev_status == "bearish" and current_status == "bullish":
                    flipped.append(f"  ⬆️ {name}: {prev_status} → {current_status}")

        if flipped and current_level in ("orange", "red"):
            flip_msg = (
                f"🔄 SIGNAL FLIP ALERT\n"
                + "\n".join(flipped)
                + f"\nComposite: {composite:+.1f} ({status})"
            )
            self._send_alert(flip_msg, urgent=False)
            alerts_sent.append(flip_msg)

        # ── Update state ───────────────────────
        self.last_alert_level = current_level
        self.last_signal_states = {s["name"]: s["status"] for s in signals}
        self._save_state()

        return alerts_sent

    def _build_escalation_alert(self, state: Dict) -> str:
        """Build escalation alert message."""
        level = state.get("alert_level", "yellow").upper()
        status = state.get("composite_status", "WATCH")
        score = state.get("composite_score", 0)
        msg = state.get("alert_message", "")

        bearish_signals = [
            s for s in state.get("signals", [])
            if s["status"] == "bearish"
        ]

        # Top rotation targets
        targets = state.get("rotation_targets", [])[:3]
        target_lines = [
            f"  → {t['name']} (score: {t['score']:.0%}) — {', '.join(t['tickers'])}"
            for t in targets if t["score"] > 0
        ]

        parts = [
            f"{'🔴' if level == 'RED' else '🟠'} MINING ROTATION MONITOR — {level}",
            f"Status: {status} | Score: {score:+.1f}",
            f"{msg}",
            "",
            "Bearish signals firing:",
        ]
        for s in bearish_signals:
            parts.append(f"  • {s['name']}: {s['detail']}")

        if target_lines:
            parts.append("")
            parts.append("Top rotation targets:")
            parts.extend(target_lines)

        return "\n".join(parts)

    def _send_alert(self, message: str, urgent: bool = False):
        """Send alert via configured channels."""
        logger.info(f"ALERT ({'URGENT' if urgent else 'INFO'}): {message[:100]}...")

        # SMS via Twilio
        if TWILIO_SID and TWILIO_AUTH and TWILIO_FROM and ALERT_PHONE:
            try:
                self._send_sms(message)
            except Exception as e:
                logger.error(f"SMS send failed: {e}")

        # Email
        if SMTP_USER and SMTP_PASS and ALERT_EMAIL:
            try:
                self._send_email(message, urgent)
            except Exception as e:
                logger.error(f"Email send failed: {e}")

    def _send_sms(self, message: str):
        """Send SMS via Twilio."""
        from twilio.rest import Client
        client = Client(TWILIO_SID, TWILIO_AUTH)
        # Truncate for SMS
        sms_body = message[:1500]
        client.messages.create(
            body=sms_body,
            from_=TWILIO_FROM,
            to=ALERT_PHONE,
        )
        logger.info("SMS sent successfully")

    def _send_email(self, message: str, urgent: bool):
        """Send email alert."""
        subject = (
            "🔴 MINING ROTATION — URGENT" if urgent
            else "Mining Rotation Monitor Update"
        )
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = ALERT_EMAIL

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        logger.info("Email sent successfully")

    def force_alert(self, message: str):
        """Send an immediate alert regardless of state changes."""
        self._send_alert(message, urgent=True)
