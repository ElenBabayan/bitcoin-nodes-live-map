# Bitcoin Node Heatmap Visualization

This project visualizes the global distribution of Bitcoin nodes by creating an interactive heatmap. It uses `bitcoin-cli` to query an actual Bitcoin Core node running on your machine to retrieve the IP addresses of all connected peer nodes. The backend server executes `bitcoin-cli getpeerinfo` to get real-time peer information from local `bitcoind` instance.

## Setup

Initially, run these two commands:

```bash
npm install
brew install bitcoin
```

## Running the Project

After setup, run these two commands in **2 different terminals**:

**Terminal 1:**
```bash
bitcoind
```

**Terminal 2:**
```bash
npm start
```

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
