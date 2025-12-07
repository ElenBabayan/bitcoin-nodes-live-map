#!/bin/bash
#
# Fix corrupted bitcoin_peers.db by fetching fresh data
#

echo "🔧 Fixing corrupted database..."
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

# Remove corrupted database
if [ -f "bitcoin_peers.db" ]; then
    echo "Removing corrupted bitcoin_peers.db..."
    rm bitcoin_peers.db
fi

# Fetch fresh data
echo "Fetching fresh data from bitnodes.io API..."
$PYTHON fetch_from_api.py --db bitcoin_peers.db

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database fixed! You can now run:"
    echo "   ./run_pipeline.sh"
else
    echo ""
    echo "❌ Failed to fetch data. Check your internet connection."
    exit 1
fi

