#!/usr/bin/env python3
"""
Geolocate Bitcoin peers using MaxMind GeoLite2-City database.
Designed to work with the DuckDB crawler database.

INSTANT geolocation - no API rate limits!
Uses the local MaxMind GeoLite2-City.mmdb database.
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import BitcoinNodesDB

# Try to import geoip2
try:
    import geoip2.database
    from geoip2.errors import AddressNotFoundError
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False
    logger.error("geoip2 not installed. Run: pip install geoip2")


class BitcoinNodeGeolocator:
    """
    Geolocator for Bitcoin nodes using MaxMind GeoLite2-City database.
    Updates geolocation data directly in Redis.
    """
    
    def __init__(self, geoip_db_path: str = None, redis_host: str = None, redis_port: int = None, redis_db: int = None):
        """
        Initialize with database connections.
        
        Args:
            geoip_db_path: Path to GeoLite2-City.mmdb file
            redis_host: Redis host (default: localhost)
            redis_port: Redis port (default: 6379)
            redis_db: Redis database number (default: 1)
        """
        if not GEOIP2_AVAILABLE:
            raise ImportError("geoip2 library not available. Install with: pip install geoip2")
        
        # Find GeoIP database
        if geoip_db_path is None:
            # Look in bitnodes-crawler first
            script_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.join(script_dir, '..', 'bitnodes-crawler', 'geoip', 'GeoLite2-City.mmdb'),
                os.path.join(script_dir, '..', 'geoip', 'GeoLite2-City.mmdb'),
                os.path.join(script_dir, 'geoip', 'GeoLite2-City.mmdb'),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    geoip_db_path = os.path.abspath(path)
                    break
        
        if not geoip_db_path or not os.path.exists(geoip_db_path):
            raise FileNotFoundError(
                f"GeoLite2-City database not found. Searched: {possible_paths}"
            )
        
        logger.info(f"📍 Loading GeoLite2-City database from: {geoip_db_path}")
        self.geoip_reader = geoip2.database.Reader(geoip_db_path)
        
        # Try to load ASN database for ISP info
        self.asn_reader = None
        asn_path = geoip_db_path.replace('City', 'ASN')
        if os.path.exists(asn_path):
            self.asn_reader = geoip2.database.Reader(asn_path)
            logger.info(f"📡 Loaded ASN database from: {asn_path}")
        
        # Connect to Redis
        self.db = BitcoinNodesDB(host=redis_host, port=redis_port, db=redis_db)
        logger.info("✅ GeoIP databases loaded successfully!")
    
    def geolocate_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """
        Geolocate a single IP address.
        
        Args:
            ip: IP address to geolocate
            
        Returns:
            Dictionary with location data or None if not found
        """
        try:
            response = self.geoip_reader.city(ip)
            
            location = {
                'ip': ip,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'region': response.subdivisions.most_specific.name if response.subdivisions else None,
                'timezone': response.location.time_zone,
                'asn': None,
                'isp': None
            }
            
            # Try to get ASN/ISP info
            if self.asn_reader:
                try:
                    asn_response = self.asn_reader.asn(ip)
                    location['asn'] = asn_response.autonomous_system_number
                    location['isp'] = asn_response.autonomous_system_organization
                except:
                    pass
            
            return location
            
        except AddressNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Error geolocating {ip}: {e}")
            return None
    
    def geolocate_all_peers(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Geolocate all peers in the database that don't have location data.
        Updates DuckDB directly for efficiency.
        
        Args:
            batch_size: Number of peers to process in each batch
            
        Returns:
            Statistics dictionary
        """
        # Get peers needing geolocation
        peers = self.db.get_peers_for_geolocation()
        total = len(peers)
        
        if total == 0:
            logger.info("📍 All peers already geolocated!")
            return {'total': 0, 'geolocated': 0, 'failed': 0}
        
        logger.info(f"📍 Geolocating {total:,} peers using MaxMind database...")
        
        geolocated_count = 0
        failed_count = 0
        batch = []
        
        for idx, peer in enumerate(peers, 1):
            ip = peer['ip']
            location = self.geolocate_ip(ip)
            
            if location and location.get('latitude') and location.get('longitude'):
                batch.append(location)
                geolocated_count += 1
            else:
                failed_count += 1
            
            # Process batch
            if len(batch) >= batch_size:
                self.db.update_geolocation_batch(batch)
                batch = []
                logger.info(
                    f"   Progress: {idx:,}/{total:,} ({idx*100//total}%) - "
                    f"Geolocated: {geolocated_count:,}"
                )
        
        # Process remaining batch
        if batch:
            self.db.update_geolocation_batch(batch)
        
        logger.info(f"✅ Geolocation complete! {geolocated_count:,}/{total:,} peers geolocated")
        
        return {
            'total': total,
            'geolocated': geolocated_count,
            'failed': failed_count
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get geolocation statistics."""
        return self.db.get_stats_summary()
    
    def close(self):
        """Close database connections."""
        self.geoip_reader.close()
        if self.asn_reader:
            self.asn_reader.close()
        self.db.close()
        logger.info("📍 GeoIP connections closed")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Geolocate Bitcoin peers using MaxMind GeoLite2-City database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script uses the local MaxMind GeoLite2-City database for INSTANT geolocation.
No API rate limits - can process all discovered nodes in seconds!

The database is included with bitnodes-crawler in geoip/GeoLite2-City.mmdb

Examples:
  # Geolocate all peers (using Redis):
  python3 geolocate.py
  
  # Use custom GeoIP database:
  python3 geolocate.py --geoip-path /path/to/GeoLite2-City.mmdb

Environment Variables:
  REDIS_HOST  - Redis host (default: localhost)
  REDIS_PORT  - Redis port (default: 6379)
  REDIS_DB    - Redis database (default: 1)
        """
    )
    
    parser.add_argument('--geoip-path', type=str, default=None,
                       help='Path to GeoLite2-City.mmdb')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for database updates (default: 1000)')
    
    args = parser.parse_args()
    
    try:
        geolocator = BitcoinNodeGeolocator(
            geoip_db_path=args.geoip_path
        )
    except (ImportError, FileNotFoundError) as e:
        logger.error(str(e))
        return 1
    
    try:
        # Run geolocation
        stats = geolocator.geolocate_all_peers(batch_size=args.batch_size)
        
        # Get full stats
        full_stats = geolocator.get_stats()
        
        # Print summary
        print()
        print("╔" + "═" * 60 + "╗")
        print("║" + "  📍 GEOLOCATION COMPLETE!".center(60) + "║")
        print("╠" + "═" * 60 + "╣")
        print(f"║  Total peers processed: {stats['total']:,}".ljust(61) + "║")
        print(f"║  Successfully geolocated: {stats['geolocated']:,}".ljust(61) + "║")
        print(f"║  Failed (private/invalid): {stats['failed']:,}".ljust(61) + "║")
        print("╠" + "═" * 60 + "╣")
        print(f"║  Total peers in database: {full_stats['total_peers']:,}".ljust(61) + "║")
        print(f"║  Geolocated peers: {full_stats['geolocated_peers']:,}".ljust(61) + "║")
        print(f"║  Countries represented: {full_stats['countries']}".ljust(61) + "║")
        print("╠" + "═" * 60 + "╣")
        print("║  🚀 Next step: Run visualize.py to create heatmap!".ljust(61) + "║")
        print("╚" + "═" * 60 + "╝")
        
    finally:
        geolocator.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

