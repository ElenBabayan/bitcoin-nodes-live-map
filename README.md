# 🌍 Bitcoin Nodes Live Map

Interactive heatmap visualization of Bitcoin nodes worldwide, showing the real-time geographic distribution of the Bitcoin network.

![Bitcoin Network Heatmap](https://img.shields.io/badge/Nodes-7,358-blue) ![Countries](https://img.shields.io/badge/Countries-98-green) ![Total Network](https://img.shields.io/badge/Total%20Network-24,000-orange)

## 📖 Overview

This project creates beautiful visualizations of the global Bitcoin network through a three-step process:

1. **🔍 Node Discovery** - Fetch Bitcoin nodes via API or direct P2P crawling
2. **📍 Geolocation** - Map IP addresses to coordinates using MaxMind GeoLite2-City
3. **🗺️ Visualization** - Generate interactive heatmaps with node clusters

Built on the official [bitnodes-crawler](https://github.com/ayeowch/bitnodes) protocol library.

## 🚀 Quick Start

**Choose your approach:**
- **🅰️ Approach A** - Easiest, instant results, mainnet data (see below)
- **🅱️ Approach B** - Advanced, custom crawling, testnet (see below)

For most users, start with **Approach A** using the one-command setup:

```bash
./run_pipeline.sh
```

For detailed instructions, see [Approach A](#️-approach-a-api-based-simple--fast) or [Approach B](#️-approach-b-custom-crawler-advanced-analytics) sections below.

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Command not found** | Use `python3` and `pip3` instead of `python`/`pip` |
| **Permission denied** | Run `pip3 install --user -r requirements.txt` |
| **Redis errors** | Safe to ignore - not needed for Approach A |
| **Module not found** | Reinstall: `pip3 install -r requirements.txt` |
| **GeoIP database missing** | Clone bitnodes-crawler: `git clone https://github.com/ayeowch/bitnodes.git bitnodes-crawler` |

## 📊 Network Statistics

The latest crawl discovered:

- **24,000 total nodes** across the Bitcoin network
- **7,358 IPv4 nodes** successfully geolocated (32%)
- **15,892 anonymous nodes** (Tor/I2P/CJDNS - cannot be mapped)
- **98 countries** represented globally

**Top 3 Countries by Node Count:**
1. 🇺🇸 USA - 2,324 nodes
2. 🇩🇪 Germany - 972 nodes  
3. 🇫🇷 France - 451 nodes

## 🔀 Two Approaches

This project offers two distinct methods for visualizing Bitcoin nodes:

---

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

#### Detailed Installation

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

#### Manual Execution

```bash
cd custom_crawler

# Crawl the network
python3 crawler.py --target 1000 --concurrency 200 --no-delay

# Geolocate discovered peers
python3 geolocate.py

# Generate visualization
python3 visualize.py --theme bitcoin
```

#### Visualization Themes

```bash
# Bitcoin orange/gold aesthetic
python3 visualize.py --theme bitcoin

# Cyberpunk purple/pink vibes
python3 visualize.py --theme cyber

# Neon blue/teal matrix
python3 visualize.py --theme neon
```

---

**💡 Recommendation:**
- **First-time users** → Start with **Approach A** for simplicity
- **Developers/Researchers** → Use **Approach B** for custom crawling
- **Data analytics** → **Approach B** with Redis query capabilities
- **Production dashboards** → **Approach A** for reliable mainnet data

## Dependencies

```
requests>=2.28.0    # For API calls
folium>=0.14.0      # For map visualization  
geoip2>=4.8.1       # For MaxMind database
```

Install all: `pip install -r requirements.txt`

## Heatmap Features

- **🔥 Heatmap layer** - Shows node concentration (red = high, blue = low)
- **📍 Marker clusters** - Click to expand and see individual nodes
- **🗺️ Multiple tile layers** - OpenStreetMap, CartoDB dark/light
- **📊 Statistics panel** - Top countries by node count
- **ℹ️ Node details** - Click markers for IP, location, ISP info
- **🔄 Layer control** - Toggle between heatmap and markers

## Technical Details

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

## References

- [bitnodes.io](https://bitnodes.io/) - Bitcoin network crawler
- [bitnodes-crawler GitHub](https://github.com/ayeowch/bitnodes) - Crawler source code
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) - Free IP geolocation
- [Bitcoin P2P Protocol](https://en.bitcoin.it/wiki/Protocol_documentation) - Protocol specification
- [Folium Documentation](https://python-visualization.github.io/folium/) - Python mapping library

