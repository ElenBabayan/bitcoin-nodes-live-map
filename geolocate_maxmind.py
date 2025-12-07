#!/usr/bin/env python3
"""
Geolocate Bitcoin peers using IP geolocation database.
This is INSTANT - no API rate limits!

Auto-decompresses database on first run (included in repo, no download needed!).
"""

import json
import os
import sys
import gzip
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from database import PeersDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import geoip2
try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.error("geoip2 not installed. Run: pip install geoip2")


def decompress_geolite2_db(compressed_path: str, db_path: str) -> bool:
    """
    Decompress the included GeoLite2-City database.
    
    The database is included compressed in the repo to save space.
    This extracts it on first run.
    """
    logger.info("📦 Decompressing GeoLite2-City database...")
    logger.info(f"   From: {os.path.basename(compressed_path)}")
    logger.info(f"   To: {os.path.basename(db_path)}")
    
    try:
        with gzip.open(compressed_path, 'rb') as f_in:
            with open(db_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        file_size = os.path.getsize(db_path) / (1024 * 1024)
        logger.info(f"✅ Decompressed successfully! ({file_size:.1f} MB)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to decompress database: {e}")
        return False


class MaxMindGeolocator:
    """Geolocator using MaxMind GeoLite2-City database."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize with GeoLite2-City database.
        Auto-decompresses from included .gz file if needed!
        
        Args:
            db_path: Path to GeoLite2-City.mmdb file
        """
        if not GEOIP2_AVAILABLE:
            raise ImportError("geoip2 library not available")
        
        # Find database
        if db_path is None:
            # Look in local geoip directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, 'geoip', 'GeoLite2-City.mmdb')
        
        # Auto-decompress if not found but .gz exists
        if not os.path.exists(db_path):
            compressed_path = db_path + '.gz'
            if os.path.exists(compressed_path):
                logger.info(f"Database not found, but compressed version exists")
                if not decompress_geolite2_db(compressed_path, db_path):
                    raise FileNotFoundError(f"Could not decompress GeoLite2-City database")
            else:
                raise FileNotFoundError(
                    f"GeoLite2-City database not found at: {db_path}\n"
                    f"Compressed version also not found at: {compressed_path}"
                )
        
        logger.info(f"Loading GeoLite2-City database from: {db_path}")
        self.reader = geoip2.database.Reader(db_path)
        logger.info("Database loaded successfully!")
    
    def geolocate_ip(self, ip: str) -> Optional[Dict]:
        """
        Geolocate a single IP address.
        
        Args:
            ip: IP address to geolocate
            
        Returns:
            Dictionary with location data or None if not found
        """
        try:
            response = self.reader.city(ip)
            
            # Also get ASN info if available
            asn_info = {}
            try:
                asn_db_path = os.path.join(os.path.dirname(self.reader._db_reader._filename), 
                                          'GeoLite2-ASN.mmdb')
                if os.path.exists(asn_db_path):
                    asn_reader = geoip2.database.Reader(asn_db_path)
                    asn_response = asn_reader.asn(ip)
                    asn_info = {
                        'asn': f"AS{asn_response.autonomous_system_number}",
                        'asn_org': asn_response.autonomous_system_organization
                    }
                    asn_reader.close()
            except:
                pass
            
            return {
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'timezone': response.location.time_zone,
                **asn_info
            }
        except AddressNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Error geolocating {ip}: {e}")
            return None
    
    def geolocate_all_peers(self, peers: List[Dict]) -> List[Dict]:
        """
        Geolocate all peers using local database (INSTANT!).
        
        Args:
            peers: List of peer dictionaries with 'ip' field
            
        Returns:
            List of peers with updated location data
        """
        total = len(peers)
        geolocated_count = 0
        
        logger.info(f"Geolocating {total} peers using MaxMind database...")
        
        for idx, peer in enumerate(peers, 1):
            ip = peer.get('ip')
            
            if ip:
                location = self.geolocate_ip(ip)
                if location and location.get('latitude') and location.get('longitude'):
                    # Update peer with location data directly
                    peer.update({
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'country': location.get('country'),
                        'country_code': location.get('country_code'),
                        'city': location.get('city'),
                        'timezone': location.get('timezone'),
                        'asn': location.get('asn'),
                        'asn_org': location.get('asn_org')
                    })
                    geolocated_count += 1
            
            # Progress every 1000
            if idx % 1000 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx*100//total}%) - Geolocated: {geolocated_count}")
        
        logger.info(f"Geolocation complete! {geolocated_count}/{total} peers geolocated")
        return peers
    
    def close(self):
        """Close the database reader."""
        self.reader.close()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Geolocate Bitcoin peers using IP geolocation database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script uses MaxMind GeoLite2-City database for IP geolocation.
Auto-downloads database on first run (no manual setup required!).

No API rate limits - can process all 20,000+ nodes in seconds!

Examples:
  python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json
  python3 geolocate_maxmind.py --db bitcoin_peers.db  # Use database directly
        """
    )
    
    parser.add_argument('--input', type=str, default='peers.json',
                       help='Input peers.json file (default: peers.json)')
    parser.add_argument('--output', type=str, default='peers_with_locations.json',
                       help='Output file with location data (default: peers_with_locations.json)')
    parser.add_argument('--db', type=str, default='bitcoin_peers.db',
                       help='SQLite database file (default: bitcoin_peers.db)')
    parser.add_argument('--geoip-db', type=str, default=None,
                       help='Path to GeoLite2-City.mmdb (default: geoip/GeoLite2-City.mmdb)')
    parser.add_argument('--use-db', action='store_true',
                       help='Read from and write to SQLite database instead of JSON')
    parser.add_argument('--no-json', action='store_true',
                       help='Skip saving to JSON file')
    
    args = parser.parse_args()
    
    # Initialize geolocator (auto-downloads database if needed!)
    try:
        logger.info("🌍 Initializing geolocation (auto-setup enabled)")
        geolocator = MaxMindGeolocator(db_path=args.geoip_db)
    except (ImportError, FileNotFoundError) as e:
        logger.error(str(e))
        return 1
    
    # Load peers from database or JSON
    if args.use_db or (not os.path.exists(args.input) and os.path.exists(args.db)):
        # Use database
        logger.info(f"Reading from database: {args.db}")
        peers_db = PeersDatabase(args.db)
        data = peers_db.get_latest_snapshot()
        
        if not data:
            logger.error("No data found in database")
            return 1
        
        peers = data['peers']
        original_metadata = {k: v for k, v in data.items() if k != 'peers'}
        logger.info(f"Loaded {len(peers)} peers from database")
        
    else:
        # Use JSON file
        try:
            with open(args.input, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'peers' in data:
                peers = data['peers']
                original_metadata = {k: v for k, v in data.items() if k != 'peers'}
            else:
                peers = data if isinstance(data, list) else []
                original_metadata = {}
            
            logger.info(f"Loaded {len(peers)} peers from {args.input}")
            
        except FileNotFoundError:
            logger.error(f"File not found: {args.input}")
            return 1
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {args.input}: {e}")
            return 1
    
    # Geolocate all peers (modifies in place)
    geolocated_peers = geolocator.geolocate_all_peers(peers)
    geolocator.close()
    
    # Count geolocated peers
    geolocated_count = sum(1 for p in geolocated_peers 
                          if p.get('latitude') and p.get('longitude'))
    
    output_data = {
        **original_metadata,
        'peers': geolocated_peers,
        'geolocation_stats': {
            'total_peers': len(geolocated_peers),
            'geolocated': geolocated_count,
            'failed': len(geolocated_peers) - geolocated_count
        }
    }
    
    # Save to database
    if args.use_db:
        peers_db = PeersDatabase(args.db)
        snapshot_id = peers_db.save_snapshot(output_data)
        logger.info(f"Saved geolocated data to database as snapshot {snapshot_id}")
    
    # Save to JSON (unless --no-json)
    if not args.no_json:
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Saved geolocated data to {args.output}")
    
    stats = output_data['geolocation_stats']
    print(f"\n{'='*60}")
    print(f"✅ Geolocation complete!")
    print(f"Total peers: {stats['total_peers']}")
    print(f"Successfully geolocated: {stats['geolocated']}")
    print(f"Failed (private/invalid IPs): {stats['failed']}")
    if args.use_db:
        print(f"Database: {args.db}")
    if not args.no_json:
        print(f"JSON file: {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

