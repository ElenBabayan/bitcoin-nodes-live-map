# Bitcoin Node Heatmap Visualization

This project visualizes the global distribution of Bitcoin nodes by creating an interactive heatmap. It uses a **Python Bitcoin P2P network crawler** (similar to bitnodes-crawler) to discover nodes across the entire Bitcoin network by directly connecting to nodes using the Bitcoin P2P protocol and requesting peer addresses via `getaddr` messages.

## Setup

### Prerequisites

1. **Node.js** (for the web server)
2. **Python 3** (for the Bitcoin crawler)

### Installation

1. Install Node.js dependencies:
```bash
npm install
```

2. **No additional Python packages required!** The Python crawler uses only the standard library (similar to bitnodes-crawler approach).

**No Bitcoin Core installation required!** The crawler connects directly to the Bitcoin network.

## Running the Project

Simply run:

```bash
npm start
```

Then open the map visualization in your browser.

## How It Works

- **Backend uses a Python Bitcoin P2P crawler** (similar to bitnodes-crawler) that:
  1. Connects to Bitcoin DNS seeds to get initial nodes
  2. Performs Bitcoin P2P protocol handshake with each node
  3. Sends `getaddr` messages to request peer addresses
  4. Recursively crawls discovered peers to build a comprehensive network map
- Discovers **all reachable nodes** in the Bitcoin network (not just local peers)
- Extracts IPv4 addresses from discovered nodes
- Frontend geolocates IPs and displays them on an interactive Leaflet map with heatmap overlay

The Python crawler directly implements the Bitcoin P2P protocol (similar to the open-source bitnodes-crawler project), using only Python standard library - no external dependencies required.

## Configuration

- `P2P_API_URL` in `app.js`: Backend API endpoint (default: "http://localhost:3000/api/nodes")
- `MAX_IPS` in `app.js`: Number of nodes to geolocate (default: 800)
- `UPDATE_INTERVAL` in `app.js`: Update frequency in milliseconds (default: 10000)
- `MAX_NODES` environment variable: Maximum nodes to discover during crawl (default: 1000)

## Technical Details

The Python crawler (`services/bitcoin_crawler.py`) implements the Bitcoin P2P protocol:
- Uses Bitcoin mainnet magic bytes (`0xf9beb4d9`)
- Protocol version 70015
- Sends `version`, `verack`, and `getaddr` messages
- Parses `addr` responses to extract peer information
- Recursively crawls the network starting from DNS seeds
- Uses only Python standard library (no external dependencies)

This implementation is similar to:
- [bitnodes-crawler](https://github.com/ayeowch/bitnodes) (Python, open source)
- [bitnodes.io](https://bitnodes.io/) (web service)

The advantage over `bitcoin-cli getpeerinfo` is that it discovers **all reachable nodes** in the network, not just the peers connected to a single local node.

### Python Configuration

- Default Python command: `python3` (set via `PYTHON_CMD` environment variable)
- The crawler script is located at: `services/bitcoin_crawler.py`
- You can run it directly: `python3 services/bitcoin_crawler.py --max-nodes 1000`
