#!/usr/bin/env python3
"""
Simple Bitcoin network crawler using bitnodes-crawler's protocol library.
Connects directly to Bitcoin nodes to discover peers.
"""

import sys
import os
import json
import time
import socket
import logging
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add bitnodes-crawler to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bitnodes-crawler'))

try:
    from protocol import Connection, ProtocolError, ConnectionError
    from utils import new_redis_conn
except ImportError as e:
    logger.error(f"Could not import from bitnodes-crawler: {e}")
    logger.error("Make sure bitnodes-crawler directory exists")
    sys.exit(1)


class SimpleCrawler:
    """Simple crawler using bitnodes protocol implementation."""
    
    def __init__(self, max_nodes=1000):
        self.max_nodes = max_nodes
        self.discovered = set()
        self.visited = set()
        self.queue = deque()
        
        # DNS seeds
        self.seeds = [
            'seed.bitcoin.sipa.be',
            'dnsseed.bluematt.me',
            'dnsseed.bitcoin.dashjr.org',
            'seed.bitcoinstats.com',
            'seed.bitcoin.jonasschnelli.ch',
            'seed.btc.petertodd.org'
        ]
    
    def get_seed_nodes(self):
        """Get initial nodes from DNS seeds."""
        for seed in self.seeds:
            try:
                result = socket.getaddrinfo(seed, 8333, socket.AF_INET)
                for addr_info in result[:5]:
                    ip = addr_info[4][0]
                    self.discovered.add((ip, 8333))
                    self.queue.append((ip, 8333))
                    logger.info(f"Seed node: {ip}:8333")
            except Exception as e:
                logger.debug(f"Failed to resolve {seed}: {e}")
    
    def crawl_node(self, address):
        """Connect to a node and get its peers."""
        ip, port = address
        
        try:
            logger.info(f"Connecting to {ip}:{port}")
            
            conn = Connection(
                (ip, port),
                to_services=1,
                from_services=0,
                user_agent="/bitnodes-local-crawler:0.1/",
                height=0,
                relay=0
            )
            
            try:
                conn.open()
                logger.info(f"✓ Connected to {ip}:{port}")
                
                # Request addresses
                conn.getaddr(block=False)
                
                # Wait for addr response
                time.sleep(2)
                
                msgs = conn.get_messages(commands=[b"addr", b"addrv2"])
                
                new_peers = []
                for msg in msgs:
                    if msg.get('count', 0) > 0:
                        addrs = msg.get('addr_list', [])
                        for addr in addrs:
                            if isinstance(addr, tuple) and len(addr) >= 2:
                                peer_ip = addr[0]
                                peer_port = addr[1]
                                # Only IPv4 for now
                                if '.' in peer_ip and peer_port == 8333:
                                    new_peers.append((peer_ip, peer_port))
                
                if new_peers:
                    logger.info(f"  Got {len(new_peers)} peers from {ip}:{port}")
                    return new_peers
                else:
                    logger.debug(f"  No peers from {ip}:{port}")
                    return []
                
            finally:
                conn.close()
                
        except (ProtocolError, ConnectionError, socket.error, Exception) as e:
            logger.debug(f"Failed to connect to {ip}:{port}: {e}")
            return []
    
    def crawl(self):
        """Crawl the network."""
        logger.info("Starting crawl...")
        
        # Get seed nodes
        self.get_seed_nodes()
        logger.info(f"Starting with {len(self.queue)} seed nodes")
        
        # Crawl
        while self.queue and len(self.visited) < self.max_nodes:
            address = self.queue.popleft()
            
            if address in self.visited:
                continue
            
            self.visited.add(address)
            logger.info(f"Progress: {len(self.visited)}/{self.max_nodes} visited, {len(self.discovered)} discovered")
            
            new_peers = self.crawl_node(address)
            
            for peer in new_peers:
                if peer not in self.discovered:
                    self.discovered.add(peer)
                    if len(self.visited) + len(self.queue) < self.max_nodes:
                        self.queue.append(peer)
            
            # Small delay
            time.sleep(0.5)
        
        logger.info(f"Crawl complete: visited {len(self.visited)}, discovered {len(self.discovered)}")
    
    def export_json(self, filename):
        """Export discovered nodes to JSON."""
        peers = [
            {
                'ip': ip,
                'port': port,
                'address': f"{ip}:{port}"
            }
            for ip, port in sorted(self.discovered)
        ]
        
        data = {
            'total_discovered': len(peers),
            'total_visited': len(self.visited),
            'source': 'local-bitnodes-crawler',
            'peers': peers
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Exported {len(peers)} peers to {filename}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Simple Bitcoin network crawler using bitnodes protocol'
    )
    parser.add_argument('--max-nodes', type=int, default=100,
                       help='Maximum nodes to visit (default: 100)')
    parser.add_argument('--output', type=str, default='peers.json',
                       help='Output file (default: peers.json)')
    
    args = parser.parse_args()
    
    crawler = SimpleCrawler(max_nodes=args.max_nodes)
    crawler.crawl()
    crawler.export_json(args.output)
    
    print(f"\n{'='*60}")
    print(f"Crawl complete!")
    print(f"Visited: {len(crawler.visited)} nodes")
    print(f"Discovered: {len(crawler.discovered)} nodes")
    print(f"Output: {args.output}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

