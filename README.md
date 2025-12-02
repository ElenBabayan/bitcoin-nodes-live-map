# Bitcoin Nodes Live Map

Interactive heatmap visualization of all Bitcoin nodes online worldwide.

![Bitcoin Network Heatmap](https://img.shields.io/badge/Nodes-7,358-blue) ![Countries](https://img.shields.io/badge/Countries-98-green) ![Total Network](https://img.shields.io/badge/Total%20Network-24,000-orange)

## Overview

This project visualizes the global Bitcoin network by:
1. **Discovering Bitcoin nodes** using two methods (API or direct crawling)
2. **Geolocating nodes** using MaxMind GeoLite2-City database
3. **Creating an interactive heatmap** showing node concentration

Built using the official [bitnodes-crawler](https://github.com/ayeowch/bitnodes) protocol library.

## Quick Start

```bash
# 1. Clone bitnodes-crawler (includes GeoIP database)
git clone https://github.com/ayeowch/bitnodes.git bitnodes-crawler

# 2. Install dependencies
pip install -r requirements.txt

# 3. Fetch Bitcoin nodes (choose ONE method below)

## Method A: bitnodes.io API (Recommended - gets all 24,000 nodes)
python3 fetch_bitnodes.py --output peers.json

## Method B: Direct crawling (connects to real nodes, limited discovery)
python3 crawl_bitnodes.py --max-nodes 200 --output peers.json

# 4. Geolocate nodes (instant using MaxMind database)
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json

# 5. Create heatmap visualization
python3 visualize_peers_map.py --input peers_with_locations.json --output bitcoin_peers_map.html

# 6. Open in browser
open bitcoin_peers_map.html
```

## Results

- **24,000 total nodes** discovered from Bitcoin network
- **7,358 IPv4 nodes** geolocated and mapped
- **15,892 anonymous nodes** (Tor/I2P/CJDNS - cannot be geolocated)
- **98 countries** represented
- **Top countries**: USA (2,324), Germany (972), France (451)

## Two Approaches

### Method A: bitnodes.io API (Recommended)

**File:** `fetch_bitnodes.py`

- ✅ Gets complete network view (~24,000 nodes)
- ✅ Updated every 5 minutes
- ✅ Fast (instant download)
- ℹ️ Uses pre-crawled data from bitnodes.io's continuous crawling

**How it works:**
- bitnodes.io runs persistent crawler infrastructure 24/7
- Crawler connects to real Bitcoin nodes using P2P protocol
- API provides snapshot of discovered nodes
- Data represents actual node connections, just pre-collected

### Method B: Direct Crawling

**File:** `crawl_bitnodes.py`

- ✅ Connects directly to Bitcoin nodes
- ✅ Uses bitnodes-crawler protocol library
- ✅ Implements Bitcoin P2P protocol
- ⚠️ Limited peer discovery (~25 nodes from DNS seeds)

**Why limited discovery?**

Modern Bitcoin nodes prioritize privacy and security:
- Only share peer lists with trusted, long-established connections
- Ignore `getaddr` requests from new connections
- Prevents network mapping attacks and Eclipse attacks
- Our short-lived connections (2-5 seconds) aren't trusted

**What we successfully do:**
1. ✅ Query DNS seeds for initial nodes
2. ✅ Establish TCP connections
3. ✅ Complete Bitcoin handshake (version/verack)
4. ✅ Send `getaddr` messages
5. ❌ Nodes don't respond (privacy protection)

**Why bitnodes.io succeeds:**
- Maintains persistent connections (hours/days)
- Distributed crawler infrastructure
- Builds trust with nodes over time
- Multiple attempts and retry logic

## Project Structure

```
bitcoin-nodes-live-map/
├── fetch_bitnodes.py              # Fetch nodes from bitnodes.io API
├── crawl_bitnodes.py              # Direct P2P crawler (educational)
├── geolocate_maxmind.py           # Geolocate using MaxMind database
├── visualize_peers_map.py         # Create heatmap visualization
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── bitnodes-crawler/              # Official bitnodes protocol library
│   └── geoip/                     # MaxMind GeoLite2 databases
├── peers.json                     # Discovered nodes (generated)
├── peers_with_locations.json      # Geolocated nodes (generated)
└── bitcoin_peers_map.html         # Final heatmap (generated)
```

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

## Command Reference

### Fetch Nodes (API)
```bash
python3 fetch_bitnodes.py --output peers.json
```

### Crawl Nodes (Direct)
```bash
python3 crawl_bitnodes.py --max-nodes 100 --output peers.json
```
Options:
- `--max-nodes N` - Maximum nodes to visit (default: 1000)
- `--output FILE` - Output file (default: peers.json)

### Geolocate
```bash
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json
```
Options:
- `--input FILE` - Input peers file
- `--output FILE` - Output with locations
- `--db PATH` - Path to GeoLite2-City.mmdb

### Visualize
```bash
python3 visualize_peers_map.py --input peers_with_locations.json --output map.html
```
Options:
- `--input FILE` - Input geolocated peers
- `--output FILE` - Output HTML map
- `--no-heatmap` - Disable heatmap (markers only)

## References

- [bitnodes.io](https://bitnodes.io/) - Bitcoin network crawler
- [bitnodes-crawler GitHub](https://github.com/ayeowch/bitnodes) - Crawler source code
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) - Free IP geolocation
- [Bitcoin P2P Protocol](https://en.bitcoin.it/wiki/Protocol_documentation) - Protocol specification
- [Folium Documentation](https://python-visualization.github.io/folium/) - Python mapping library

