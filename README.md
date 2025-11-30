# Bitcoin Node Heatmap Visualization

Visualizes the global distribution of Bitcoin nodes by creating an interactive heatmap. Gets node IPs from a local Bitcoin Core node using `bitcoin-cli` and displays them on an interactive world map.

## Requirements

- **Bitcoin Core** installed and running (`bitcoind`)
- **Node.js** 14.0 or higher
- Internet connection (for geolocation)

## How to Reproduce

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start Bitcoin Core:**
   ```bash
   bitcoind
   ```
   Wait for Bitcoin Core to sync and connect to peers (check with `bitcoin-cli getpeerinfo`).

3. **Start the backend server:**
   ```bash
   npm start
   ```

4. **Open the frontend:**
   - Open `bitcoin_nodes_live_map.html` in your web browser
   - The map will automatically fetch nodes from the backend and display them

## How It Works

- Backend queries local Bitcoin Core node using `bitcoin-cli getpeerinfo`
- Extracts IPv4 addresses from connected peers
- Frontend geolocates IPs and displays them on an interactive Leaflet map with heatmap overlay
- Auto-updates every 10 seconds

## Configuration

- `P2P_API_URL` in `app.js`: Backend API endpoint (default: "http://localhost:3000/api/nodes")
- `MAX_IPS` in `app.js`: Number of nodes to geolocate (default: 800)
- `UPDATE_INTERVAL` in `app.js`: Update frequency in milliseconds (default: 10000)
