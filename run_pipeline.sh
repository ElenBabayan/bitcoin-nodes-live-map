#!/bin/bash
#
# Bitcoin Nodes Live Map - Full Pipeline Runner
# Runs all steps: fetch nodes, geolocate, visualize
# Now uses SQLite database for efficient storage!
#

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Bitcoin Nodes Live Map - Full Pipeline Runner        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON="python3"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo "❌ Error: Python not found. Please install Python 3.7+"
    exit 1
fi

echo "✓ Using: $PYTHON"
echo ""

# Check dependencies
echo "📦 Checking dependencies..."
if ! $PYTHON -c "import requests, folium, geoip2" 2>/dev/null; then
    echo "⚠️  Missing dependencies. Installing..."
    if command -v pip3 &> /dev/null; then
        pip3 install -r requirements.txt
    else
        pip install -r requirements.txt
    fi
else
    echo "✓ Dependencies installed"
fi
echo ""

# Database file
DB_FILE="bitcoin_peers.db"

echo ""

# Step 1: Fetch nodes
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1/3: Fetching Bitcoin nodes from bitnodes.io..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Use cached data if DB exists, otherwise fetch from API
$PYTHON fetch_bitnodes.py --db "$DB_FILE" --use-cached
echo ""

# Step 2: Geolocate
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2/3: Geolocating nodes using MaxMind database..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON geolocate_maxmind.py --db "$DB_FILE" --use-db --no-json
echo ""

# Step 3: Visualize
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3/3: Creating heatmap visualization..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON visualize_peers_map.py --db "$DB_FILE" --use-db
echo ""

# Done
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ COMPLETE!                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Results:"
echo "   • $DB_FILE                   - SQLite database (can be committed!)"
echo "   • bitcoin_peers_map.html     - Interactive heatmap"
echo ""
echo "💡 Database commands:"
echo "   • python3 database.py --db $DB_FILE --stats   # Show statistics"
echo "   • python3 database.py --db $DB_FILE --list    # List snapshots"
echo ""
echo "🌐 Opening map in browser..."

# Open in browser (cross-platform)
if command -v open &> /dev/null; then
    open bitcoin_peers_map.html
elif command -v xdg-open &> /dev/null; then
    xdg-open bitcoin_peers_map.html
elif command -v start &> /dev/null; then
    start bitcoin_peers_map.html
else
    echo "   Please open bitcoin_peers_map.html manually"
fi

echo ""
echo "✨ Done!"


