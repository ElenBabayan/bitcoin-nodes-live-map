#!/usr/bin/env python3
"""
Geolocation script for Bitcoin peers.
Adds location data (latitude, longitude, country, city) to peers.json
using IP geolocation API.
"""

import json
import time
import requests
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PeerGeolocator:
    """Geolocates IP addresses using ip-api.com (free tier)."""
    
    def __init__(self, rate_limit_delay=0.2):
        """
        Initialize geolocator.
        
        Args:
            rate_limit_delay: Delay between API calls in seconds (ip-api.com allows 45 req/min)
        """
        self.rate_limit_delay = rate_limit_delay
        self.api_url = "http://ip-api.com/json/{ip}"
        self.cache = {}  # Cache for already geolocated IPs
    
    def geolocate_ip(self, ip: str) -> Optional[Dict]:
        """
        Get geolocation data for an IP address.
        
        Args:
            ip: IP address to geolocate
            
        Returns:
            Dictionary with location data or None if failed
        """
        # Check cache first
        if ip in self.cache:
            return self.cache[ip]
        
        try:
            url = self.api_url.format(ip=ip)
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    location_data = {
                        'latitude': data.get('lat'),
                        'longitude': data.get('lon'),
                        'country': data.get('country'),
                        'countryCode': data.get('countryCode'),
                        'region': data.get('regionName'),
                        'city': data.get('city'),
                        'isp': data.get('isp'),
                        'timezone': data.get('timezone')
                    }
                    self.cache[ip] = location_data
                    return location_data
                else:
                    logger.warning(f"Failed to geolocate {ip}: {data.get('message', 'Unknown error')}")
                    return None
            else:
                logger.warning(f"API error for {ip}: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error geolocating {ip}: {e}")
            return None
        
        finally:
            # Rate limiting
            time.sleep(self.rate_limit_delay)
    
    def geolocate_peers(self, peers: List[Dict], output_file: str = None) -> List[Dict]:
        """
        Geolocate a list of peers.
        
        Args:
            peers: List of peer dictionaries with 'ip' field
            output_file: Optional file to save progress incrementally
            
        Returns:
            List of peers with added location data
        """
        total = len(peers)
        geolocated_peers = []
        
        logger.info(f"Starting geolocation for {total} peers...")
        
        for idx, peer in enumerate(peers, 1):
            ip = peer.get('ip')
            if not ip:
                logger.warning(f"Peer {idx} missing IP address, skipping")
                geolocated_peers.append(peer)
                continue
            
            logger.info(f"Geolocating {ip} ({idx}/{total})...")
            location = self.geolocate_ip(ip)
            
            # Add location data to peer
            peer_with_location = peer.copy()
            if location:
                peer_with_location['location'] = location
            else:
                peer_with_location['location'] = None
            
            geolocated_peers.append(peer_with_location)
            
            # Save progress incrementally
            if output_file and idx % 10 == 0:
                self._save_progress(geolocated_peers, output_file, idx, total)
        
        logger.info(f"Geolocation complete! Processed {total} peers")
        return geolocated_peers
    
    def _save_progress(self, peers: List[Dict], output_file: str, current: int, total: int):
        """Save progress to file."""
        try:
            with open(output_file, 'w') as f:
                json.dump({
                    'total_geolocated': current,
                    'total_peers': total,
                    'peers': peers
                }, f, indent=2)
            logger.info(f"Progress saved: {current}/{total} peers geolocated")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Geolocate Bitcoin peers from peers.json',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--input', type=str, default='peers.json',
                       help='Input peers.json file (default: peers.json)')
    parser.add_argument('--output', type=str, default='peers_with_locations.json',
                       help='Output file with location data (default: peers_with_locations.json)')
    parser.add_argument('--rate-limit', type=float, default=0.2,
                       help='Delay between API calls in seconds (default: 0.2)')
    
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
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {args.input}: {e}")
        return
    
    # Geolocate peers
    geolocator = PeerGeolocator(rate_limit_delay=args.rate_limit)
    geolocated_peers = geolocator.geolocate_peers(peers, args.output)
    
    # Save results
    output_data = {
        **original_metadata,
        'peers': geolocated_peers,
        'geolocation_stats': {
            'total_peers': len(geolocated_peers),
            'geolocated': sum(1 for p in geolocated_peers if p.get('location')),
            'failed': sum(1 for p in geolocated_peers if not p.get('location'))
        }
    }
    
    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    stats = output_data['geolocation_stats']
    print(f"\n{'='*60}")
    print(f"Geolocation complete!")
    print(f"Total peers: {stats['total_peers']}")
    print(f"Successfully geolocated: {stats['geolocated']}")
    print(f"Failed: {stats['failed']}")
    print(f"Results saved to {args.output}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
