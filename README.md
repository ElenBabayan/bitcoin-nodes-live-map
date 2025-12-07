# 🌍 Bitcoin Nodes Live Map

Interactive heatmap visualization of Bitcoin nodes worldwide, showing the real-time geographic distribution of the Bitcoin network.

**Deployment:** https://seto-y.github.io/blockchain_project/

![Bitcoin Network Heatmap](https://img.shields.io/badge/Nodes-7,358-blue) ![Countries](https://img.shields.io/badge/Countries-98-green) ![Total Network](https://img.shields.io/badge/Total%20Network-24,000-orange)

## 📖 Overview

This project creates beautiful visualizations of the global Bitcoin network through a three-step process:

1. **🔍 Node Discovery** - Fetch Bitcoin nodes via API or direct P2P crawling
2. **📍 Geolocation** - Map IP addresses to coordinates using MaxMind GeoLite2-City
3. **🗺️ Visualization** - Generate interactive heatmaps with node clusters

### 🅰️ Approach A: API-Based (Simple & Fast)

**📁 Location:** Root directory  
**👤 Best for:** Quick network overview, beginners, production use

#### What's Included

| File | Purpose |
|------|---------|
| `fetch_bitnodes.py` | Fetch nodes from bitnodes.io API |
| `crawl_bitnodes.py` | Educational P2P crawler |
| `geolocate_maxmind.py` | MaxMind database geolocation |
| `visualize_peers_map.py` | Generate interactive heatmap |

#### Quick Start

```bash
# Automated (recommended)
./run_pipeline.sh
```

#### (Alternative) Detailed Installation Steps (If you prefer to run manually)

```bash
# Step 1: Clone bitnodes-crawler (includes GeoIP databases)
git clone https://github.com/ayeowch/bitnodes.git bitnodes-crawler

# Step 2: Install Python dependencies
pip3 install -r requirements.txt

# Step 3: Fetch Bitcoin nodes (choose one method)
# Option 1: API fetch (recommended - gets ~24,000 nodes instantly)
python3 fetch_bitnodes.py --output peers.json
# Option 2: Direct P2P crawl (educational - limited discovery)
python3 crawl_bitnodes.py --max-nodes 200 --output peers.json

# Step 4: Geolocate IP addresses
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json

# Step 5: Generate visualization
python3 visualize_peers_map.py --input peers_with_locations.json --output bitcoin_peers_map.html

# Step 6: View the map
open bitcoin_peers_map.html  # macOS
# xdg-open bitcoin_peers_map.html  # Linux
# start bitcoin_peers_map.html  # Windows
```

#### Key Features

- ✅ **Complete network view** - ~24,000 mainnet nodes
- ✅ **Real-time data** - Updated every 5 minutes
- ✅ **Instant results** - No waiting for crawls
- ✅ **Zero dependencies** - No database setup
- ℹ️ Uses bitnodes.io's 24/7 crawler infrastructure

**How It Works:**
1. bitnodes.io runs persistent P2P crawlers connecting to real Bitcoin nodes
2. API provides snapshots of discovered nodes
3. You get authentic network data without running your own crawler

---

### 🅱️ Approach B: Custom Crawler (Advanced Analytics)

**📁 Location:** `custom_crawler/` directory  
**👤 Best for:** Developers, custom crawling, real-time analytics

#### What's Included

| File | Purpose |
|------|---------|
| `crawler.py` | Async P2P crawler (500+ concurrent connections) |
| `database.py` | Redis storage engine |
| `geolocate.py` | Real-time MaxMind geolocation |
| `visualize.py` | Advanced visualizations (heatmap + 3D globe) |
| `run_pipeline.sh` | Automated execution pipeline |

#### Quick Start

```bash
cd custom_crawler

# 1. Start Redis server
redis-server --daemonize yes

# 2. Install dependencies
pip3 install redis requests geoip2 folium

# 3. Run crawler (choose scale)

# Small test: 1,000 nodes (~2-3 minutes)
./run_pipeline.sh --target 1000 --concurrency 200 --theme bitcoin

# Medium: 10,000 nodes (~15-20 minutes)
./run_pipeline.sh --target 10000 --concurrency 300 --theme bitcoin

# Large: 100,000 nodes (~1-2 hours)
./run_pipeline.sh --target 100000 --concurrency 500 --theme cyber

# 4. View results
open bitcoin_network_heatmap.html
```

#### Key Features

- ✅ **Redis-backed** - Ultra-fast storage (100K+ ops/sec)
- ✅ **Async architecture** - 500+ parallel connections
- ✅ **Real-time discovery** - Direct P2P protocol implementation
- ✅ **Instant geolocation** - Local MaxMind lookups
- ✅ **Advanced analytics** - Redis query capabilities
- ⚠️ **Bitcoin Testnet** - Uses testnet (not mainnet)

## Technical Details

### Custom Crawler – Short Breakdown

• **Bitcoin P2P Protocol**  
Implemented VERSION/VERACK/GETADDR/ADDR logic from scratch using testnet magic bytes and full message framing (headers, checksum, varint, etc.).

• **High-Concurrency Networking**  
Used asyncio with 200+ parallel connections, strict timeouts, and filtering of private/unreachable IPs.

• **Crawl Logic**  
Seed → handshake → GETADDR → extract ~1000 peers → dedupe → continue until ~20K nodes.

• **Storage & Scaling**  
Redis for fast "seen IP" checks; stored metadata (IP, port, user agent, protocol version) and exported to SQLite.

• **Data Pipeline**  
Crawler → Redis → SQLite → MaxMind geolocation → Folium heatmap.

### Bitcoin P2P Protocol

Both approaches use the Bitcoin P2P protocol:
- **Protocol version:** 70016
- **User agent:** `/bitnodes-local-crawler:0.1/`
- **Messages:** version, verack, getaddr, addr
- **Default port:** 8333

### Geolocation

Uses MaxMind GeoLite2-City database:
- **Database:** Included in bitnodes-crawler/geoip/
- **Speed:** Instant (local lookups)
- **Accuracy:** City-level precision
- **Coverage:** ~32% of nodes (IPv4 only)

### Why Only 32% Geolocated?

Out of 24,000 total nodes:
- **7,358 (32%)** - IPv4 nodes with public IPs → ✅ Geolocated
- **15,892 (68%)** - Anonymous nodes:
  - ~15,000 Tor (.onion addresses)
  - ~1,000 I2P nodes
  - ~400 CJDNS nodes
  - These are intentionally anonymous and cannot be mapped

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Command not found** | Use `python3` and `pip3` instead of `python`/`pip` |
| **Permission denied** | Run `pip3 install --user -r requirements.txt` |
| **Redis errors** | Safe to ignore - not needed for Approach A |
| **Module not found** | Reinstall: `pip3 install -r requirements.txt` |
| **GeoIP database missing** | Clone bitnodes-crawler: `git clone https://github.com/ayeowch/bitnodes.git bitnodes-crawler` |
