#!/usr/bin/env python3
"""
Redis Database Module for Bitcoin Testnet Crawler
High-performance in-memory database - NOT SQLite!

Redis Features:
- Ultra-fast in-memory storage
- Persistent to disk (RDB/AOF)
- Hash/Set data structures perfect for peer data
- Atomic operations for concurrent access
- Already used by bitnodes-crawler
"""

import json
import os
import time
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  redis not installed. Run: pip3 install redis")

# Default Redis configuration
DEFAULT_REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
DEFAULT_REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
DEFAULT_REDIS_DB = int(os.environ.get('REDIS_DB', '1'))  # Use DB 1 for crawler


class BitcoinNodesDB:
    """
    Redis-based storage for Bitcoin network nodes.
    Optimized for high-speed reads/writes and large-scale data.
    
    Data Structure:
    - peers:{ip} - Hash containing peer information
    - peers:uncontacted - Set of IPs that haven't been contacted
    - peers:contacted - Set of IPs that have been contacted
    - peers:successful - Set of IPs with successful handshakes
    - peers:geolocated - Set of IPs with geolocation data
    - stats:* - Various statistics
    - session:{id} - Crawl session metadata
    """
    
    # Key prefixes
    PREFIX_PEER = "btc:peer:"
    PREFIX_SESSION = "btc:session:"
    KEY_UNCONTACTED = "btc:peers:uncontacted"
    KEY_CONTACTED = "btc:peers:contacted"
    KEY_SUCCESSFUL = "btc:peers:successful"
    KEY_GEOLOCATED = "btc:peers:geolocated"
    KEY_ALL_PEERS = "btc:peers:all"
    KEY_SESSION_COUNTER = "btc:session:counter"
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = None,
        decode_responses: bool = True
    ):
        """
        Initialize the Redis database connection.
        
        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 6379)
            db: Redis database number (default: 1)
            decode_responses: Decode responses to strings (default: True)
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis library not available. Install with: pip3 install redis")
        
        self.host = host or DEFAULT_REDIS_HOST
        self.port = port or DEFAULT_REDIS_PORT
        self.db = db if db is not None else DEFAULT_REDIS_DB
        
        # Create connection
        self.conn = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=decode_responses
        )
        
        # Verify connection
        try:
            self.conn.ping()
            print(f"📦 Redis connected: {self.host}:{self.port} (db={self.db})")
        except redis.ConnectionError as e:
            print(f"❌ Redis connection failed: {e}")
            print("   Make sure Redis server is running!")
            print("   Start with: redis-server")
            raise
    
    def start_crawl_session(self, network: str = 'testnet') -> int:
        """
        Start a new crawl session and return its ID.
        """
        session_id = self.conn.incr(self.KEY_SESSION_COUNTER)
        
        session_data = {
            'id': session_id,
            'network': network,
            'started_at': datetime.now().isoformat(),
            'ended_at': '',
            'total_discovered': 0,
            'total_contacted': 0,
            'successful_handshakes': 0,
            'failed_connections': 0,
            'iterations_completed': 0,
            'duration_seconds': 0
        }
        
        self.conn.hset(f"{self.PREFIX_SESSION}{session_id}", mapping=session_data)
        print(f"🚀 Started crawl session #{session_id}")
        return session_id
    
    def end_crawl_session(self, session_id: int, stats: Dict[str, int]):
        """
        End a crawl session and record final statistics.
        """
        session_key = f"{self.PREFIX_SESSION}{session_id}"
        
        updates = {
            'ended_at': datetime.now().isoformat(),
            'total_discovered': stats.get('total_discovered', 0),
            'total_contacted': stats.get('total_contacted', 0),
            'successful_handshakes': stats.get('successful_handshakes', 0),
            'failed_connections': stats.get('failed_connections', 0),
            'iterations_completed': stats.get('iterations_completed', 0),
            'duration_seconds': stats.get('duration_seconds', 0)
        }
        
        self.conn.hset(session_key, mapping=updates)
        print(f"✅ Ended crawl session #{session_id}")
    
    def save_peer(
        self,
        ip: str,
        port: int,
        user_agent: Optional[str] = None,
        contacted: bool = False,
        successful: bool = False,
        services: int = 0,
        version: int = 0,
        height: int = 0
    ):
        """
        Save or update a peer in the database.
        Uses Redis Hash for efficient storage.
        """
        peer_key = f"{self.PREFIX_PEER}{ip}"
        now = datetime.now().isoformat()
        
        # Check if peer exists
        exists = self.conn.exists(peer_key)
        
        peer_data = {
            'ip': ip,
            'port': port,
            'last_seen': now
        }
        
        if not exists:
            peer_data['first_discovered'] = now
            # Add to uncontacted set if new
            if not contacted:
                self.conn.sadd(self.KEY_UNCONTACTED, ip)
        
        if user_agent:
            peer_data['user_agent'] = user_agent
        if services:
            peer_data['services'] = services
        if version:
            peer_data['version'] = version
        if height:
            peer_data['height'] = height
        
        # Store peer data
        self.conn.hset(peer_key, mapping=peer_data)
        
        # Add to all peers set
        self.conn.sadd(self.KEY_ALL_PEERS, ip)
        
        # Update status sets
        if contacted:
            self.conn.srem(self.KEY_UNCONTACTED, ip)
            self.conn.sadd(self.KEY_CONTACTED, ip)
            self.conn.hset(peer_key, 'contacted', '1')
        
        if successful:
            self.conn.sadd(self.KEY_SUCCESSFUL, ip)
            self.conn.hset(peer_key, 'successful_handshake', '1')
    
    def save_peers_batch(self, peers: List[Tuple[str, int]]):
        """
        Save multiple peers efficiently using pipeline.
        """
        if not peers:
            return
        
        now = datetime.now().isoformat()
        pipe = self.conn.pipeline()
        
        for ip, port in peers:
            peer_key = f"{self.PREFIX_PEER}{ip}"
            
            # Only add if new
            if not self.conn.exists(peer_key):
                peer_data = {
                    'ip': ip,
                    'port': port,
                    'first_discovered': now,
                    'last_seen': now,
                    'contacted': '0',
                    'successful_handshake': '0'
                }
                pipe.hset(peer_key, mapping=peer_data)
                pipe.sadd(self.KEY_UNCONTACTED, ip)
                pipe.sadd(self.KEY_ALL_PEERS, ip)
        
        pipe.execute()
    
    def mark_peer_contacted(
        self,
        ip: str,
        port: int,
        success: bool,
        user_agent: Optional[str] = None,
        services: int = 0,
        version: int = 0,
        height: int = 0
    ):
        """
        Mark a peer as contacted and update its information.
        """
        peer_key = f"{self.PREFIX_PEER}{ip}"
        now = datetime.now().isoformat()
        
        updates = {
            'contacted': '1',
            'last_seen': now,
            'successful_handshake': '1' if success else '0'
        }
        
        if user_agent:
            updates['user_agent'] = user_agent
        if services:
            updates['services'] = services
        if version:
            updates['version'] = version
        if height:
            updates['height'] = height
        
        pipe = self.conn.pipeline()
        pipe.hset(peer_key, mapping=updates)
        pipe.srem(self.KEY_UNCONTACTED, ip)
        pipe.sadd(self.KEY_CONTACTED, ip)
        
        if success:
            pipe.sadd(self.KEY_SUCCESSFUL, ip)
        
        pipe.execute()
    
    def get_uncontacted_peers(self, limit: int = 1000) -> List[Tuple[str, int]]:
        """
        Get peers that haven't been contacted yet.
        """
        # Get random uncontacted peers
        ips = self.conn.srandmember(self.KEY_UNCONTACTED, limit)
        
        if not ips:
            return []
        
        peers = []
        pipe = self.conn.pipeline()
        for ip in ips:
            pipe.hget(f"{self.PREFIX_PEER}{ip}", 'port')
        
        ports = pipe.execute()
        
        for ip, port in zip(ips, ports):
            if port:
                peers.append((ip, int(port)))
        
        return peers
    
    def get_peer_counts(self) -> Dict[str, int]:
        """
        Get counts of total, contacted, and successful peers.
        """
        pipe = self.conn.pipeline()
        pipe.scard(self.KEY_ALL_PEERS)
        pipe.scard(self.KEY_CONTACTED)
        pipe.scard(self.KEY_SUCCESSFUL)
        
        total, contacted, successful = pipe.execute()
        
        return {
            'total': total or 0,
            'contacted': contacted or 0,
            'successful': successful or 0
        }
    
    def update_geolocation(
        self,
        ip: str,
        latitude: float,
        longitude: float,
        country: str,
        country_code: str,
        city: str,
        region: str,
        timezone: str,
        asn: Optional[int] = None,
        isp: Optional[str] = None
    ):
        """
        Update geolocation data for a peer.
        """
        peer_key = f"{self.PREFIX_PEER}{ip}"
        
        geo_data = {
            'latitude': latitude,
            'longitude': longitude,
            'country': country or '',
            'country_code': country_code or '',
            'city': city or '',
            'region': region or '',
            'timezone': timezone or ''
        }
        
        if asn:
            geo_data['asn'] = asn
        if isp:
            geo_data['isp'] = isp
        
        pipe = self.conn.pipeline()
        pipe.hset(peer_key, mapping=geo_data)
        pipe.sadd(self.KEY_GEOLOCATED, ip)
        pipe.execute()
    
    def update_geolocation_batch(self, locations: List[Dict[str, Any]]):
        """
        Batch update geolocation data for multiple peers.
        """
        if not locations:
            return
        
        pipe = self.conn.pipeline()
        
        for loc in locations:
            ip = loc['ip']
            peer_key = f"{self.PREFIX_PEER}{ip}"
            
            # Convert None values to empty strings for Redis
            geo_data = {
                'latitude': str(loc.get('latitude', '')),
                'longitude': str(loc.get('longitude', '')),
                'country': str(loc.get('country') or ''),
                'country_code': str(loc.get('country_code') or ''),
                'city': str(loc.get('city') or ''),
                'region': str(loc.get('region') or ''),
                'timezone': str(loc.get('timezone') or '')
            }
            
            if loc.get('asn'):
                geo_data['asn'] = str(loc['asn'])
            if loc.get('isp'):
                geo_data['isp'] = str(loc['isp'])
            
            pipe.hset(peer_key, mapping=geo_data)
            pipe.sadd(self.KEY_GEOLOCATED, ip)
        
        pipe.execute()
    
    def get_peers_for_geolocation(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get peers that need geolocation (no latitude set).
        """
        # Get all peers that are not geolocated
        all_peers = self.conn.smembers(self.KEY_ALL_PEERS)
        geolocated = self.conn.smembers(self.KEY_GEOLOCATED)
        
        need_geolocation = all_peers - geolocated
        
        if limit:
            need_geolocation = list(need_geolocation)[:limit]
        
        peers = []
        for ip in need_geolocation:
            peer_key = f"{self.PREFIX_PEER}{ip}"
            data = self.conn.hgetall(peer_key)
            if data:
                peers.append({
                    'ip': ip,
                    'port': int(data.get('port', 18333)),
                    'user_agent': data.get('user_agent'),
                    'successful': data.get('successful_handshake') == '1'
                })
        
        return peers
    
    def get_geolocated_peers(self) -> List[Dict[str, Any]]:
        """
        Get all peers with geolocation data for visualization.
        """
        geolocated_ips = self.conn.smembers(self.KEY_GEOLOCATED)
        
        peers = []
        pipe = self.conn.pipeline()
        
        for ip in geolocated_ips:
            pipe.hgetall(f"{self.PREFIX_PEER}{ip}")
        
        results = pipe.execute()
        
        for ip, data in zip(geolocated_ips, results):
            if data and data.get('latitude') and data.get('longitude'):
                try:
                    lat = float(data.get('latitude', 0))
                    lon = float(data.get('longitude', 0))
                    if lat and lon:
                        peers.append({
                            'ip': ip,
                            'port': int(data.get('port', 18333)),
                            'user_agent': data.get('user_agent', ''),
                            'latitude': lat,
                            'longitude': lon,
                            'country': data.get('country', 'Unknown'),
                            'country_code': data.get('country_code', ''),
                            'city': data.get('city', 'Unknown'),
                            'region': data.get('region', ''),
                            'timezone': data.get('timezone', ''),
                            'asn': int(data.get('asn', 0)) if data.get('asn') else None,
                            'isp': data.get('isp', ''),
                            'successful': data.get('successful_handshake') == '1',
                            'services': int(data.get('services', 0)) if data.get('services') else 0,
                            'version': int(data.get('version', 0)) if data.get('version') else 0,
                            'height': int(data.get('height', 0)) if data.get('height') else 0
                        })
                except (ValueError, TypeError):
                    continue
        
        return peers
    
    def get_country_stats(self) -> List[Dict[str, Any]]:
        """
        Get peer counts grouped by country.
        """
        peers = self.get_geolocated_peers()
        
        from collections import defaultdict
        country_data = defaultdict(lambda: {
            'peer_count': 0,
            'successful_count': 0,
            'lats': [],
            'lons': []
        })
        
        for peer in peers:
            country = peer.get('country', 'Unknown')
            country_code = peer.get('country_code', '')
            
            key = (country, country_code)
            country_data[key]['peer_count'] += 1
            if peer.get('successful'):
                country_data[key]['successful_count'] += 1
            country_data[key]['lats'].append(peer['latitude'])
            country_data[key]['lons'].append(peer['longitude'])
        
        result = []
        for (country, country_code), data in country_data.items():
            result.append({
                'country': country,
                'country_code': country_code,
                'peer_count': data['peer_count'],
                'successful_count': data['successful_count'],
                'avg_lat': sum(data['lats']) / len(data['lats']) if data['lats'] else 0,
                'avg_lon': sum(data['lons']) / len(data['lons']) if data['lons'] else 0
            })
        
        return sorted(result, key=lambda x: x['peer_count'], reverse=True)
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics summary.
        """
        # Basic counts
        counts = self.get_peer_counts()
        
        # Geolocated count
        geolocated = self.conn.scard(self.KEY_GEOLOCATED)
        
        # Country count
        country_stats = self.get_country_stats()
        
        # User agent distribution (sample)
        peers = self.get_geolocated_peers()
        ua_counts = {}
        for peer in peers:
            ua = peer.get('user_agent', 'unknown')
            if ua and ua != 'unknown':
                ua_counts[ua] = ua_counts.get(ua, 0) + 1
        
        top_uas = sorted(ua_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_peers': counts['total'],
            'contacted_peers': counts['contacted'],
            'successful_handshakes': counts['successful'],
            'geolocated_peers': geolocated,
            'countries': len(country_stats),
            'top_user_agents': [{'user_agent': ua, 'count': c} for ua, c in top_uas]
        }
    
    def export_to_json(self, output_path: str) -> int:
        """
        Export all geolocated peers to JSON file.
        """
        peers = self.get_geolocated_peers()
        
        with open(output_path, 'w') as f:
            json.dump(peers, f, indent=2)
        
        return len(peers)
    
    def clear_all(self):
        """
        Clear all crawler data (use with caution!).
        """
        keys = self.conn.keys('btc:*')
        if keys:
            self.conn.delete(*keys)
        print("🗑️  All crawler data cleared")
    
    def close(self):
        """Close the database connection."""
        self.conn.close()
        print("📦 Redis connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience function
def get_db(host: str = None, port: int = None, db: int = None) -> BitcoinNodesDB:
    """Get a database instance."""
    return BitcoinNodesDB(host=host, port=port, db=db)


if __name__ == "__main__":
    # Test the database
    print("🧪 Testing Redis Module...")
    
    try:
        with BitcoinNodesDB() as db:
            # Test save peer
            db.save_peer("203.0.113.1", 18333, "test-agent")
            db.save_peer("203.0.113.2", 18333)
            
            # Test batch save
            db.save_peers_batch([
                ("203.0.113.3", 18333),
                ("203.0.113.4", 18333),
            ])
            
            # Test counts
            counts = db.get_peer_counts()
            print(f"📊 Peer counts: {counts}")
            
            # Test uncontacted
            uncontacted = db.get_uncontacted_peers(10)
            print(f"📋 Uncontacted peers: {len(uncontacted)}")
            
            print("✅ Redis module tests passed!")
    except redis.ConnectionError:
        print("❌ Redis server not running. Start with: redis-server")
        print("   Or install Redis: brew install redis (macOS)")
