# Bitcoin Peer Crawler

Gets all peers of a given Bitcoin node using open-source crawlers.

## Important Note

**Bitcoin CLI does NOT expose an API to list peers of a given node.** You cannot connect to a random node and ask for its peers from a command line interface. 

This project uses open-source Bitcoin crawlers:
- **bitnodes-crawler** (open source, same idea as bitnodes.io)
- **python-bitcoinlib** (for Bitcoin protocol utilities)

## Installation

1. Install Python 3.7 or higher

2. Install bitnodes-crawler:
```bash
git clone https://github.com/ayeowch/bitnodes.git
cd bitnodes
pip install -r requirements.txt
```

3. Install python-bitcoinlib (optional, for additional utilities):
```bash
pip install python-bitcoinlib
```

## Usage

### Using bitnodes-crawler

**Option 1: Run bitnodes-crawler directly**
```bash
cd bitnodes
python crawler.py
```

**Option 2: Use this wrapper script**
```bash
# If bitnodes is in the current directory or home directory:
python3 bitcoin_peer_crawler.py

# Or specify the path:
python3 bitcoin_peer_crawler.py --bitnodes-path /path/to/bitnodes

# Show installation instructions:
python3 bitcoin_peer_crawler.py --install-instructions
```

## How It Works

1. **bitnodes-crawler**: Crawls the Bitcoin network by sending `getaddr` messages recursively to discover all reachable nodes, similar to bitnodes.io
2. **python-bitcoinlib**: Provides Bitcoin protocol utilities and network parameter selection

## Output

The crawler will output discovered peers. Check the bitnodes directory for results.

## References

- [bitnodes-crawler GitHub](https://github.com/ayeowch/bitnodes)
- [bitnodes.io](https://bitnodes.io/)
- [python-bitcoinlib](https://github.com/petertodd/python-bitcoinlib)
- [Bitcoin P2P Protocol](https://en.bitcoin.it/wiki/Protocol_documentation)

## Why Not Bitcoin CLI?

Bitcoin Core's `bitcoin-cli` does NOT provide an API to:
- Connect to a random node
- Ask that node for its list of peers

You can only get peers from your **own local node** using:
```bash
bitcoin-cli getpeerinfo  # Only works with YOUR local node
```

To crawl the network and discover peers from any node, you need to use crawlers like bitnodes-crawler that implement the Bitcoin P2P protocol.
