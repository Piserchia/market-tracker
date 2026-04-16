#!/bin/bash
# ═══════════════════════════════════════════════════════
# Daily Research Workflow
# ═══════════════════════════════════════════════════════
# Invokes Claude Code CLI to:
#   1. Review current portfolio holdings and market conditions
#   2. Identify stocks NOT in portfolio that merit investigation
#   3. Suggest position increases for existing holdings
#   4. Flag any holdings that should be reduced
#
# Output: suggestions.json (read by the dashboard)
#
# Usage: ./daily_research.sh
# Schedule: Point your Docker scheduler to this script, run once daily
#           (ideally 30-60 min after market close, ~5 PM ET)
# ═══════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AI_SECTOR_DIR="$(dirname "$SCRIPT_DIR")"
PORTFOLIO_FILE="$AI_SECTOR_DIR/portfolio.json"
PROFILES_FILE="$AI_SECTOR_DIR/stock_profiles.json"
SUGGESTIONS_FILE="$AI_SECTOR_DIR/data/suggestions.json"
PROMPT_FILE="$SCRIPT_DIR/prompts/daily_research_prompt.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_FILE="$AI_SECTOR_DIR/data/research_$(date +%Y%m%d).log"

mkdir -p "$AI_SECTOR_DIR/data"

echo "[$TIMESTAMP] Starting daily research workflow..." | tee -a "$LOG_FILE"

# ── 1. Build context from current portfolio ──────────
PORTFOLIO_CONTEXT=$(cat "$PORTFOLIO_FILE")
PROFILES_CONTEXT=$(cat "$PROFILES_FILE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
profiles = data.get('profiles', {})
summary = []
for ticker, p in profiles.items():
    summary.append(f'{ticker}: {p.get(\"category\",\"?\")} | {p.get(\"risk_tier\",\"?\")} | sells: {\", \".join(p.get(\"sell_triggers\",[])[:])}')
print('\n'.join(summary))
" 2>/dev/null || echo "Could not parse profiles")

# ── 2. Get current date context ──────────────────────
CURRENT_DATE=$(date +"%A, %B %d, %Y")

# ── 3. Build the prompt ──────────────────────────────
PROMPT=$(cat <<PROMPTEOF
You are a senior equity research analyst helping an individual investor manage a ~\$115k portfolio focused on AI/tech with a goal of long-term growth. Today is $CURRENT_DATE.

## Current Portfolio
\`\`\`json
$PORTFOLIO_CONTEXT
\`\`\`

## Current Stock Profiles Summary
$PROFILES_CONTEXT

## Your Task

Perform research and produce a JSON response with the following structure. Be specific, cite real data, and think critically. Do not be promotional — be honest about risks.

### 1. Market Conditions Summary (2-3 sentences)
What's happening today that affects AI/tech stocks? Any earnings, macro events, geopolitical developments?

### 2. New Stock Suggestions (3-5 stocks NOT currently in the portfolio)
For each, provide:
- ticker, company name
- why_now: What specific catalyst or valuation setup makes this interesting RIGHT NOW
- category: chip_designer | server_infra | cloud_platform | ai_monetizer | connectivity | ai_power | ai_networking | ai_memory | ai_software | other
- risk_level: low | medium | high | speculative
- suggested_allocation: dollar amount appropriate for a \$115k portfolio
- bull_case: 1-2 sentences
- bear_case: 1-2 sentences
- key_metric_to_watch: The single most important number to track

### 3. Position Increase Suggestions (0-3 existing holdings worth adding to)
For each:
- ticker
- current_dollars: from portfolio
- suggested_increase: dollar amount to add
- rationale: Why add now specifically

### 4. Position Reduction Warnings (0-3 holdings that look risky)
For each:
- ticker
- current_dollars
- concern: Specific, factual reason for concern (not generic)
- severity: watch | trim | exit
- suggested_action: What to do and when

### 5. Sector Outlook (1-2 sentences)
Overall bullish/bearish/neutral on AI sector for the next 30 days and why.

## Output Format
Respond with ONLY valid JSON, no markdown fences, no preamble. Structure:
{
  "timestamp": "$TIMESTAMP",
  "market_summary": "...",
  "new_suggestions": [...],
  "increase_suggestions": [...],
  "reduction_warnings": [...],
  "sector_outlook": "...",
  "sector_sentiment": "bullish|neutral|bearish",
  "confidence": "high|medium|low"
}
PROMPTEOF
)

# ── 4. Invoke Claude Code CLI ────────────────────────
echo "[$TIMESTAMP] Invoking Claude Code CLI..." | tee -a "$LOG_FILE"

CLAUDE_OUTPUT=$(echo "$PROMPT" | claude -p --output-format text 2>>"$LOG_FILE") || {
    echo "[$TIMESTAMP] ERROR: Claude CLI invocation failed" | tee -a "$LOG_FILE"
    exit 1
}

# ── 5. Parse and save output ─────────────────────────
echo "[$TIMESTAMP] Parsing Claude output..." | tee -a "$LOG_FILE"

# Try to extract JSON from the response (handle potential markdown fences)
CLEAN_OUTPUT=$(echo "$CLAUDE_OUTPUT" | python3 -c "
import sys, json, re

raw = sys.stdin.read()

# Strip markdown code fences if present
raw = re.sub(r'^```json\s*', '', raw.strip())
raw = re.sub(r'\s*```$', '', raw.strip())

try:
    parsed = json.loads(raw)
    # Add metadata
    parsed['_generated_by'] = 'daily_research_workflow'
    parsed['_generated_at'] = '$TIMESTAMP'
    print(json.dumps(parsed, indent=2))
except json.JSONDecodeError as e:
    # If JSON parsing fails, wrap the raw text
    fallback = {
        '_generated_by': 'daily_research_workflow',
        '_generated_at': '$TIMESTAMP',
        '_parse_error': str(e),
        'raw_output': raw[:5000],
        'market_summary': 'Research completed but output parsing failed. See raw_output.',
        'new_suggestions': [],
        'increase_suggestions': [],
        'reduction_warnings': [],
        'sector_outlook': 'Unable to parse',
        'sector_sentiment': 'unknown',
        'confidence': 'low'
    }
    print(json.dumps(fallback, indent=2))
" 2>>"$LOG_FILE")

echo "$CLEAN_OUTPUT" > "$SUGGESTIONS_FILE"

echo "[$TIMESTAMP] Research complete. Saved to $SUGGESTIONS_FILE" | tee -a "$LOG_FILE"

# ── 6. Quick summary to stdout/log ──────────────────
python3 -c "
import json
with open('$SUGGESTIONS_FILE') as f:
    data = json.load(f)
print(f\"  Sector outlook: {data.get('sector_sentiment', '?')}\")
print(f\"  New suggestions: {len(data.get('new_suggestions', []))}\")
print(f\"  Increase suggestions: {len(data.get('increase_suggestions', []))}\")
print(f\"  Reduction warnings: {len(data.get('reduction_warnings', []))}\")
for s in data.get('new_suggestions', []):
    print(f\"    + {s.get('ticker','?')}: {s.get('why_now','')[:80]}\")
for w in data.get('reduction_warnings', []):
    print(f\"    ! {w.get('ticker','?')} [{w.get('severity','?')}]: {w.get('concern','')[:80]}\")
" 2>/dev/null | tee -a "$LOG_FILE"

echo "[$TIMESTAMP] Done." | tee -a "$LOG_FILE"
