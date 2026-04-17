#!/bin/bash
# ═══════════════════════════════════════════════════════
# Build Dashboard HTML Files
# ═══════════════════════════════════════════════════════
# Converts JSX artifacts into standalone HTML files that Flask serves.
# Run once after cloning, or after editing any JSX dashboard file.
#
# Usage: ./build_dashboards.sh
# ═══════════════════════════════════════════════════════

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
DASHBOARD_DIR="$DIR/dashboard"

echo "Building dashboard HTML files..."

build_html() {
    local JSX_FILE="$1"
    local OUTPUT_FILE="$2"
    local TITLE="$3"
    local COMPONENT_NAME="$4"

    if [ ! -f "$JSX_FILE" ]; then
        echo "  SKIP: $JSX_FILE not found"
        return
    fi

    # Read JSX, strip import/export lines for browser compatibility
    local JSX_CONTENT
    JSX_CONTENT=$(cat "$JSX_FILE" | \
        sed 's/^import .*//' | \
        sed 's/^export default /const __App__ = /' | \
        sed "s/export default/const __App__ =/" \
    )

    cat > "$OUTPUT_FILE" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${TITLE}</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:#080b12}</style>
</head>
<body>
<div id="root"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.3.1/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.3.1/umd/react-dom.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.26.5/babel.min.js"></script>
<script type="text/babel" data-type="module">
const { useState, useEffect, useCallback } = React;

${JSX_CONTENT}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(__App__));
</script>
</body>
</html>
HTMLEOF

    echo "  ✓ Built: $OUTPUT_FILE"
}

# Mining dashboard → static/index.html (already has landing page, use mining.html)
build_html \
    "$DASHBOARD_DIR/MiningRotationDashboard.jsx" \
    "$DIR/static/mining.html" \
    "Mining Rotation Monitor" \
    "MiningRotationDashboard"

# Stocks dashboard (renamed from AI Sector — now covers all equity holdings with sector filtering)
mkdir -p "$DIR/ai_sector/static"
build_html \
    "$DASHBOARD_DIR/StocksDashboard.jsx" \
    "$DIR/ai_sector/static/index.html" \
    "Stocks Dashboard" \
    "StocksDashboard"

# Crypto dashboard
mkdir -p "$DIR/crypto/static"
build_html \
    "$DASHBOARD_DIR/CryptoDashboard.jsx" \
    "$DIR/crypto/static/index.html" \
    "Crypto Dashboard" \
    "CryptoDashboard"

echo ""
echo "Done! Dashboards are at:"
echo "  Landing:  http://localhost:8787"
echo "  Mining:   http://localhost:8787/mining.html"
echo "  AI:       http://localhost:8788"
echo "  Crypto:   http://localhost:8789"
