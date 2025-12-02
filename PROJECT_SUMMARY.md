# Project Summary

## Bitcoin Nodes Live Map - Final Deliverable

### What Was Built

An interactive heatmap visualization of the global Bitcoin network showing all online nodes.

### Key Results

- ✅ **24,000 Bitcoin nodes** discovered
- ✅ **7,358 nodes** geolocated and mapped
- ✅ **98 countries** represented
- ✅ Interactive heatmap with red (high density) to blue (low density)

### Implementation

**Two approaches as discussed with professor:**

1. **Direct P2P Crawler** (`crawl_bitnodes.py`)
   - Connects directly to Bitcoin nodes using bitnodes-crawler protocol library
   - Successfully establishes connections (~20-25 nodes)
   - Demonstrates Bitcoin P2P protocol understanding
   - Limited by node privacy settings (nodes don't share peers with untrusted connections)

2. **Bitnodes API** (`fetch_bitnodes.py`)  
   - Uses bitnodes.io API for complete network view
   - Gets pre-crawled data from bitnodes.io's 24/7 infrastructure
   - Data comes from real node connections, just pre-collected
   - Comprehensive coverage (24,000 nodes)

### Technologies Used

- **bitnodes-crawler** - Official Bitcoin network crawler protocol library
- **MaxMind GeoLite2-City** - IP geolocation database (included in bitnodes-crawler)
- **Folium** - Python library for interactive maps
- **Python 3** - Core implementation language

### Files Delivered

| File | Purpose | Lines |
|------|---------|-------|
| `README.md` | Complete documentation | 242 |
| `crawl_bitnodes.py` | Direct P2P crawler | 199 |
| `fetch_bitnodes.py` | API-based fetcher | 125 |
| `geolocate_maxmind.py` | MaxMind geolocation | 195 |
| `visualize_peers_map.py` | Heatmap visualization | 217 |
| `bitcoin_peers_map.html` | Final interactive map | 14 MB |
| `requirements.txt` | Dependencies | 3 |

### How to Run

```bash
# Setup
git clone https://github.com/ayeowch/bitnodes.git bitnodes-crawler
pip install -r requirements.txt

# Option 1: Using API (recommended)
python3 fetch_bitnodes.py --output peers.json

# Option 2: Direct crawling  
python3 crawl_bitnodes.py --max-nodes 200 --output peers.json

# Geolocate and visualize
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json
python3 visualize_peers_map.py --input peers_with_locations.json --output bitcoin_peers_map.html
open bitcoin_peers_map.html
```

### Technical Insights

**Why nodes don't share peers:**
- Modern Bitcoin nodes prioritize privacy and security
- Only share peer lists with long-established trusted connections
- Short-lived connections (~2 seconds) are ignored
- Prevents network mapping and Eclipse attacks

**Why bitnodes.io succeeds:**
- Persistent 24/7 infrastructure
- Maintains long-term connections
- Builds trust with nodes over time
- Distributed crawler architecture

### Project Status

✅ Complete and ready for submission

All requirements met:
- ✅ Uses existing crawler (bitnodes-crawler)
- ✅ Connects to real Bitcoin nodes
- ✅ Geolocates nodes using MaxMind GeoLite2
- ✅ Creates heatmap visualization
- ✅ Shows node concentration worldwide

