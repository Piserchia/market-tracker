#!/bin/bash
# Crypto Daily Research — Claude Code CLI
# Point Docker scheduler here. Run daily after market close.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRYPTO_DIR="$(dirname "$SCRIPT_DIR")"
PORTFOLIO=$(cat "$CRYPTO_DIR/portfolio.json")
SUGGESTIONS_FILE="$CRYPTO_DIR/data/crypto_suggestions.json"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG="$CRYPTO_DIR/data/crypto_research_$(date +%Y%m%d).log"
mkdir -p "$CRYPTO_DIR/data"
echo "[$TS] Starting crypto research..." | tee -a "$LOG"

PROMPT="You are a senior crypto analyst helping an investor manage a portfolio focused on BTC, ETH, SOL, and select alts. Today is $(date +"%A, %B %d, %Y").

Current Portfolio:
$PORTFOLIO

Research current crypto market conditions and produce JSON with:
1. market_summary (2-3 sentences)
2. on_chain_highlights (BTC MVRV, ETF flows, funding rates, whale activity)
3. new_suggestions (2-4 coins NOT in portfolio): coin_id, symbol, name, why_now, category, risk_level, suggested_allocation_usd, bull_case, bear_case
4. position_suggestions (0-3): coin_id, action (increase|decrease), rationale
5. btc_cycle_assessment
6. sector_outlook, sector_sentiment (bullish|neutral|bearish)
7. risks_to_watch (2-3 specific near-term risks)
8. confidence (high|medium|low)

Output ONLY valid JSON, no markdown fences, no preamble."

echo "[$TS] Invoking Claude..." | tee -a "$LOG"
CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG") || { echo "ERROR" | tee -a "$LOG"; exit 1; }

echo "$CLAUDE_OUTPUT" | python3 -c "
import sys,json,re
raw=sys.stdin.read().strip()
raw=re.sub(r'^[^\{]*','',raw,count=1)
raw=re.sub(r'[^\}]*$','',raw[::-1],count=1)[::-1]
try: p=json.loads(raw); p['_generated_at']='$TS'; print(json.dumps(p,indent=2))
except: print(json.dumps({'_error':'parse_failed','raw':raw[:2000],'new_suggestions':[],'sector_sentiment':'unknown'},indent=2))
" > "$SUGGESTIONS_FILE" 2>>"$LOG"

echo "[$TS] Saved to $SUGGESTIONS_FILE" | tee -a "$LOG"
echo "[$TS] Done." | tee -a "$LOG"
