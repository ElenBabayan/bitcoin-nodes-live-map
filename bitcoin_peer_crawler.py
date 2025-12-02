#!/usr/bin/env python3
"""
Bitcoin Peer Crawler using python-bitcoinlib
Gets all peers of Bitcoin nodes by crawling the network.

Note: Bitcoin CLI does NOT expose an API to list peers of a given node.
You cannot connect to a random node and ask for its peers via CLI.

This script uses python-bitcoinlib to implement a crawler that:
- Connects to Bitcoin nodes using P2P protocol
- Sends getaddr messages to discover peers
- Iteratively crawls discovered peers to build a network map

Requirements:
- python-bitcoinlib: pip install python-bitcoinlib
"""

import asyncio
import socket
import struct
import time
import json
import random
from typing import Set, List, Dict, Optional
from collections import deque
import logging

# Import python-bitcoinlib
try:
    from bitcoin import SelectParams
    from bitcoin.net import CAddress
    BITCOINLIB_AVAILABLE = True
except ImportError:
    BITCOINLIB_AVAILABLE = False
    print("Error: python-bitcoinlib is required.")
    print("Install it with: pip install python-bitcoinlib")
    exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BitcoinPeerCrawler:
    """Crawls Bitcoin network to discover peers using python-bitcoinlib."""
    
    # Bitcoin network magic bytes
    MAINNET_MAGIC = 0xD9B4BEF9
    TESTNET_MAGIC = 0x0709110B
    
    PROTOCOL_VERSION = 70015
    
    def __init__(self, network='mainnet', max_peers=1000):
        """Initialize crawler with python-bitcoinlib."""
        self.network = network
        self.max_peers = max_peers
        self.discovered_peers: Set[tuple] = set()
        self.visited_peers: Set[tuple] = set()
        self.peer_queue = deque()
        
        # Use python-bitcoinlib to select network parameters
        if network == 'mainnet':
            SelectParams('mainnet')
            self.magic = self.MAINNET_MAGIC
        else:
            SelectParams('testnet')
            self.magic = self.TESTNET_MAGIC
        
        logger.info(f"Using python-bitcoinlib for {network} network")
    
    def get_dns_seeds(self) -> List[tuple]:
        """Get initial peers from Bitcoin DNS seeds."""
        dns_seeds = [
            'seed.bitcoin.sipa.be',
            'dnsseed.bluematt.me',
            'dnsseed.bitcoin.dashjr.org',
            'seed.bitcoinstats.com',
            'seed.bitcoin.jonasschnelli.ch',
            'seed.btc.petertodd.org'
        ]
        
        peers = []
        if self.network == 'mainnet':
            for seed in dns_seeds:
                try:
                    result = socket.getaddrinfo(seed, 8333, socket.AF_INET)
                    for addr_info in result[:3]:
                        ip = addr_info[4][0]
                        peers.append((ip, 8333))
                        logger.info(f"Got peer from DNS seed {seed}: {ip}:8333")
                except Exception as e:
                    logger.debug(f"Failed to resolve {seed}: {e}")
        
        return peers
    
    def create_message(self, command: str, payload: bytes) -> bytes:
        """Create Bitcoin protocol message."""
        command_bytes = command.encode('ascii').ljust(12, b'\x00')
        length = struct.pack('<I', len(payload))
        
        # Checksum: double SHA256, first 4 bytes
        import hashlib
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        return (
            struct.pack('<I', self.magic) +
            command_bytes +
            length +
            checksum +
            payload
        )
    
    def create_version_message(self, peer_addr: tuple) -> bytes:
        """Create version message."""
        version = struct.pack('<i', self.PROTOCOL_VERSION)
        services = struct.pack('<Q', 1)  # NODE_NETWORK
        timestamp = struct.pack('<q', int(time.time()))
        
        # Address receiving
        addr_recv_services = struct.pack('<Q', 1)
        addr_recv_ip = self._ip_to_bytes(peer_addr[0])
        addr_recv_port = struct.pack('>H', peer_addr[1])
        
        # Address transmitting
        addr_trans_services = struct.pack('<Q', 1)
        addr_trans_ip = self._ip_to_bytes('0.0.0.0')
        addr_trans_port = struct.pack('>H', 0)
        
        nonce = struct.pack('<Q', random.getrandbits(64))
        user_agent = b'/bitcoinlib-crawler:0.1/'
        user_agent_len = struct.pack('<B', len(user_agent))
        start_height = struct.pack('<i', 0)
        relay = struct.pack('<?', False)
        
        return (
            version + services + timestamp +
            addr_recv_services + addr_recv_ip + addr_recv_port +
            addr_trans_services + addr_trans_ip + addr_trans_port +
            nonce + user_agent_len + user_agent +
            start_height + relay
        )
    
    @staticmethod
    def _ip_to_bytes(ip: str) -> bytes:
        """Convert IP to 16-byte format."""
        parts = ip.split('.')
        return bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xFF, 0xFF,
                     int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])])
    
    def parse_addr_message(self, data: bytes) -> List[tuple]:
        """Parse addr message to extract peer addresses."""
        peers = []
        try:
            if len(data) < 1:
                return peers
            
            # Parse compact size (varint)
            offset = 0
            first_byte = data[offset]
            offset += 1
            
            if first_byte < 253:
                count = first_byte
            elif first_byte == 253:
                if len(data) < 3:
                    return peers
                count = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
            elif first_byte == 254:
                if len(data) < 5:
                    return peers
                count = struct.unpack('<I', data[offset:offset+4])[0]
                offset += 4
            else:
                if len(data) < 9:
                    return peers
                count = struct.unpack('<Q', data[offset:offset+8])[0]
                offset += 8
            
            # Limit count for safety
            count = min(count, 1000)
            
            # Parse addresses (30 bytes each: timestamp + services + IP + port)
            for _ in range(count):
                if offset + 30 > len(data):
                    break
                
                timestamp = struct.unpack('<I', data[offset:offset+4])[0]
                services = struct.unpack('<Q', data[offset+4:offset+12])[0]
                ip_bytes = data[offset+12:offset+28]
                port = struct.unpack('>H', data[offset+28:offset+30])[0]
                
                # Extract IPv4 address
                if ip_bytes[:12] == bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xFF, 0xFF]):
                    ip = '.'.join(str(b) for b in ip_bytes[12:16])
                    peers.append((ip, port))
                
                offset += 30
                
        except Exception as e:
            logger.debug(f"Error parsing addr message: {e}")
        
        return peers
    
    async def connect_to_peer(self, peer_addr: tuple, timeout: float = 10.0) -> Optional[List[tuple]]:
        """Connect to peer and get its peer list."""
        ip, port = peer_addr
        discovered = []
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            
            # Send version message
            version_payload = self.create_version_message(peer_addr)
            version_msg = self.create_message('version', version_payload)
            writer.write(version_msg)
            await writer.drain()
            
            # Read version response
            response = b''
            for _ in range(5):
                chunk = await asyncio.wait_for(reader.read(1024), timeout=3.0)
                if not chunk:
                    break
                response += chunk
                
                # Look for Bitcoin magic
                for i in range(min(len(response) - 3, 200)):
                    if struct.unpack('<I', response[i:i+4])[0] == self.magic:
                        response = response[i:]
                        break
                else:
                    continue
                break
            
            if len(response) < 24:
                writer.close()
                await writer.wait_closed()
                return None
            
            # Send verack
            verack_msg = self.create_message('verack', b'')
            writer.write(verack_msg)
            await writer.drain()
            
            # Wait for verack (optional)
            try:
                await asyncio.wait_for(reader.read(24), timeout=2.0)
            except:
                pass
            
            # Send getaddr
            getaddr_msg = self.create_message('getaddr', b'')
            writer.write(getaddr_msg)
            await writer.drain()
            
            # Read addr response
            addr_response = b''
            for _ in range(10):
                chunk = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                if not chunk:
                    break
                addr_response += chunk
                
                # Check if we have a complete addr message
                if len(addr_response) >= 24:
                    header = addr_response[:24]
                    magic = struct.unpack('<I', header[0:4])[0]
                    if magic == self.magic:
                        command = header[4:16].rstrip(b'\x00').decode('ascii', errors='ignore')
                        if command == 'addr':
                            payload_len = struct.unpack('<I', header[16:20])[0]
                            if len(addr_response) >= 24 + payload_len:
                                break
            
            # Parse addr message - scan for addr messages in response
            if len(addr_response) >= 24:
                # Look for addr messages in the response
                for i in range(len(addr_response) - 24):
                    header = addr_response[i:i+24]
                    magic = struct.unpack('<I', header[0:4])[0]
                    if magic == self.magic:
                        command = header[4:16].rstrip(b'\x00').decode('ascii', errors='ignore')
                        if command == 'addr':
                            payload_len = struct.unpack('<I', header[16:20])[0]
                            if payload_len > 0 and len(addr_response) >= i + 24 + payload_len:
                                payload = addr_response[i+24:i+24+payload_len]
                                discovered = self.parse_addr_message(payload)
                                if discovered:
                                    logger.info(f"Discovered {len(discovered)} peers from {ip}:{port}")
                                    break
            
            writer.close()
            await writer.wait_closed()
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout connecting to {ip}:{port}")
        except Exception as e:
            logger.debug(f"Error connecting to {ip}:{port}: {e}")
        
        return discovered if discovered else None
    
    async def crawl_from_seed(self, seed_peer: Optional[tuple] = None):
        """Start crawling from seed peer or DNS seeds."""
        # Get initial peers from DNS seeds
        dns_peers = self.get_dns_seeds()
        for peer in dns_peers[:20]:  # Use first 20 DNS peers
            if peer not in self.discovered_peers:
                self.peer_queue.append(peer)
                self.discovered_peers.add(peer)
        
        # Add seed peer if provided
        if seed_peer and seed_peer not in self.discovered_peers:
            self.peer_queue.append(seed_peer)
            self.discovered_peers.add(seed_peer)
        
        logger.info(f"Starting crawl with {len(self.peer_queue)} initial peers")
        
        # Iteratively crawl peers
        while self.peer_queue and len(self.visited_peers) < self.max_peers:
            current_peer = self.peer_queue.popleft()
            
            if current_peer in self.visited_peers:
                continue
            
            self.visited_peers.add(current_peer)
            logger.info(f"Crawling {current_peer[0]}:{current_peer[1]} "
                       f"({len(self.visited_peers)}/{self.max_peers} visited, "
                       f"{len(self.discovered_peers)} discovered)")
            
            # Connect and get peers
            new_peers = await self.connect_to_peer(current_peer)
            
            if new_peers:
                for peer in new_peers:
                    if peer not in self.discovered_peers:
                        self.discovered_peers.add(peer)
                        self.peer_queue.append(peer)
            
            # Small delay to avoid overwhelming nodes
            await asyncio.sleep(0.2)
    
    def get_results(self) -> Dict:
        """Get crawling results."""
        return {
            'total_discovered': len(self.discovered_peers),
            'total_visited': len(self.visited_peers),
            'peers': [
                {
                    'ip': ip,
                    'port': port,
                    'address': f"{ip}:{port}"
                }
                for ip, port in sorted(self.discovered_peers)
            ]
        }


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crawl Bitcoin network peers using python-bitcoinlib',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Note: Bitcoin CLI does NOT provide an API to list peers of a given node.
This script uses python-bitcoinlib to crawl the Bitcoin network.

Examples:
  # Crawl from DNS seeds (default):
  python3 bitcoin_peer_crawler.py --max-peers 100
  
  # Crawl from specific node:
  python3 bitcoin_peer_crawler.py --seed-ip 104.248.9.49 --seed-port 8333
        """
    )
    
    parser.add_argument('--seed-ip', type=str,
                       help='Seed peer IP address')
    parser.add_argument('--seed-port', type=int, default=8333,
                       help='Seed peer port (default: 8333)')
    parser.add_argument('--network', type=str, choices=['mainnet', 'testnet'],
                       default='mainnet', help='Bitcoin network (default: mainnet)')
    parser.add_argument('--max-peers', type=int, default=100,
                       help='Maximum peers to discover (default: 100)')
    parser.add_argument('--output', type=str, default='peers.json',
                       help='Output file (default: peers.json)')
    
    args = parser.parse_args()
    
    # Create crawler
    crawler = BitcoinPeerCrawler(network=args.network, max_peers=args.max_peers)
    
    # Start crawling
    seed_peer = None
    if args.seed_ip:
        seed_peer = (args.seed_ip, args.seed_port)
    
    await crawler.crawl_from_seed(seed_peer)
    
    # Get results
    results = crawler.get_results()
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Crawling complete!")
    print(f"Discovered {results['total_discovered']} peers")
    print(f"Visited {results['total_visited']} peers")
    print(f"Results saved to {args.output}")
    print(f"{'='*60}")


if __name__ == '__main__':
    asyncio.run(main())
