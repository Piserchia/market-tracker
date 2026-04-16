#!/bin/bash
# Daily Crypto Research — invokes Claude Code CLI
# Schedule: Run once daily, ideally after US market close
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRYPTO_DIR="$(dirname "$SCRIPT_DIR")"
PORTFOLIO=$(cat "$CRYPTO_DIR/crypto_portfolio.json")
SUGGESTIONS_FILE="$CRYPTO_DIR/data/crypto_suggestions.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG="$CRYPTO_DIR/data/crypto_research_$(date +%Y%m%d).log"
mkdir -p "$CRYPTO_DIR/data"
echo "[$TIMESTAMP] Starting daily crypto research..." | tee -a "$LOG"

PROMPT=$(cat <<'PROMPTEOF'
You are a senior crypto analyst. Today is CURRENT_DATE.

## Current Portfolio
PORTFOLIO_JSON

## Task
Research the crypto market and produce JSON with:

1. market_summary: 2-3 sentences on today's crypto conditions
2. new_suggestions: 2-4 coins NOT in portfolio worth investigating. For each:
   - symbol, name, price_approx, category, risk_level
   - why_now: specific catalyst making this interesting RIGHT NOW
   - bull_case, bear_case (1-2 sentences each)
3. position_changes: 0-3 suggestions to increase/decrease existing holdings
   - symbol, action (increase/decrease/hold), rationale
4. on_chain_insights: Any notable on-chain signals (MVRV, funding rates, whale movements, ETF flows)
5. sector_sentiment: bullish/neutral/bearish for next 30 days

Output ONLY valid JSON, no markdown fences:
{"timestamp":"...","market_summary":"...","new_suggestions":[...],"position_changes":[...],"on_chain_insights":"...","sector_sentiment":"...","confidence":"high|medium|low"}
PROMPTEOF
)

PROMPT="${PROMPT//CURRENT_DATE/$(date +"%A, %B %d, %Y")}"
PROMPT="${PROMPT//PORTFOLIO_JSON/$PORTFOLIO}"

CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG") || {
    echo "[$TIMESTAMP] ERROR: Claude CLI failed" | tee -a "$LOG"; exit 1
}

echo "$CLAUDE_OUTPUT" | python3 -c "
import sys, json, re
raw = re.sub(r'^```json\s*', '', sys.stdin.read().strip())
raw = re.sub(r'\s*```$', '', raw)
try:
    parsed = json.loads(raw)
    parsed['_generated_at'] = '$TIMESTAMP'
    print(json.dumps(parsed, indent=2))
except json.JSONDecodeError as e:
    print(json.dumps({'_generated_at':'$TIMESTAMP','_error':str(e),'raw':raw[:3000],'new_suggestions':[],'position_changes':[],'sector_sentiment':'unknown'}, indent=2))
" > "$SUGGESTIONS_FILE"

echo "[$TIMESTAMP] Saved to $SUGGESTIONS_FILE" | tee -a "$LOG"
