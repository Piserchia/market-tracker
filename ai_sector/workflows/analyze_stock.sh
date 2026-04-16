#!/bin/bash
# ═══════════════════════════════════════════════════════
# Analyze Stock Workflow
# ═══════════════════════════════════════════════════════
# Invokes Claude Code CLI to deeply analyze a specific stock and
# generate a stock profile (sell triggers, buy signals, thresholds).
#
# Called automatically when a stock is added via the dashboard UI,
# or manually: ./analyze_stock.sh PLTR
#
# Output: Writes/updates the stock's entry in stock_profiles.json
#         Also saves full analysis to data/analysis_<TICKER>.json
# ═══════════════════════════════════════════════════════

set -euo pipefail

TICKER="${1:?Usage: ./analyze_stock.sh <TICKER>}"
TICKER=$(echo "$TICKER" | tr '[:lower:]' '[:upper:]')

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AI_SECTOR_DIR="$(dirname "$SCRIPT_DIR")"
PROFILES_FILE="$AI_SECTOR_DIR/stock_profiles.json"
PORTFOLIO_FILE="$AI_SECTOR_DIR/portfolio.json"
ANALYSIS_FILE="$AI_SECTOR_DIR/data/analysis_${TICKER}.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_FILE="$AI_SECTOR_DIR/data/analysis.log"

mkdir -p "$AI_SECTOR_DIR/data"

echo "[$TIMESTAMP] Analyzing $TICKER..." | tee -a "$LOG_FILE"

# ── 1. Check if profile already exists ───────────────
EXISTING_PROFILE=$(python3 -c "
import json
with open('$PROFILES_FILE') as f:
    data = json.load(f)
profile = data.get('profiles', {}).get('$TICKER')
if profile:
    print(json.dumps(profile, indent=2))
else:
    print('NONE')
" 2>/dev/null || echo "NONE")

# ── 2. Get current portfolio context ─────────────────
CURRENT_HOLDINGS=$(python3 -c "
import json
with open('$PORTFOLIO_FILE') as f:
    data = json.load(f)
tickers = list(set(h['ticker'] for h in data.get('holdings', [])))
tickers.sort()
print(', '.join(tickers))
" 2>/dev/null || echo "unknown")

CURRENT_DATE=$(date +"%A, %B %d, %Y")

# ── 3. Build the prompt ──────────────────────────────
PROMPT=$(cat <<PROMPTEOF
You are a senior equity research analyst. Today is $CURRENT_DATE.

Perform a comprehensive analysis of **$TICKER** for an individual investor with a ~\$115k portfolio. The investor's current holdings include: $CURRENT_HOLDINGS.

$(if [ "$EXISTING_PROFILE" != "NONE" ]; then
echo "## Existing Profile (update if needed)"
echo "\`\`\`json"
echo "$EXISTING_PROFILE"
echo "\`\`\`"
fi)

## Research and provide:

1. **Company Overview**: What does the company do? Where does it sit in the AI/tech value chain? What's the investment thesis in 2-3 sentences?

2. **Current State**: Recent earnings, revenue trajectory, margin trends, any recent news or catalysts.

3. **Competitive Position**: Who are the main competitors? What's the moat (or lack thereof)?

4. **Valuation Assessment**: Is it cheap, fair, or expensive right now? Use forward P/E, PEG, EV/EBITDA, FCF yield — whichever metrics are most relevant.

5. **Risk Assessment**: What are the specific, concrete risks? Not generic platitudes — real risks.

6. **Sell Triggers**: 3-5 specific, measurable conditions that should make the investor sell this stock. Be precise — include numbers where possible.

7. **Buy Signals**: 2-3 specific conditions that would make this a compelling add.

8. **Category and Tags**: Where this stock fits in the AI/tech landscape.

## Output Format
Respond with ONLY valid JSON, no markdown fences, no preamble:
{
  "ticker": "$TICKER",
  "name": "Company Name",
  "analysis_date": "$TIMESTAMP",
  "overview": "...",
  "current_state": "...",
  "competitive_position": "...",
  "valuation_assessment": "...",
  "verdict": "buy|hold|sell|avoid",
  "confidence": "high|medium|low",
  "profile": {
    "name": "Company Name",
    "category": "chip_designer|chip_fabricator|server_infra|cloud_platform|ai_monetizer|connectivity|ai_power|ai_networking|ai_memory|ai_software|speculative|non_tech",
    "risk_tier": "core_hold|core_growth|turnaround|speculative|high_risk",
    "value_chain_position": "One sentence description",
    "sector_signal_sensitivity": ["list", "of", "relevant", "sector", "signals"],
    "fundamental_thresholds": {
      "metric_name_floor_or_ceiling": {
        "value": 0.0,
        "severity": "high|medium|immediate",
        "description": "What this threshold means"
      }
    },
    "sell_triggers": ["Specific measurable condition 1", "Condition 2", "Condition 3"],
    "buy_signals": ["Specific condition 1", "Condition 2"],
    "earnings_metrics_to_track": ["metric1", "metric2"],
    "last_earnings_update": null,
    "manual_fundamentals": {}
  }
}
PROMPTEOF
)

# ── 4. Invoke Claude Code CLI ────────────────────────
echo "[$TIMESTAMP] Invoking Claude Code CLI for $TICKER..." | tee -a "$LOG_FILE"

CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG_FILE") || {
    echo "[$TIMESTAMP] ERROR: Claude CLI failed for $TICKER" | tee -a "$LOG_FILE"
    echo '{"error": "Claude CLI invocation failed", "ticker": "'$TICKER'"}' > "$ANALYSIS_FILE"
    exit 1
}

# ── 5. Parse output ──────────────────────────────────
echo "[$TIMESTAMP] Parsing analysis for $TICKER..." | tee -a "$LOG_FILE"

CLEAN_OUTPUT=$(echo "$CLAUDE_OUTPUT" | python3 -c "
import sys, json, re
raw = sys.stdin.read().strip()
raw = re.sub(r'^```json\s*', '', raw)
raw = re.sub(r'\s*```$', '', raw)
try:
    parsed = json.loads(raw)
    print(json.dumps(parsed, indent=2))
except json.JSONDecodeError as e:
    fallback = {
        'ticker': '$TICKER',
        'error': 'JSON parse failed',
        'parse_error': str(e),
        'raw_output': raw[:5000]
    }
    print(json.dumps(fallback, indent=2))
" 2>>"$LOG_FILE")

# Save full analysis
echo "$CLEAN_OUTPUT" > "$ANALYSIS_FILE"
echo "[$TIMESTAMP] Full analysis saved to $ANALYSIS_FILE" | tee -a "$LOG_FILE"

# ── 6. Update stock_profiles.json ────────────────────
python3 -c "
import json, sys

analysis_file = '$ANALYSIS_FILE'
profiles_file = '$PROFILES_FILE'
ticker = '$TICKER'

with open(analysis_file) as f:
    analysis = json.load(f)

# Extract the profile section
new_profile = analysis.get('profile')
if not new_profile:
    print(f'  No profile generated for {ticker}, skipping profiles update')
    sys.exit(0)

# Load existing profiles
with open(profiles_file) as f:
    profiles_data = json.load(f)

# Update or add the profile
profiles_data.setdefault('profiles', {})[ticker] = new_profile

# Save
with open(profiles_file, 'w') as f:
    json.dump(profiles_data, f, indent=2)

print(f'  Updated stock_profiles.json with {ticker} profile')
print(f'  Category: {new_profile.get(\"category\", \"?\")}')
print(f'  Risk tier: {new_profile.get(\"risk_tier\", \"?\")}')
print(f'  Sell triggers: {len(new_profile.get(\"sell_triggers\", []))}')
" 2>>"$LOG_FILE" | tee -a "$LOG_FILE"

# ── 7. Print summary ────────────────────────────────
python3 -c "
import json
with open('$ANALYSIS_FILE') as f:
    data = json.load(f)
if 'error' in data:
    print(f'  ERROR: {data[\"error\"]}')
else:
    print(f'  Verdict: {data.get(\"verdict\", \"?\").upper()}')
    print(f'  Confidence: {data.get(\"confidence\", \"?\")}')
    v = data.get('valuation_assessment', '')
    print(f'  Valuation: {v[:120]}...' if len(v) > 120 else f'  Valuation: {v}')
" 2>/dev/null | tee -a "$LOG_FILE"

echo "[$TIMESTAMP] $TICKER analysis complete." | tee -a "$LOG_FILE"
