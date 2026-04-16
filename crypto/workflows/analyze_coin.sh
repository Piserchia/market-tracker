#!/bin/bash
# Analyze a specific crypto — invoked when adding via UI or manually
# Usage: ./analyze_coin.sh SOL
set -euo pipefail
SYMBOL="${1:?Usage: ./analyze_coin.sh <SYMBOL>}"
SYMBOL=$(echo "$SYMBOL" | tr '[:lower:]' '[:upper:]')
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRYPTO_DIR="$(dirname "$SCRIPT_DIR")"
PROFILES_FILE="$CRYPTO_DIR/crypto_profiles.json"
ANALYSIS_FILE="$CRYPTO_DIR/data/analysis_${SYMBOL}.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG="$CRYPTO_DIR/data/analysis.log"
mkdir -p "$CRYPTO_DIR/data"
echo "[$TIMESTAMP] Analyzing $SYMBOL..." | tee -a "$LOG"

PROMPT=$(cat <<PROMPTEOF
You are a senior crypto analyst. Perform comprehensive analysis of $SYMBOL.

Research and provide:
1. Overview: What is this crypto? What problem does it solve?
2. Current state: Price action, recent developments, network metrics
3. Competitive position: Who competes? What's the moat?
4. On-chain health: TVL, active addresses, transaction volume, staking if applicable
5. Risk assessment: Specific concrete risks
6. Sell triggers: 3-5 specific measurable conditions to exit
7. Buy signals: 2-3 conditions that make it compelling

Output ONLY valid JSON:
{
  "symbol": "$SYMBOL",
  "analysis_date": "$TIMESTAMP",
  "overview": "...",
  "current_state": "...",
  "verdict": "accumulate|hold|caution|avoid",
  "confidence": "high|medium|low",
  "profile": {
    "name": "...",
    "category": "store_of_value|smart_contract_platform|high_performance_l1|oracle_infrastructure|payments|enterprise_l1|defi|gaming|meme|other",
    "risk_tier": "core|growth|moderate|speculative|high_risk",
    "coingecko_id": "...",
    "yahoo_symbol": "${SYMBOL}-USD",
    "thesis": "...",
    "sell_triggers": ["..."],
    "buy_signals": ["..."]
  }
}
PROMPTEOF
)

CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG") || {
    echo "[$TIMESTAMP] ERROR: Claude CLI failed for $SYMBOL" | tee -a "$LOG"
    echo '{"error":"Claude CLI failed","symbol":"'$SYMBOL'"}' > "$ANALYSIS_FILE"; exit 1
}

echo "$CLAUDE_OUTPUT" | python3 -c "
import sys, json, re
raw = re.sub(r'^```json\s*', '', sys.stdin.read().strip())
raw = re.sub(r'\s*```$', '', raw)
try:
    parsed = json.loads(raw)
    print(json.dumps(parsed, indent=2))
except: print(json.dumps({'error':'parse_failed','symbol':'$SYMBOL','raw':raw[:3000]}, indent=2))
" > "$ANALYSIS_FILE"

# Update profiles
python3 -c "
import json
with open('$ANALYSIS_FILE') as f: analysis = json.load(f)
profile = analysis.get('profile')
if not profile: exit(0)
with open('$PROFILES_FILE') as f: data = json.load(f)
data.setdefault('profiles', {})['$SYMBOL'] = profile
with open('$PROFILES_FILE', 'w') as f: json.dump(data, f, indent=2)
print(f'  Updated crypto_profiles.json with $SYMBOL')
" 2>>"$LOG" | tee -a "$LOG"

echo "[$TIMESTAMP] $SYMBOL analysis complete." | tee -a "$LOG"
