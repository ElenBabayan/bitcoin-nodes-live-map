#!/usr/bin/env python3
"""
Geolocate Bitcoin peers using MaxMind GeoLite2-City database.
This is INSTANT - no API rate limits!

Uses the GeoLite2-City.mmdb from bitnodes-crawler.
"""

import json
import os
import sys
import logging
from typing import Dict, List, Optional

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


class MaxMindGeolocator:
    """Geolocator using MaxMind GeoLite2-City database."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize with GeoLite2-City database.
        
        Args:
            db_path: Path to GeoLite2-City.mmdb file
        """
        if not GEOIP2_AVAILABLE:
            raise ImportError("geoip2 library not available")
        
        # Find database
        if db_path is None:
            # Look in bitnodes-crawler
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, 'bitnodes-crawler', 'geoip', 'GeoLite2-City.mmdb')
        
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"GeoLite2-City database not found at: {db_path}")
        
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
            
            return {
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'country': response.country.name,
                'countryCode': response.country.iso_code,
                'region': response.subdivisions.most_specific.name if response.subdivisions else None,
                'city': response.city.name,
                'isp': None,  # Not available in City database
                'timezone': response.location.time_zone
            }
        except AddressNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Error geolocating {ip}: {e}")
            return None
    
    def geolocate_all_peers(self, peers: List[Dict], output_file: str = None) -> List[Dict]:
        """
        Geolocate all peers using local database (INSTANT!).
        
        Args:
            peers: List of peer dictionaries with 'ip' field
            output_file: Optional file to save progress
            
        Returns:
            List of peers with added location data
        """
        total = len(peers)
        geolocated_peers = []
        geolocated_count = 0
        
        logger.info(f"Geolocating {total} peers using MaxMind database...")
        
        for idx, peer in enumerate(peers, 1):
            ip = peer.get('ip')
            peer_copy = peer.copy()
            
            if ip:
                location = self.geolocate_ip(ip)
                if location and location.get('latitude') and location.get('longitude'):
                    peer_copy['location'] = location
                    geolocated_count += 1
                else:
                    peer_copy['location'] = None
            else:
                peer_copy['location'] = None
            
            geolocated_peers.append(peer_copy)
            
            # Progress every 1000
            if idx % 1000 == 0:
                logger.info(f"Progress: {idx}/{total} ({idx*100//total}%) - Geolocated: {geolocated_count}")
        
        logger.info(f"Geolocation complete! {geolocated_count}/{total} peers geolocated")
        return geolocated_peers
    
    def close(self):
        """Close the database reader."""
        self.reader.close()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Geolocate Bitcoin peers using MaxMind GeoLite2-City database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script uses the local MaxMind GeoLite2-City database for INSTANT geolocation.
No API rate limits - can process all 20,000+ nodes in seconds!

The database is included with bitnodes-crawler in geoip/GeoLite2-City.mmdb

Examples:
  python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json
        """
    )
    
    parser.add_argument('--input', type=str, default='peers.json',
                       help='Input peers.json file (default: peers.json)')
    parser.add_argument('--output', type=str, default='peers_with_locations.json',
                       help='Output file with location data (default: peers_with_locations.json)')
    parser.add_argument('--db', type=str, default=None,
                       help='Path to GeoLite2-City.mmdb (default: bitnodes-crawler/geoip/)')
    
    args = parser.parse_args()
    
    # Load peers
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
    
    # Geolocate
    try:
        geolocator = MaxMindGeolocator(db_path=args.db)
    except (ImportError, FileNotFoundError) as e:
        logger.error(str(e))
        return 1
    
    geolocated_peers = geolocator.geolocate_all_peers(peers, args.output)
    geolocator.close()
    
    # Save results
    geolocated_count = sum(1 for p in geolocated_peers if p.get('location'))
    output_data = {
        **original_metadata,
        'peers': geolocated_peers,
        'geolocation_stats': {
            'total_peers': len(geolocated_peers),
            'geolocated': geolocated_count,
            'failed': len(geolocated_peers) - geolocated_count
        }
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    stats = output_data['geolocation_stats']
    print(f"\n{'='*60}")
    print(f"MaxMind geolocation complete!")
    print(f"Total peers: {stats['total_peers']}")
    print(f"Successfully geolocated: {stats['geolocated']}")
    print(f"Failed (private/invalid IPs): {stats['failed']}")
    print(f"Results saved to {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

