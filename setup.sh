#!/bin/bash
# ═══════════════════════════════════════════════
# Mining Rotation Monitor — Mac Mini Setup
# ═══════════════════════════════════════════════
# Run this once on your Mac Mini to set everything up.
# Usage: chmod +x setup.sh && ./setup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "═══════════════════════════════════════════════"
echo "  Mining Rotation Monitor — Setup"
echo "═══════════════════════════════════════════════"

# ── 1. Python virtual environment ────────────
echo ""
echo "→ Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  Created venv at $VENV_DIR"
else
    echo "  Venv already exists"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q
echo "  Dependencies installed ✓"

# ── 2. Data directory ────────────────────────
mkdir -p "$SCRIPT_DIR/data"
mkdir -p "$SCRIPT_DIR/static"
echo "→ Data directory ready ✓"

# ── 3. Environment file ─────────────────────
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'ENVEOF'
# ═══════════════════════════════════════════════
# Mining Rotation Monitor — Environment Variables
# ═══════════════════════════════════════════════
# Fill in the values below and source this file
# before running the server/scheduler.

# FRED API (free: https://fred.stlouisfed.org/docs/api/api_key.html)
export FRED_API_KEY=""

# Twilio SMS alerts (optional)
export TWILIO_SID=""
export TWILIO_AUTH=""
export TWILIO_FROM=""       # Your Twilio phone number
export ALERT_PHONE=""       # Your cell phone number

# Email alerts (optional — Gmail example)
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER=""         # Your Gmail address
export SMTP_PASS=""         # App password (not your regular password)
export ALERT_EMAIL=""       # Where to receive alerts
ENVEOF
    echo "→ Created .env file — EDIT THIS with your API keys!"
    echo "  $ENV_FILE"
else
    echo "→ .env file already exists"
fi

# ── 4. Quick test ────────────────────────────
echo ""
echo "→ Running quick connectivity test..."
source "$ENV_FILE" 2>/dev/null || true
python3 -c "
import yfinance as yf
data = yf.Ticker('GDX').fast_info
print(f'  GDX last price: \${data[\"lastPrice\"]:.2f} ✓')
" 2>/dev/null || echo "  ⚠ yfinance test failed — check internet connection"

# ── 5. launchd plist for auto-start ──────────
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_SERVER="$PLIST_DIR/com.mining-rotation.server.plist"
PLIST_SCHEDULER="$PLIST_DIR/com.mining-rotation.scheduler.plist"
mkdir -p "$PLIST_DIR"

cat > "$PLIST_SERVER" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mining-rotation.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$SCRIPT_DIR/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/data/server.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/data/server_error.log</string>
</dict>
</plist>
PLISTEOF

cat > "$PLIST_SCHEDULER" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mining-rotation.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>$VENV_DIR/bin/python3</string>
        <string>$SCRIPT_DIR/scheduler.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$SCRIPT_DIR/data/scheduler.log</string>
    <key>StandardErrorPath</key>
    <string>$SCRIPT_DIR/data/scheduler_error.log</string>
</dict>
</plist>
PLISTEOF

echo "→ Created launchd plists ✓"
echo "  $PLIST_SERVER"
echo "  $PLIST_SCHEDULER"

# ── 6. Helper scripts ────────────────────────
cat > "$SCRIPT_DIR/start.sh" << 'STARTEOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.env" 2>/dev/null || true
source "$DIR/.venv/bin/activate"

echo "Starting Mining Rotation Monitor..."
echo "Dashboard: http://localhost:8787"
echo "Press Ctrl+C to stop"
python3 "$DIR/server.py"
STARTEOF
chmod +x "$SCRIPT_DIR/start.sh"

cat > "$SCRIPT_DIR/start-scheduler.sh" << 'SCHEDEOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.env" 2>/dev/null || true
source "$DIR/.venv/bin/activate"
python3 "$DIR/scheduler.py"
SCHEDEOF
chmod +x "$SCRIPT_DIR/start-scheduler.sh"

cat > "$SCRIPT_DIR/register-services.sh" << 'REGEOF'
#!/bin/bash
# Register launchd services to auto-start on boot
echo "Registering services..."
launchctl load ~/Library/LaunchAgents/com.mining-rotation.server.plist
launchctl load ~/Library/LaunchAgents/com.mining-rotation.scheduler.plist
echo "Services registered. They will auto-start on boot."
echo "Check status: launchctl list | grep mining"
REGEOF
chmod +x "$SCRIPT_DIR/register-services.sh"

cat > "$SCRIPT_DIR/unregister-services.sh" << 'UNREGEOF'
#!/bin/bash
echo "Unregistering services..."
launchctl unload ~/Library/LaunchAgents/com.mining-rotation.server.plist 2>/dev/null
launchctl unload ~/Library/LaunchAgents/com.mining-rotation.scheduler.plist 2>/dev/null
echo "Services unregistered."
UNREGEOF
chmod +x "$SCRIPT_DIR/unregister-services.sh"

# ── Done ─────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Setup Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  NEXT STEPS:"
echo ""
echo "  1. Edit .env with your API keys:"
echo "     nano $ENV_FILE"
echo ""
echo "  2. Get a free FRED API key:"
echo "     https://fred.stlouisfed.org/docs/api/api_key.html"
echo ""
echo "  3. (Optional) Set up Twilio for SMS alerts"
echo ""
echo "  4. Copy the dashboard HTML to static/:"
echo "     (built separately as a React artifact)"
echo ""
echo "  5. Start manually:"
echo "     ./start.sh"
echo ""
echo "  6. Or register as auto-start services:"
echo "     ./register-services.sh"
echo ""
echo "  Dashboard will be at: http://localhost:8787"
echo "  API endpoint: http://localhost:8787/api/state"
echo ""
