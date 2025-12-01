const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);

const BITCOIN_CLI_CMD = process.env.BITCOIN_CLI_PATH || 'bitcoin-cli';

async function getNodesFromBitcoinCore() {
    try {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] Querying Bitcoin Core node using: ${BITCOIN_CLI_CMD} getpeerinfo`);
        
        const { stdout, stderr } = await execAsync(`${BITCOIN_CLI_CMD} getpeerinfo`);
        
        if (stderr) {
            console.warn('bitcoin-cli stderr:', stderr);
        }
        
        const peerInfo = JSON.parse(stdout);
        
        if (!Array.isArray(peerInfo)) {
            throw new Error('Invalid response from bitcoin-cli getpeerinfo');
        }
        
        console.log(`[${new Date().toISOString()}] Found ${peerInfo.length} connected peers from Bitcoin Core`);
        
        const nodes = {};
        const seenIPs = new Set();
        
        peerInfo.forEach(peer => {
            let ip = null;
            let port = 8333;
            
            if (peer.addr) {
                const parts = peer.addr.split(':');
                ip = parts[0];
                if (parts.length > 1) {
                    port = parseInt(parts[1]) || 8333;
                }
            } else if (peer.addrlocal) {
                const parts = peer.addrlocal.split(':');
                ip = parts[0];
            }
            
            if (!ip || seenIPs.has(ip)) {
                return;
            }
            
            if (ip.includes(':') || ip.startsWith('[')) {
                return;
            }
            
            if (ip.endsWith('.onion')) {
                return;
            }
            
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
        
        console.log(`[${new Date().toISOString()}] Extracted ${Object.keys(nodes).length} unique IPv4 nodes at this moment`);
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

const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

app.get('/api/nodes', async (req, res) => {
    try {
        const requestTime = new Date().toISOString();
        console.log(`[${requestTime}] API Request: Fetching live nodes from Bitcoin Core at this exact moment...`);
        const nodes = await getNodesFromBitcoinCore();
        
        res.json({ 
            nodes,
            timestamp: requestTime,
            source: 'bitcoin-cli getpeerinfo'
        });
    } catch (error) {
        console.error('Error discovering nodes:', error);
        res.status(500).json({ error: error.message });
    }
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.get('/api/ips', async (req, res) => {
    try {
        const requestTime = new Date().toISOString();
        console.log(`[${requestTime}] API Request: Fetching live IP addresses from Bitcoin Core at this exact moment...`);
        const nodes = await getNodesFromBitcoinCore();
        const ips = Object.keys(nodes).map(key => {
            const lastColon = key.lastIndexOf(':');
            return lastColon !== -1 ? key.substring(0, lastColon) : key;
        });
        res.json({ 
            total: ips.length,
            ips: ips.sort(),
            timestamp: requestTime,
            source: 'bitcoin-cli getpeerinfo',
            note: 'These IPs were retrieved in real-time using bitcoin-cli getpeerinfo from your local Bitcoin Core node at the moment of this request'
        });
    } catch (error) {
        console.error('Error getting IPs:', error);
        res.status(500).json({ error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`Bitcoin Node Discovery Server running on http://localhost:${PORT}`);
    console.log(`API endpoint: http://localhost:${PORT}/api/nodes`);
    console.log(`IP list endpoint: http://localhost:${PORT}/api/ips`);
    console.log(`\nMake sure Bitcoin Core (bitcoind) is running and bitcoin-cli is accessible.`);
    console.log(`The server uses bitcoin-cli getpeerinfo to query your local Bitcoin node for peer information.`);
});
