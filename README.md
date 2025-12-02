# Bitcoin Nodes Live Map

Interactive heatmap visualization of all Bitcoin nodes online worldwide.

![Bitcoin Network Heatmap](https://img.shields.io/badge/Nodes-7,358-blue) ![Countries](https://img.shields.io/badge/Countries-98-green) ![Total Network](https://img.shields.io/badge/Total%20Network-24,000-orange)

## Overview

This project visualizes the global Bitcoin network by:
1. **Discovering Bitcoin nodes** using the bitnodes.io API
2. **Geolocating nodes** using MaxMind GeoLite2-City database
3. **Creating an interactive heatmap** showing node concentration

Data from [bitnodes.io](https://bitnodes.io/) - a Bitcoin network crawler that monitors the network 24/7.

## Quick Start

### One-Command Run (Easiest)

```bash
./run_pipeline.sh
```

This script automatically:
- Detects Python (python3 or python)
- Installs dependencies if needed
- Runs all 3 steps (fetch → geolocate → visualize)
- Opens the map in your browser

### Manual Steps

```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Fetch Bitcoin nodes from bitnodes.io API
python3 fetch_bitnodes.py --output peers.json

# 3. Geolocate nodes (instant using MaxMind database)
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json

# 4. Create heatmap visualization
python3 visualize_peers_map.py --input peers_with_locations.json --output bitcoin_peers_map.html

# 5. Open in browser
open bitcoin_peers_map.html
```

## Troubleshooting

**Command not found errors?** Use `python3` and `pip3` instead of `python` and `pip` (common on macOS/Linux)

**Permission denied?** Use `pip3 install --user -r requirements.txt`

**Redis errors?** Ignore them - not needed for our scripts

**Module not found?** Run `pip3 install -r requirements.txt` again

## Results

- **24,000 total nodes** discovered from Bitcoin network
- **7,358 IPv4 nodes** geolocated and mapped
- **15,892 anonymous nodes** (Tor/I2P/CJDNS - cannot be geolocated)
- **98 countries** represented
- **Top countries**: USA (2,324), Germany (972), France (451)

## How It Works

**Data Source:** bitnodes.io API

**File:** `fetch_bitnodes.py`

- ✅ Gets complete network view (~24,000 nodes)
- ✅ Updated every 5 minutes
- ✅ Fast (instant download)
- ℹ️ Uses pre-crawled data from bitnodes.io's continuous crawling

**Behind the scenes:**
- bitnodes.io runs persistent crawler infrastructure 24/7
- Crawler connects to real Bitcoin nodes using P2P protocol
- API provides snapshot of discovered nodes
- Data represents actual node connections, just pre-collected

Modern Bitcoin nodes prioritize privacy and security, making direct crawling difficult:
- Nodes only share peer lists with trusted, long-established connections
- They ignore `getaddr` requests from new connections to prevent network mapping attacks
- bitnodes.io succeeds by maintaining persistent connections and distributed infrastructure

## Project Structure

```
bitcoin-nodes-live-map/
├── fetch_bitnodes.py              # Fetch nodes from bitnodes.io API
├── geolocate_maxmind.py           # Geolocate using MaxMind database
├── visualize_peers_map.py         # Create heatmap visualization
├── requirements.txt               # Python dependencies
├── run_pipeline.sh                # One-command script to run everything
├── README.md                      # This file
├── geoip/                         # MaxMind GeoLite2 database
│   └── GeoLite2-City.mmdb         # IP geolocation database (60MB)
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

### Geolocation

Uses MaxMind GeoLite2-City database:
- **Database:** Included in geoip/GeoLite2-City.mmdb
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

- [bitnodes.io](https://bitnodes.io/) - Bitcoin network crawler and data source
- [bitnodes.io API](https://bitnodes.io/api/) - Public API for Bitcoin network data
- [MaxMind GeoLite2](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data) - Free IP geolocation
- [Folium Documentation](https://python-visualization.github.io/folium/) - Python mapping library
- [Bitcoin P2P Protocol](https://en.bitcoin.it/wiki/Protocol_documentation) - Protocol specification

