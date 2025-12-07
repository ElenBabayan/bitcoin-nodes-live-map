#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    Bitcoin Testnet Crawler Pipeline                         ║
# ║                    Powered by Redis (Not SQLite!)                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    ₿ BITCOIN TESTNET CRAWLER PIPELINE                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis server is not running!"
    echo "   Start it with: redis-server"
    echo "   Or install with: brew install redis (macOS)"
    exit 1
fi
echo "✅ Redis server is running"
echo ""

# Default values
TARGET_PEERS=${TARGET_PEERS:-10000}
CONCURRENCY=${CONCURRENCY:-300}
THEME=${THEME:-bitcoin}
SKIP_CRAWL=${SKIP_CRAWL:-false}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET_PEERS="$2"
            shift 2
            ;;
        --concurrency)
            CONCURRENCY="$2"
            shift 2
            ;;
        --theme)
            THEME="$2"
            shift 2
            ;;
        --skip-crawl)
            SKIP_CRAWL=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --target N       Target number of peers (default: 10000)"
            echo "  --concurrency N  Parallel connections (default: 300)"
            echo "  --theme THEME    Visualization theme: bitcoin, cyber, neon (default: bitcoin)"
            echo "  --skip-crawl     Skip crawling, only geolocate and visualize"
            echo "  --help           Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  BITCOIN_RPC_USER     Bitcoin Core RPC username"
            echo "  BITCOIN_RPC_PASSWORD Bitcoin Core RPC password"
            echo "  BITCOIN_RPC_HOST     Bitcoin Core RPC host (default: 127.0.0.1)"
            echo "  BITCOIN_RPC_PORT     Bitcoin Core RPC port (default: 18332)"
            echo "  REDIS_HOST           Redis host (default: localhost)"
            echo "  REDIS_PORT           Redis port (default: 6379)"
            echo "  REDIS_DB             Redis database number (default: 1)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Step 1: Crawl (if not skipped)
if [ "$SKIP_CRAWL" = false ]; then
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║  STEP 1/3: CRAWLING BITCOIN TESTNET NETWORK                               ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🎯 Target: $TARGET_PEERS peers"
    echo "⚡ Concurrency: $CONCURRENCY connections"
    echo ""
    
    python3 crawler.py --target "$TARGET_PEERS" --concurrency "$CONCURRENCY" --no-delay
    
    echo ""
fi

# Step 2: Geolocate
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║  STEP 2/3: GEOLOCATING PEERS                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

python3 geolocate.py

echo ""

# Step 3: Visualize
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║  STEP 3/3: CREATING VISUALIZATION                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

python3 visualize.py --theme "$THEME" --all

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║  🎉 PIPELINE COMPLETE!                                                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════╣"
echo "║  Output:                                                                   ║"
echo "║    📦 Redis DB 1                     - All peer data stored                ║"
echo "║    🗺️  bitcoin_network_heatmap.html  - Interactive heatmap                 ║"
echo "║    🌐 bitcoin_network_globe.html     - 3D globe visualization              ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Open the HTML files in browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    open bitcoin_network_heatmap.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open bitcoin_network_heatmap.html
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    start bitcoin_network_heatmap.html
fi

