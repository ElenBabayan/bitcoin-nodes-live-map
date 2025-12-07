#!/usr/bin/env python3
"""
Fetch Bitcoin node data from bitnodes.io API and store in database.
This is the initial data collection step.
"""

import json
import logging
import requests
from database import PeersDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_from_bitnodes_api():
    """Fetch Bitcoin nodes from bitnodes.io API.
    
    Returns:
        Dictionary with peers data or None on failure
    """
    url = "https://bitnodes.io/api/v1/snapshots/latest/"
    
    try:
        logger.info("Fetching latest snapshot from bitnodes.io API...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Transform API response to our format
        peers = []
        nodes_dict = data.get('nodes', {})
        
        logger.info(f"Processing {len(nodes_dict)} nodes...")
        
        for node_key, node_data in nodes_dict.items():
            # node_key format: "ip:port" or "[ipv6]:port"
            # Handle IPv6: [2001:db8::1]:8333
            # Handle IPv4: 192.168.1.1:8333
            # Handle onion: xxx.onion:8333
            
            if node_key.startswith('['):
                # IPv6 format: [address]:port
                bracket_end = node_key.rfind(']')
                if bracket_end != -1:
                    ip = node_key[1:bracket_end]  # Remove brackets
                    port_str = node_key[bracket_end+2:] if bracket_end+2 < len(node_key) else '8333'
                    try:
                        port = int(port_str)
                    except ValueError:
                        port = 8333
                else:
                    ip = node_key
                    port = 8333
            else:
                # IPv4 or hostname format
                last_colon = node_key.rfind(':')
                if last_colon != -1:
                    ip = node_key[:last_colon]
                    port_str = node_key[last_colon+1:]
                    try:
                        port = int(port_str)
                    except ValueError:
                        port = 8333
                else:
                    ip = node_key
                    port = 8333
            
            peer = {
                'ip': ip,
                'port': port,
                'protocol_version': node_data[0] if len(node_data) > 0 else None,
                'user_agent': node_data[1] if len(node_data) > 1 else None,
                'connected_since': node_data[2] if len(node_data) > 2 else None,
                'services': node_data[3] if len(node_data) > 3 else None,
                'height': node_data[4] if len(node_data) > 4 else None,
                'hostname': node_data[5] if len(node_data) > 5 else None,
                'city': node_data[6] if len(node_data) > 6 else None,
                'country_code': node_data[7] if len(node_data) > 7 else None,
                'latitude': node_data[8] if len(node_data) > 8 else None,
                'longitude': node_data[9] if len(node_data) > 9 else None,
                'timezone': node_data[10] if len(node_data) > 10 else None,
                'asn': node_data[11] if len(node_data) > 11 else None,
                'org': node_data[12] if len(node_data) > 12 else None,
            }
            peers.append(peer)
        
        result = {
            'source': 'bitnodes.io',
            'timestamp': data.get('timestamp'),
            'total_nodes': data.get('total_nodes', len(peers)),
            'latest_height': data.get('latest_height'),
            'total_discovered': len(peers),
            'peers': peers
        }
        
        logger.info(f"✅ Successfully fetched {len(peers)} nodes")
        logger.info(f"   Total nodes in network: {result['total_nodes']}")
        logger.info(f"   Latest block height: {result['latest_height']}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch from API: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing API response: {e}")
        return None


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Bitcoin nodes from bitnodes.io API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script fetches Bitcoin peer data from bitnodes.io API and stores it in SQLite database.

Examples:
  python3 fetch_from_api.py --db bitcoin_peers.db
  python3 fetch_from_api.py --db bitcoin_peers.db --output peers.json
        """
    )
    
    parser.add_argument('--output', type=str, default=None,
                       help='Optional: Also export to JSON file')
    parser.add_argument('--db', type=str, default='bitcoin_peers.db',
                       help='Database file (default: bitcoin_peers.db)')
    
    args = parser.parse_args()
    
    # Fetch from API
    results = fetch_from_bitnodes_api()
    
    if not results:
        logger.error("Failed to fetch nodes from API")
        return 1
    
    # Save to database
    try:
        db = PeersDatabase(args.db)
        snapshot_id = db.save_snapshot(results)
        logger.info(f"✅ Saved to database as snapshot {snapshot_id}")
        logger.info(f"   Database: {args.db}")
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        return 1
    
    # Export to JSON if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"✅ Also exported to JSON: {args.output}")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return 1
    
    print(f"\n{'='*60}")
    print(f"✅ Data fetched and stored successfully!")
    print(f"Source: {results.get('source')}")
    print(f"Total peers: {len(results.get('peers', []))}")
    print(f"Database: {args.db}")
    if args.output:
        print(f"JSON export: {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    exit(main())

