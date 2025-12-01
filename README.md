# Bitcoin Node Heatmap Visualization

Visualizes the global distribution of Bitcoin nodes by creating an interactive heatmap. 

**This project uses `bitcoin-cli` to query an actual Bitcoin Core node** running on your machine to retrieve the IP addresses of all connected peer nodes. The backend server executes `bitcoin-cli getpeerinfo` to get real-time peer information from your local `bitcoind` instance.

## Requirements

- **Bitcoin Core** installed and running (`bitcoind`)
- **Node.js** 14.0 or higher
- Internet connection (for geolocation)

## Installing Bitcoin Core

### macOS (using Homebrew):
```bash
brew install bitcoin
```

### macOS (Manual):
1. Download from: https://bitcoincore.org/en/download/
2. Extract and move `bitcoin-cli` to your PATH or use full path

### After Installation:
1. Start Bitcoin Core: `bitcoind`
2. Wait for initial sync (this can take hours/days for full sync)
3. Once connected to peers, you can test with: `bitcoin-cli getpeerinfo`

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

- **Backend uses `bitcoin-cli getpeerinfo`** to query your local Bitcoin Core node (`bitcoind`)
- Extracts IPv4 addresses from all connected peers
- Frontend geolocates IPs and displays them on an interactive Leaflet map with heatmap overlay
- Auto-updates every 10 seconds (optional - you can take a single screenshot instead)

## Getting IP Addresses for Screenshot

To get a simple list of IP addresses retrieved via `bitcoin-cli`:

1. Start the server: `npm start`
2. Visit: `http://localhost:3000/api/ips`
3. This will show all IP addresses retrieved from your Bitcoin node using `bitcoin-cli getpeerinfo`

## Configuration

- `P2P_API_URL` in `app.js`: Backend API endpoint (default: "http://localhost:3000/api/nodes")
- `MAX_IPS` in `app.js`: Number of nodes to geolocate (default: 800)
- `UPDATE_INTERVAL` in `app.js`: Update frequency in milliseconds (default: 10000)
