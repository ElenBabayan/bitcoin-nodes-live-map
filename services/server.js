const { exec } = require('child_process');
const { promisify } = require('util');
const path = require('path');
const execAsync = promisify(exec);

const PYTHON_CRAWLER_PATH = path.join(__dirname, 'bitcoin_crawler.py');
const MAX_NODES_TO_DISCOVER = parseInt(process.env.MAX_NODES) || 1000;
const PYTHON_CMD = process.env.PYTHON_CMD || 'python3';

/**
 * Discover Bitcoin nodes using Python P2P network crawler
 * 
 * This function uses a Python Bitcoin P2P crawler (similar to bitnodes-crawler) that:
 * 1. Connects to Bitcoin DNS seeds to get initial nodes
 * 2. Performs Bitcoin P2P protocol handshake with each node
 * 3. Requests peer addresses using getaddr messages
 * 4. Recursively crawls discovered peers to build a network map
 * 
 * This approach discovers ALL reachable nodes in the Bitcoin network,
 * not just the peers connected to a local bitcoind instance.
 * 
 * Uses Python implementation similar to bitnodes-crawler approach.
 */
async function getNodesFromBitcoinNetwork() {
    try {
        const timestamp = new Date().toISOString();
        console.log(`[${timestamp}] Starting Bitcoin P2P network crawl using Python crawler...`);
        console.log(`[${timestamp}] This will discover nodes across the entire Bitcoin network`);
        
        const command = `${PYTHON_CMD} "${PYTHON_CRAWLER_PATH}" --max-nodes ${MAX_NODES_TO_DISCOVER} --timeout 30`;
        const { stdout, stderr } = await execAsync(command, {
            maxBuffer: 10 * 1024 * 1024, // 10MB buffer for large responses
            timeout: 60000 // 60 second timeout
        });
        
        if (stderr) {
            // Python crawler writes progress to stderr, which is fine
            console.log(stderr);
        }
        
        const result = JSON.parse(stdout);
        const nodes = result.nodes || {};
        
        console.log(`[${new Date().toISOString()}] Discovered ${Object.keys(nodes).length} unique Bitcoin nodes`);
        return nodes;
        
    } catch (error) {
        if (error.code === 'ENOENT') {
            throw new Error(`Python not found. Please install Python 3 and ensure '${PYTHON_CMD}' is in your PATH.`);
        }
        if (error.message.includes('JSON')) {
            throw new Error(`Error parsing crawler output: ${error.message}. Make sure Python crawler is working correctly.`);
        }
        console.error(`[${new Date().toISOString()}] Error crawling Bitcoin network:`, error);
        throw new Error(`Error crawling Bitcoin network: ${error.message}`);
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
        console.log(`[${requestTime}] API Request: Starting Bitcoin P2P network crawl...`);
        const nodes = await getNodesFromBitcoinNetwork();
        
        res.json({ 
            nodes,
            timestamp: requestTime,
            source: 'python-bitcoin-crawler',
            method: 'P2P protocol crawl (getaddr messages) - Python implementation similar to bitnodes-crawler'
        });
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
    console.log(`\nThe server uses a Python Bitcoin P2P network crawler to discover nodes.`);
    console.log(`It connects directly to Bitcoin nodes using the P2P protocol and getaddr messages.`);
    console.log(`Implementation is similar to bitnodes-crawler (Python-based).`);
    console.log(`No local Bitcoin Core installation is required.`);
    console.log(`\nMax nodes to discover: ${MAX_NODES_TO_DISCOVER} (set via MAX_NODES env var)`);
    console.log(`Python command: ${PYTHON_CMD}`);
});
