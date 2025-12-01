#!/usr/bin/env python3

import sys
import json
import time
import socket
import struct
import hashlib
import threading
from collections import deque
from threading import Lock, Event
import signal
import random

DNS_SEEDS = [
    'seed.bitcoin.sipa.be',
    'dnsseed.bluematt.me',
    'dnsseed.bitcoin.dashjr.org',
    'seed.bitcoinstats.com',
    'seed.bitcoin.jonasschnelli.ch',
    'seed.btc.petertodd.org',
    'seed.bitcoin.sprovoost.nl',
    'dnsseed.emzy.de',
    'seed.bitcoin.wiz.biz'
]

BITCOIN_PORT = 8333
MAGIC_BYTES = b'\xf9\xbe\xb4\xd9'
PROTOCOL_VERSION = 70015
MAX_NODES = 1000
CRAWL_TIMEOUT = 30
CONNECTION_TIMEOUT = 5

class BitcoinCrawler:
    def __init__(self, max_nodes=MAX_NODES, timeout=CRAWL_TIMEOUT):
        self.max_nodes = max_nodes
        self.timeout = timeout
        self.discovered_nodes = {}
        self.to_crawl = deque()
        self.crawled = set()
        self.nodes_lock = Lock()
        self.stop_event = Event()
        
    def get_nodes_from_dns_seeds(self):
        """Get initial nodes from DNS seeds"""
        nodes = []
        for seed in DNS_SEEDS:
            try:
                ip_addresses = socket.gethostbyname_ex(seed)[2]
                for ip in ip_addresses:
                    try:
                        socket.inet_aton(ip)
                        nodes.append((ip, BITCOIN_PORT))
                    except socket.error:
                        continue
            except (socket.gaierror, socket.herror) as e:
                print(f"Warning: Failed to resolve {seed}: {e}", file=sys.stderr)
        return nodes
    
    def create_message(self, command, payload):
        """Create Bitcoin P2P message"""
        command_bytes = command.encode('ascii').ljust(12, b'\x00')
        payload_length = struct.pack('<I', len(payload))
        
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        return MAGIC_BYTES + command_bytes + payload_length + checksum + payload
    
    def create_version_message(self, remote_ip, remote_port):
        """Create version message"""
        version = struct.pack('<I', PROTOCOL_VERSION)
        services = struct.pack('<Q', 1)
        timestamp = struct.pack('<Q', int(time.time()))
        
        addr_recv = struct.pack('<I', 0)
        addr_recv += struct.pack('>H', remote_port)
        addr_recv += struct.pack('<Q', 1)
        addr_recv += b'\x00' * 12
        addr_recv += socket.inet_aton(remote_ip)
        
        addr_from = struct.pack('<I', 0)
        addr_from += struct.pack('>H', 0)
        addr_from += struct.pack('<Q', 0)
        addr_from += b'\x00' * 16
        
        nonce = struct.pack('<Q', random.getrandbits(64))
        user_agent = b'/BitcoinNodeCrawler:1.0/'
        user_agent_len = struct.pack('B', len(user_agent))
        start_height = struct.pack('<I', 0)
        relay = struct.pack('B', 1)
        
        payload = (version + services + timestamp + addr_recv + addr_from + 
                   nonce + user_agent_len + user_agent + start_height + relay)
        
        return self.create_message('version', payload)
    
    def create_getaddr_message(self):
        """Create getaddr message"""
        return self.create_message('getaddr', b'')
    
    def create_verack_message(self):
        """Create verack message"""
        return self.create_message('verack', b'')
    
    def parse_message(self, data):
        """Parse Bitcoin P2P message"""
        if len(data) < 24:
            return None
        
        magic = data[0:4]
        if magic != MAGIC_BYTES:
            return None
        
        command = data[4:16].rstrip(b'\x00').decode('ascii', errors='ignore')
        payload_length = struct.unpack('<I', data[16:20])[0]
        checksum = data[20:24]
        
        if len(data) < 24 + payload_length:
            return None
        
        payload = data[24:24 + payload_length]
        
        calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        if calculated_checksum != checksum:
            return None
        
        return {'command': command, 'payload': payload}
    
    def read_varint(self, data, offset):
        """Read variable-length integer"""
        if offset >= len(data):
            return (0, 0)
        
        first = data[offset]
        if first < 0xfd:
            return (first, 1)
        elif first == 0xfd:
            if offset + 3 > len(data):
                return (0, 0)
            return (struct.unpack('<H', data[offset+1:offset+3])[0], 3)
        elif first == 0xfe:
            if offset + 5 > len(data):
                return (0, 0)
            return (struct.unpack('<I', data[offset+1:offset+5])[0], 5)
        else:
            if offset + 9 > len(data):
                return (0, 0)
            return (struct.unpack('<Q', data[offset+1:offset+9])[0], 9)
    
    def parse_addr_message(self, payload):
        """Parse addr message to extract peer addresses"""
        addresses = []
        
        if len(payload) < 1:
            return addresses
        
        count, offset = self.read_varint(payload, 0)
        count = min(count, 1000)
        
        for i in range(count):
            if offset + 30 > len(payload):
                break
            
            timestamp = struct.unpack('<I', payload[offset:offset+4])[0]
            services = struct.unpack('<Q', payload[offset+4:offset+12])[0]
            ip_bytes = payload[offset+12:offset+28]
            
            is_ipv4 = (ip_bytes[0:12] == b'\x00' * 12 and 
                      ip_bytes[12:14] == b'\x00\x00' and
                      ip_bytes[14:16] == b'\xff\xff')
            
            if is_ipv4:
                ip = socket.inet_ntoa(ip_bytes[16:20])
                port = struct.unpack('>H', payload[offset+28:offset+30])[0]
                
                try:
                    socket.inet_aton(ip)
                    addresses.append({'ip': ip, 'port': port, 'timestamp': timestamp})
                except socket.error:
                    pass
            
            offset += 30
        
        return addresses
    
    def connect_and_crawl(self, ip, port):
        """Connect to a Bitcoin node and request peer addresses"""
        if self.stop_event.is_set():
            return {'success': False, 'peers': []}
        
        peers = []
        sock = None
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECTION_TIMEOUT)
            sock.connect((ip, port))
            
            version_msg = self.create_version_message(ip, port)
            sock.sendall(version_msg)
            
            message_buffer = b''
            version_received = False
            verack_received = False
            addr_received = False
            
            start_time = time.time()
            while (time.time() - start_time) < CONNECTION_TIMEOUT and not addr_received:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    message_buffer += data
                    
                    while len(message_buffer) >= 24:
                        msg = self.parse_message(message_buffer)
                        
                        if not msg:
                            magic_index = message_buffer.find(MAGIC_BYTES, 1)
                            if magic_index > 0:
                                message_buffer = message_buffer[magic_index:]
                                continue
                            break
                        
                        if msg['command'] == 'version':
                            if not version_received:
                                version_received = True
                                sock.sendall(self.create_verack_message())
                        
                        elif msg['command'] == 'verack':
                            if not verack_received and version_received:
                                verack_received = True
                                sock.sendall(self.create_getaddr_message())
                        
                        elif msg['command'] == 'addr':
                            if not addr_received:
                                addr_received = True
                                peers = self.parse_addr_message(msg['payload'])
                                break
                        
                        msg_length = 24 + len(msg['payload'])
                        message_buffer = message_buffer[msg_length:]
                    
                    if addr_received:
                        break
                        
                except socket.timeout:
                    break
                except Exception:
                    break
            
            return {'success': addr_received, 'peers': peers}
            
        except Exception as e:
            return {'success': False, 'peers': [], 'error': str(e)}
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def crawl_network(self):
        """Main crawl function"""
        print(f"[Crawler] Starting Bitcoin network crawl (max {self.max_nodes} nodes)...", file=sys.stderr)
        start_time = time.time()
        
        print("[Crawler] Getting initial nodes from DNS seeds...", file=sys.stderr)
        seed_nodes = self.get_nodes_from_dns_seeds()
        print(f"[Crawler] Found {len(seed_nodes)} seed nodes", file=sys.stderr)
        
        for ip, port in seed_nodes:
            self.to_crawl.append((ip, port))
        
        crawl_count = 0
        while (self.to_crawl and 
               len(self.discovered_nodes) < self.max_nodes and 
               (time.time() - start_time) < self.timeout and
               not self.stop_event.is_set()):
            
            if not self.to_crawl:
                break
                
            ip, port = self.to_crawl.popleft()
            node_key = f"{ip}:{port}"
            
            if node_key in self.crawled:
                continue
            
            self.crawled.add(node_key)
            crawl_count += 1
            
            if crawl_count % 10 == 0:
                print(f"[Crawler] Crawled {crawl_count} nodes, discovered {len(self.discovered_nodes)} unique nodes", file=sys.stderr)
            
            result = self.connect_and_crawl(ip, port)
            
            if result['success']:
                with self.nodes_lock:
                    if node_key not in self.discovered_nodes:
                        self.discovered_nodes[node_key] = {"version": "70015"}
                
                if result['peers']:
                    for peer in result['peers']:
                        peer_key = f"{peer['ip']}:{peer['port']}"
                        if (peer_key not in self.discovered_nodes and 
                            peer_key not in self.crawled and
                            len(self.to_crawl) < 500 and
                            len(self.discovered_nodes) < self.max_nodes):
                            self.to_crawl.append((peer['ip'], peer['port']))
            
            time.sleep(0.1)
        
        elapsed = time.time() - start_time
        print(f"[Crawler] Completed: discovered {len(self.discovered_nodes)} nodes in {elapsed:.2f}s", file=sys.stderr)
        
        return self.discovered_nodes

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bitcoin P2P Network Crawler')
    parser.add_argument('--max-nodes', type=int, default=MAX_NODES, help='Maximum nodes to discover')
    parser.add_argument('--timeout', type=int, default=CRAWL_TIMEOUT, help='Crawl timeout in seconds')
    
    args = parser.parse_args()
    
    crawler = BitcoinCrawler(max_nodes=args.max_nodes, timeout=args.timeout)
    
    def signal_handler(sig, frame):
        print("\n[Crawler] Stopping crawler...", file=sys.stderr)
        crawler.stop_event.set()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        nodes = crawler.crawl_network()
        
        output_data = {
            "nodes": nodes,
            "count": len(nodes),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        print(json.dumps(output_data))
        
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        nodes_file = os.path.join(project_root, 'nodes.json')
        with open(nodes_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"[Crawler] Nodes data written to {nodes_file}", file=sys.stderr)
        
    except KeyboardInterrupt:
        print("\n[Crawler] Interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
