#!/usr/bin/env python3
"""
Bitcoin TESTNET P2P Network Crawler
Custom implementation using Redis for high-performance storage

Discovers peers by crawling the testnet P2P network.
Uses YOUR Bitcoin Core testnet node as starting point.

Features:
- Async/concurrent connections for fast crawling
- Redis storage (NOT SQLite!) for ultra-fast queries
- Progress tracking and statistics
- Automatic geolocation support
"""

import asyncio
import socket
import struct
import hashlib
import time
import random
import os
import sys
from typing import Set, List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import requests
from requests.auth import HTTPBasicAuth
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import BitcoinNodesDB

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    BITCOIN TESTNET PROTOCOL CONSTANTS                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

MAGIC_BYTES = b'\x0b\x11\x09\x07'  # Testnet magic bytes
PROTOCOL_VERSION = 70015
USER_AGENT = "/BitcoinTestnetCrawler:2.0.0/"

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         CRAWL CONFIGURATION                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class CrawlConfig:
    """Configuration for the crawler."""
    target_peers: int = 100000       # Target: 100K unique peers
    max_queue_size: int = 10000      # Keep queue manageable
    concurrency: int = 500           # Parallel connections
    connect_timeout: int = 5         # Connection timeout (seconds)
    read_timeout: int = 5            # Read timeout (seconds)
    max_iterations: int = 100        # Maximum crawl iterations
    delay_between_iterations: float = 0.5  # Delay between iterations


# Default configuration
DEFAULT_CONFIG = CrawlConfig()

# Bitcoin Core RPC Configuration (Testnet)
RPC_USER = os.environ.get("BITCOIN_RPC_USER", "bitcoinrpc")
RPC_PASSWORD = os.environ.get("BITCOIN_RPC_PASSWORD", "your_secure_password_here_12345")
RPC_HOST = os.environ.get("BITCOIN_RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.environ.get("BITCOIN_RPC_PORT", "18332"))  # Testnet RPC port

# Testnet DNS seeds (fallback)
TESTNET_DNS_SEEDS = [
    "testnet-seed.bitcoin.jonasschnelli.ch",
    "seed.tbtc.petertodd.org",
    "testnet-seed.bluematt.me",
    "testnet-seed.bitcoin.schildbach.de",
]

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         STATISTICS TRACKER                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class CrawlStats:
    """Track crawl statistics."""
    
    def __init__(self):
        self.total_discovered = 0
        self.total_contacted = 0
        self.successful_handshakes = 0
        self.failed_connections = 0
        self.peers_per_iteration: List[int] = []
        self.start_time = 0
        self.session_id = None
    
    def to_dict(self) -> Dict[str, Any]:
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'total_discovered': self.total_discovered,
            'total_contacted': self.total_contacted,
            'successful_handshakes': self.successful_handshakes,
            'failed_connections': self.failed_connections,
            'iterations_completed': len(self.peers_per_iteration),
            'duration_seconds': int(elapsed)
        }


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         BITCOIN PROTOCOL HELPERS                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def encode_varint(n: int) -> bytes:
    """Encode variable-length integer (Bitcoin protocol)."""
    if n < 0xfd:
        return bytes([n])
    elif n <= 0xffff:
        return b'\xfd' + struct.pack('<H', n)
    elif n <= 0xffffffff:
        return b'\xfe' + struct.pack('<I', n)
    else:
        return b'\xff' + struct.pack('<Q', n)


def decode_varint(data: bytes, offset: int = 0) -> Tuple[int, int]:
    """Decode variable-length integer, return (value, new_offset)."""
    if offset >= len(data):
        return 0, offset
    
    first = data[offset]
    if first < 0xfd:
        return first, offset + 1
    elif first == 0xfd:
        if offset + 3 > len(data):
            return 0, offset
        return struct.unpack('<H', data[offset+1:offset+3])[0], offset + 3
    elif first == 0xfe:
        if offset + 5 > len(data):
            return 0, offset
        return struct.unpack('<I', data[offset+1:offset+5])[0], offset + 5
    else:
        if offset + 9 > len(data):
            return 0, offset
        return struct.unpack('<Q', data[offset+1:offset+9])[0], offset + 9


def sha256d(data: bytes) -> bytes:
    """Double SHA256 hash."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def is_public_ipv4(ip: str) -> bool:
    """Check if IP is public IPv4 (not private/local)."""
    try:
        # Skip IPv6
        if ':' in ip:
            return False
        
        parts = [int(p) for p in ip.split('.')]
        if len(parts) != 4:
            return False
        
        # Private/reserved ranges
        if parts[0] == 10:
            return False
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return False
        if parts[0] == 192 and parts[1] == 168:
            return False
        if parts[0] == 127:
            return False
        if parts[0] == 0:
            return False
        if parts[0] >= 224:  # Multicast and reserved
            return False
        
        return True
    except:
        return False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                      BITCOIN MESSAGE CONSTRUCTION                           ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def create_version_message(dest_ip: str, dest_port: int) -> bytes:
    """Create Bitcoin VERSION message for testnet."""
    payload = struct.pack('<i', PROTOCOL_VERSION)  # version
    payload += struct.pack('<Q', 0)  # services
    payload += struct.pack('<q', int(time.time()))  # timestamp
    
    # addr_recv (destination)
    payload += struct.pack('<Q', 0)  # services
    try:
        payload += b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(dest_ip)
    except:
        payload += b'\x00' * 16
    payload += struct.pack('>H', dest_port)
    
    # addr_from (us)
    payload += struct.pack('<Q', 0)  # services
    payload += b'\x00' * 16  # IPv6 (zeros)
    payload += struct.pack('>H', 0)  # port
    
    payload += struct.pack('<Q', random.getrandbits(64))  # nonce
    payload += encode_varint(len(USER_AGENT)) + USER_AGENT.encode()
    payload += struct.pack('<i', 0)  # start_height
    payload += bytes([1])  # relay
    
    # Build header
    header = MAGIC_BYTES
    header += b'version\x00\x00\x00\x00\x00'
    header += struct.pack('<I', len(payload))
    header += sha256d(payload)[:4]
    
    return header + payload


def create_verack_message() -> bytes:
    """Create Bitcoin VERACK message."""
    return MAGIC_BYTES + b'verack\x00\x00\x00\x00\x00\x00' + b'\x00\x00\x00\x00' + sha256d(b'')[:4]


def create_getaddr_message() -> bytes:
    """Create Bitcoin GETADDR message to request peer list."""
    return MAGIC_BYTES + b'getaddr\x00\x00\x00\x00\x00' + b'\x00\x00\x00\x00' + sha256d(b'')[:4]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                      BITCOIN MESSAGE PARSING                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def parse_addr_payload(payload: bytes) -> List[Tuple[str, int]]:
    """Parse ADDR message payload to extract peer addresses."""
    try:
        count, offset = decode_varint(payload, 0)
        peers = []
        
        for _ in range(min(count, 1000)):  # Limit to 1000 addresses per message
            if offset + 30 > len(payload):
                break
            
            # Skip timestamp (4 bytes) and services (8 bytes)
            offset += 12
            
            # IP address (16 bytes)
            ip_bytes = payload[offset:offset+16]
            offset += 16
            
            # Port (2 bytes, big-endian)
            if offset + 2 > len(payload):
                break
            port = struct.unpack('>H', payload[offset:offset+2])[0]
            offset += 2
            
            # Check if IPv4-mapped IPv6
            if ip_bytes[:12] == b'\x00' * 10 + b'\xff\xff':
                ip = socket.inet_ntoa(ip_bytes[12:16])
                if is_public_ipv4(ip):
                    peers.append((ip, port))
        
        return peers
    except Exception:
        return []


@dataclass
class VersionInfo:
    """Parsed version message information."""
    version: int = 0
    services: int = 0
    user_agent: str = ""
    height: int = 0


def parse_version_payload(payload: bytes) -> Optional[VersionInfo]:
    """Parse VERSION message payload."""
    try:
        if len(payload) < 80:
            return None
        
        version = struct.unpack('<i', payload[0:4])[0]
        services = struct.unpack('<Q', payload[4:12])[0]
        
        # User agent starts after fixed fields (80 bytes)
        ua_len, offset = decode_varint(payload, 80)
        user_agent = ""
        if ua_len > 0 and ua_len < 256:
            user_agent = payload[offset:offset+ua_len].decode('utf-8', errors='ignore')
        
        # Height is after user agent
        height_offset = offset + ua_len
        height = 0
        if height_offset + 4 <= len(payload):
            height = struct.unpack('<i', payload[height_offset:height_offset+4])[0]
        
        return VersionInfo(version=version, services=services, user_agent=user_agent, height=height)
    except:
        return None


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         RPC / SEED DISCOVERY                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def bitcoin_rpc_call(method: str, params: List = None) -> Optional[dict]:
    """Make an RPC call to Bitcoin Core to get initial seeds."""
    if params is None:
        params = []
    
    url = f"http://{RPC_HOST}:{RPC_PORT}/"
    headers = {"content-type": "text/plain"}
    payload = {
        "jsonrpc": "1.0",
        "id": "crawler",
        "method": method,
        "params": params
    }
    
    try:
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            auth=HTTPBasicAuth(RPC_USER, RPC_PASSWORD),
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if "error" in result and result["error"]:
            print(f"❌ RPC Error: {result['error']}")
            return None
        return result.get("result")
    except Exception as e:
        print(f"⚠️  RPC call failed: {e}")
        return None


def get_seed_peers_from_bitcoin_core() -> List[Tuple[str, int]]:
    """Fetch initial seed peers from YOUR Bitcoin Core testnet node."""
    print("🔍 Fetching seed peers from Bitcoin Core testnet node...")
    
    peers_info = bitcoin_rpc_call("getpeerinfo")
    
    if not peers_info:
        print("⚠️  Could not fetch peers from Bitcoin Core")
        print("   Using DNS seeds as fallback...")
        return get_peers_from_dns_seeds()
    
    seed_peers = []
    for peer in peers_info:
        addr = peer.get('addr', '')
        if ':' in addr:
            try:
                ip, port = addr.rsplit(':', 1)
                port = int(port)
                # Skip IPv6 for now (focus on IPv4)
                if ':' not in ip and is_public_ipv4(ip):
                    seed_peers.append((ip, port))
            except ValueError:
                continue
    
    print(f"✅ Found {len(seed_peers)} seed peers from Bitcoin Core")
    for i, (ip, port) in enumerate(seed_peers[:5], 1):
        print(f"   {i}. {ip}:{port}")
    if len(seed_peers) > 5:
        print(f"   ... and {len(seed_peers) - 5} more")
    
    return seed_peers if seed_peers else get_peers_from_dns_seeds()


def get_peers_from_dns_seeds() -> List[Tuple[str, int]]:
    """Get initial peers from DNS seeds."""
    print("🌐 Resolving DNS seeds...")
    
    peers = []
    for seed in TESTNET_DNS_SEEDS:
        try:
            ips = socket.gethostbyname_ex(seed)[2]
            for ip in ips:
                if is_public_ipv4(ip):
                    peers.append((ip, 18333))
            print(f"   ✓ {seed}: {len(ips)} IPs")
        except socket.gaierror as e:
            print(f"   ✗ {seed}: {e}")
    
    print(f"📡 Total DNS seeds resolved: {len(peers)} peers")
    return peers


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                    ASYNC P2P CONNECTION HANDLER                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

@dataclass
class ConnectionResult:
    """Result of a P2P connection attempt."""
    success: bool
    peers: List[Tuple[str, int]]
    version_info: Optional[VersionInfo] = None
    error: Optional[str] = None


async def handshake_and_get_peers(
    ip: str,
    port: int,
    config: CrawlConfig = DEFAULT_CONFIG
) -> ConnectionResult:
    """
    Connect to a peer, perform handshake, and request their peer list.
    
    Returns:
        ConnectionResult with success status, discovered peers, and version info
    """
    try:
        # Establish connection
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=config.connect_timeout
        )
        
        # Send VERSION
        writer.write(create_version_message(ip, port))
        await writer.drain()
        
        # Wait for VERSION and VERACK
        received_version = False
        received_verack = False
        version_info = None
        
        for _ in range(10):  # Max 10 messages
            try:
                header = await asyncio.wait_for(
                    reader.readexactly(24),
                    timeout=config.read_timeout
                )
                
                # Verify magic bytes
                if header[:4] != MAGIC_BYTES:
                    break
                
                payload_len = struct.unpack('<I', header[16:20])[0]
                if payload_len > 5_000_000:  # Sanity check
                    break
                
                if payload_len > 0:
                    payload = await asyncio.wait_for(
                        reader.readexactly(payload_len),
                        timeout=config.read_timeout
                    )
                else:
                    payload = b''
                
                command = header[4:16].rstrip(b'\x00').decode('ascii', errors='ignore')
                
                if command == 'version':
                    received_version = True
                    version_info = parse_version_payload(payload)
                    writer.write(create_verack_message())
                    await writer.drain()
                elif command == 'verack':
                    received_verack = True
                
                if received_version and received_verack:
                    break
                    
            except asyncio.TimeoutError:
                break
            except:
                break
        
        if not (received_version and received_verack):
            writer.close()
            await writer.wait_closed()
            return ConnectionResult(success=False, peers=[], error="Handshake incomplete")
        
        # Send GETADDR
        writer.write(create_getaddr_message())
        await writer.drain()
        
        # Wait for ADDR response
        peers = []
        for _ in range(5):  # Max 5 messages
            try:
                header = await asyncio.wait_for(
                    reader.readexactly(24),
                    timeout=config.read_timeout
                )
                
                if header[:4] != MAGIC_BYTES:
                    break
                
                payload_len = struct.unpack('<I', header[16:20])[0]
                if payload_len > 5_000_000:
                    break
                
                if payload_len > 0:
                    payload = await asyncio.wait_for(
                        reader.readexactly(payload_len),
                        timeout=config.read_timeout
                    )
                    
                    command = header[4:16].rstrip(b'\x00').decode('ascii', errors='ignore')
                    
                    if command == 'addr':
                        new_peers = parse_addr_payload(payload)
                        peers.extend(new_peers)
                        if new_peers:  # Got addresses, we're done
                            break
            except asyncio.TimeoutError:
                break
            except:
                break
        
        writer.close()
        await writer.wait_closed()
        
        return ConnectionResult(success=True, peers=peers, version_info=version_info)
        
    except asyncio.TimeoutError:
        return ConnectionResult(success=False, peers=[], error="Connection timeout")
    except ConnectionRefusedError:
        return ConnectionResult(success=False, peers=[], error="Connection refused")
    except Exception as e:
        return ConnectionResult(success=False, peers=[], error=str(e))


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         MAIN CRAWLER CLASS                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BitcoinTestnetCrawler:
    """
    Bitcoin Testnet P2P Network Crawler.
    
    Uses Redis for high-performance storage and fast queries.
    """
    
    def __init__(self, config: CrawlConfig = None, redis_host: str = None, redis_port: int = None, redis_db: int = None):
        """
        Initialize the crawler.
        
        Args:
            config: Crawl configuration
            redis_host: Redis host (default: localhost)
            redis_port: Redis port (default: 6379)
            redis_db: Redis database number (default: 1)
        """
        self.config = config or DEFAULT_CONFIG
        self.db = BitcoinNodesDB(host=redis_host, port=redis_port, db=redis_db)
        self.stats = CrawlStats()
        self.visited: Set[str] = set()
    
    def print_banner(self):
        """Print crawler banner."""
        print()
        print("╔" + "═" * 68 + "╗")
        print("║" + "  🕷️  BITCOIN TESTNET P2P NETWORK CRAWLER".center(68) + "║")
        print("║" + "  Powered by Redis (High-Performance In-Memory DB)".center(68) + "║")
        print("╠" + "═" * 68 + "╣")
        print(f"║  🎯 Target: {self.config.target_peers:,} unique peers".ljust(69) + "║")
        print(f"║  ⚡ Concurrency: {self.config.concurrency} parallel connections".ljust(69) + "║")
        print(f"║  🔄 Max iterations: {self.config.max_iterations}".ljust(69) + "║")
        print(f"║  📦 Database: Redis".ljust(69) + "║")
        print("╚" + "═" * 68 + "╝")
        print()
    
    async def crawl(self) -> Dict[str, Any]:
        """
        Main crawl function - discover testnet peers.
        
        Returns:
            Dictionary with crawl statistics
        """
        self.print_banner()
        
        self.stats.start_time = time.time()
        self.stats.session_id = self.db.start_crawl_session('testnet')
        
        # Get seed peers
        seed_peers = get_seed_peers_from_bitcoin_core()
        
        # Save seed peers to database
        print(f"\n💾 Saving {len(seed_peers)} seed peers to Redis...")
        self.db.save_peers_batch(seed_peers)
        
        # Main crawl loop
        for iteration in range(self.config.max_iterations):
            counts = self.db.get_peer_counts()
            
            print(f"\n{'═' * 70}")
            print(f"🔄 ITERATION {iteration + 1}/{self.config.max_iterations}")
            print(f"{'═' * 70}")
            print(f"📊 Total discovered: {counts['total']:,} peers")
            print(f"✅ Contacted: {counts['contacted']:,} peers")
            print(f"🤝 Successful: {counts['successful']:,} handshakes")
            print(f"🎯 Progress: {(counts['total']/self.config.target_peers)*100:.1f}% of target")
            
            if counts['total'] >= self.config.target_peers:
                print(f"\n🎉 TARGET REACHED! Discovered {counts['total']:,} peers!")
                break
            
            # Get uncontacted peers
            queue = self.db.get_uncontacted_peers(self.config.concurrency)
            
            if not queue:
                print("⚠️  No more uncontacted peers in queue")
                break
            
            print(f"📋 Processing {len(queue)} peers this iteration...")
            
            # Process peers in parallel
            tasks = []
            peers_to_process = []
            for ip, port in queue:
                if ip not in self.visited:
                    self.visited.add(ip)
                    tasks.append(handshake_and_get_peers(ip, port, self.config))
                    peers_to_process.append((ip, port))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            new_peers_count = 0
            successful_count = 0
            new_peers_batch = []
            
            for i, result in enumerate(results):
                if i >= len(peers_to_process):
                    break
                
                ip, port = peers_to_process[i]
                
                if isinstance(result, ConnectionResult):
                    if result.success:
                        self.stats.successful_handshakes += 1
                        successful_count += 1
                        
                        # Update peer info
                        user_agent = result.version_info.user_agent if result.version_info else None
                        version = result.version_info.version if result.version_info else 0
                        services = result.version_info.services if result.version_info else 0
                        height = result.version_info.height if result.version_info else 0
                        
                        self.db.mark_peer_contacted(
                            ip, port, True, user_agent, services, version, height
                        )
                        
                        # Collect new peers for batch insert
                        for peer_ip, peer_port in result.peers:
                            if peer_ip not in self.visited:
                                new_peers_batch.append((peer_ip, peer_port))
                                new_peers_count += 1
                    else:
                        self.stats.failed_connections += 1
                        self.db.mark_peer_contacted(ip, port, False)
                else:
                    # Exception occurred
                    self.stats.failed_connections += 1
                    self.db.mark_peer_contacted(ip, port, False)
                
                self.stats.total_contacted += 1
            
            # Batch save new peers
            if new_peers_batch:
                self.db.save_peers_batch(new_peers_batch)
            
            self.stats.total_discovered += new_peers_count
            self.stats.peers_per_iteration.append(new_peers_count)
            
            elapsed = time.time() - self.stats.start_time
            print(f"✨ Discovered {new_peers_count:,} new peers")
            print(f"✅ Successful handshakes: {successful_count}/{len(peers_to_process)}")
            print(f"⏱️  Elapsed time: {elapsed/60:.1f} minutes")
            print(f"📈 Discovery rate: {counts['total']/(elapsed/60):.0f} peers/minute")
            
            # Small delay between iterations
            await asyncio.sleep(self.config.delay_between_iterations)
        
        # Final statistics
        return self._finalize_crawl(iteration + 1)
    
    def _finalize_crawl(self, iterations: int) -> Dict[str, Any]:
        """Finalize crawl and print summary."""
        counts = self.db.get_peer_counts()
        elapsed = time.time() - self.stats.start_time
        
        # Update stats
        final_stats = {
            'total_discovered': counts['total'],
            'total_contacted': counts['contacted'],
            'successful_handshakes': counts['successful'],
            'failed_connections': self.stats.failed_connections,
            'iterations_completed': iterations,
            'duration_seconds': int(elapsed)
        }
        
        # Save session stats
        self.db.end_crawl_session(self.stats.session_id, final_stats)
        
        # Print summary
        print()
        print("╔" + "═" * 68 + "╗")
        print("║" + "  🎉 CRAWL COMPLETE!".center(68) + "║")
        print("╠" + "═" * 68 + "╣")
        print(f"║  ✅ Total discovered peers: {counts['total']:,}".ljust(69) + "║")
        print(f"║  📞 Total contacted peers: {counts['contacted']:,}".ljust(69) + "║")
        print(f"║  🤝 Successful handshakes: {counts['successful']:,}".ljust(69) + "║")
        print(f"║  ❌ Failed connections: {self.stats.failed_connections:,}".ljust(69) + "║")
        print(f"║  ⏱️  Total time: {elapsed/60:.1f} minutes ({elapsed/3600:.2f} hours)".ljust(69) + "║")
        print(f"║  📈 Average rate: {counts['total']/(elapsed/60):.0f} peers/minute".ljust(69) + "║")
        print("╠" + "═" * 68 + "╣")
        print("║  📦 Database: Redis (High-Performance In-Memory DB)".ljust(69) + "║")
        print("║  🚀 Next step: Run geolocate.py to map all peers!".ljust(69) + "║")
        print("╚" + "═" * 68 + "╝")
        
        return final_stats
    
    def close(self):
        """Close database connection."""
        self.db.close()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              MAIN ENTRY                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Bitcoin Testnet P2P Network Crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (target: 100K peers):
  python3 crawler.py
  
  # Run with custom target:
  python3 crawler.py --target 10000 --concurrency 200

Environment Variables:
  BITCOIN_RPC_USER     - Bitcoin Core RPC username (default: bitcoinrpc)
  BITCOIN_RPC_PASSWORD - Bitcoin Core RPC password
  BITCOIN_RPC_HOST     - Bitcoin Core RPC host (default: 127.0.0.1)
  BITCOIN_RPC_PORT     - Bitcoin Core RPC port (default: 18332 for testnet)
  REDIS_HOST           - Redis host (default: localhost)
  REDIS_PORT           - Redis port (default: 6379)
  REDIS_DB             - Redis database number (default: 1)
        """
    )
    
    parser.add_argument('--target', type=int, default=100000,
                       help='Target number of peers to discover (default: 100000)')
    parser.add_argument('--concurrency', type=int, default=500,
                       help='Number of parallel connections (default: 500)')
    parser.add_argument('--max-iterations', type=int, default=100,
                       help='Maximum crawl iterations (default: 100)')
    parser.add_argument('--no-delay', action='store_true',
                       help='Skip the 3-second startup delay')
    
    args = parser.parse_args()
    
    config = CrawlConfig(
        target_peers=args.target,
        concurrency=args.concurrency,
        max_iterations=args.max_iterations
    )
    
    print("\n⚠️  IMPORTANT: Make sure Bitcoin-Qt is running in TESTNET mode!")
    print("   Also ensure Redis server is running: redis-server")
    
    if not args.no_delay:
        print("   Press Ctrl+C to cancel, or wait 3 seconds to start...\n")
        time.sleep(3)
    
    crawler = BitcoinTestnetCrawler(config=config)
    
    try:
        await crawler.crawl()
    finally:
        crawler.close()


if __name__ == "__main__":
    asyncio.run(main())

