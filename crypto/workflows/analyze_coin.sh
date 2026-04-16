#!/bin/bash
# Analyze Coin — Claude Code CLI
# Auto-triggered when new coin added via UI. Manual: ./analyze_coin.sh chainlink LINK
set -euo pipefail
COIN_ID="${1:?Usage: ./analyze_coin.sh <coin_id> [symbol]}"
COIN_ID=$(echo "$COIN_ID" | tr '[:upper:]' '[:lower:]')
SYMBOL="${2:-$COIN_ID}"
SYMBOL=$(echo "$SYMBOL" | tr '[:lower:]' '[:upper:]')

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRYPTO_DIR="$(dirname "$SCRIPT_DIR")"
PROFILES_FILE="$CRYPTO_DIR/crypto_profiles.json"
ANALYSIS_FILE="$CRYPTO_DIR/data/analysis_${COIN_ID}.json"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG="$CRYPTO_DIR/data/analysis.log"
mkdir -p "$CRYPTO_DIR/data"
echo "[$TS] Analyzing $SYMBOL ($COIN_ID)..." | tee -a "$LOG"

PROMPT="You are a senior crypto analyst. Today is $(date +"%A, %B %d, %Y").

Analyze $SYMBOL (CoinGecko ID: $COIN_ID) for an investor with ~\$16K in SOL and watching BTC, ETH, LINK, XRP, AVAX. New to crypto.

Provide: overview, current_state, competitive_position, on_chain_health, risk_assessment, verdict (accumulate|hold|watch|avoid), confidence, and a profile object with: name, symbol, category (store_of_value|smart_contract_platform|infrastructure|payments|defi|gaming|ai_crypto), risk_tier (core|growth|moderate|speculative), role, key_drivers, thresholds (with value/direction/severity/description), sell_triggers (3-4 specific measurable), buy_signals (2-3 specific), cycle_notes.

Output ONLY valid JSON, no fences."

echo "[$TS] Invoking Claude for $SYMBOL..." | tee -a "$LOG"
CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG") || { echo "ERROR" | tee -a "$LOG"; exit 1; }

echo "$CLAUDE_OUTPUT" | python3 -c "
import sys,json,re
raw=sys.stdin.read().strip()
raw=re.sub(r'^[^\{]*','',raw,count=1)
raw=re.sub(r'[^\}]*$','',raw[::-1],count=1)[::-1]
try: p=json.loads(raw); print(json.dumps(p,indent=2))
except: print(json.dumps({'coin_id':'$COIN_ID','error':'parse_failed','raw':raw[:2000]},indent=2))
" > "$ANALYSIS_FILE" 2>>"$LOG"

echo "[$TS] Analysis saved to $ANALYSIS_FILE" | tee -a "$LOG"

# Update crypto_profiles.json
python3 -c "
import json
with open('$ANALYSIS_FILE') as f: analysis=json.load(f)
profile=analysis.get('profile')
if not profile: print('  No profile generated'); exit(0)
with open('$PROFILES_FILE') as f: profiles=json.load(f)
profiles.setdefault('profiles',{})['$COIN_ID']=profile
with open('$PROFILES_FILE','w') as f: json.dump(profiles,f,indent=2)
print(f'  Updated profiles: $SYMBOL ({profile.get(\"category\",\"?\")}, {profile.get(\"risk_tier\",\"?\")})')
" 2>>"$LOG" | tee -a "$LOG"

echo "[$TS] $SYMBOL complete." | tee -a "$LOG"
