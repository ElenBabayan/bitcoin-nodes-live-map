const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

// Bitcoin Core RPC configuration
// Default: assumes bitcoin-cli is in PATH and uses default datadir
// If you have custom config, set BITCOIN_CLI_PATH or use -datadir flag
const BITCOIN_CLI_CMD = process.env.BITCOIN_CLI_PATH || 'bitcoin-cli';

// Get nodes from Bitcoin Core using bitcoin-cli
async function getNodesFromBitcoinCore() {
    try {
        console.log('Querying Bitcoin Core node for peer information...');
        
        // Get peer information using bitcoin-cli
        const { stdout, stderr } = await execAsync(`${BITCOIN_CLI_CMD} getpeerinfo`);
        
        if (stderr) {
            console.warn('bitcoin-cli stderr:', stderr);
        }
        
        const peerInfo = JSON.parse(stdout);
        
        if (!Array.isArray(peerInfo)) {
            throw new Error('Invalid response from bitcoin-cli getpeerinfo');
        }
        
        console.log(`Found ${peerInfo.length} connected peers`);
        
        // Extract node information
        const nodes = {};
        const seenIPs = new Set();
        
        peerInfo.forEach(peer => {
            // Extract IP address from addr field (format: "ip:port" or "ip")
            let ip = null;
            let port = 8333; // Default Bitcoin port
            
            if (peer.addr) {
                const parts = peer.addr.split(':');
                ip = parts[0];
                if (parts.length > 1) {
                    port = parseInt(parts[1]) || 8333;
                }
            } else if (peer.addrlocal) {
                // Fallback to local address
                const parts = peer.addrlocal.split(':');
                ip = parts[0];
            }
            
            // Skip if no valid IP or already seen
            if (!ip || seenIPs.has(ip)) {
                return;
            }
            
            // Skip IPv6 addresses (only want IPv4)
            if (ip.includes(':') || ip.startsWith('[')) {
                return;
            }
            
            // Skip .onion addresses
            if (ip.endsWith('.onion')) {
                return;
            }
            
            // Validate IPv4 format
            const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
            if (!ipv4Regex.test(ip)) {
                return;
            }
            
            const key = `${ip}:${port}`;
            nodes[key] = {
                version: peer.version ? peer.version.toString() : '70015'
            };
            seenIPs.add(ip);
        });
        
        console.log(`Extracted ${Object.keys(nodes).length} unique IPv4 nodes`);
        return nodes;
        
    } catch (error) {
        if (error.code === 'ENOENT') {
            throw new Error('bitcoin-cli not found. Please install Bitcoin Core and ensure bitcoin-cli is in your PATH.');
        }
        if (error.message.includes('Could not connect')) {
            throw new Error('Cannot connect to Bitcoin Core. Make sure bitcoind is running.');
        }
        if (error.message.includes('Authentication failed')) {
            throw new Error('Bitcoin Core RPC authentication failed. Check your ~/.bitcoin/bitcoin.conf or RPC credentials.');
        }
        throw new Error(`Error querying Bitcoin Core: ${error.message}`);
    }
}

// Express server
const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

let cachedNodes = null;
let lastFetch = 0;
const CACHE_DURATION = 30000; // 30 second cache (Bitcoin Core updates peers frequently)

app.get('/api/nodes', async (req, res) => {
    try {
        const now = Date.now();
        
        // Use cache if available and fresh
        if (cachedNodes && (now - lastFetch) < CACHE_DURATION) {
            return res.json({ nodes: cachedNodes });
        }
        
        console.log('Fetching nodes from Bitcoin Core...');
        const nodes = await getNodesFromBitcoinCore();
        
        cachedNodes = nodes;
        lastFetch = now;
        
        res.json({ nodes });
    } catch (error) {
        console.error('Error discovering nodes:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.listen(PORT, () => {
    console.log(`Bitcoin Node Discovery Server running on http://localhost:${PORT}`);
    console.log(`API endpoint: http://localhost:${PORT}/api/nodes`);
    console.log(`\nMake sure Bitcoin Core (bitcoind) is running and bitcoin-cli is accessible.`);
    console.log(`The server will query your local Bitcoin node for peer information.`);
});
