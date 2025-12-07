#!/usr/bin/env python3
"""
Fetch Bitcoin node list from bitnodes.io API.
This is a more reliable way to get a large list of Bitcoin nodes.
"""

import requests
import json
import logging
import time
from database import PeersDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_bitnodes(max_retries=3, retry_delay=5):
    """Fetch current Bitcoin nodes from bitnodes.io API with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries (doubles with each retry)
    
    Returns:
        Dictionary with peers data or None on failure
    """
    url = "https://bitnodes.io/api/v1/snapshots/latest/"
    
    logger.info(f"Fetching Bitcoin nodes from {url}")
    
    # Add headers to be more polite to the API
    headers = {
        'User-Agent': 'Bitcoin-Nodes-Live-Map/1.0 (Educational Project)',
        'Accept': 'application/json'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract node list
            nodes = data.get('nodes', {})
            
            logger.info(f"Found {len(nodes)} nodes from bitnodes.io")
            
            # Convert to our format
            peers = []
            for node_addr, node_info in nodes.items():
                try:
                    # Node address is in format "ip:port"
                    if ':' in node_addr:
                        ip, port = node_addr.rsplit(':', 1)
                        # Remove brackets from IPv6 addresses
                        ip = ip.strip('[]')
                        
                        # Filter to only IPv4 for now
                        if '.' in ip:
                            peers.append({
                                'ip': ip,
                                'port': int(port),
                                'address': node_addr,
                                'protocol': node_info[0] if node_info else None,
                                'user_agent': node_info[1] if len(node_info) > 1 else None,
                                'connected_since': node_info[2] if len(node_info) > 2 else None,
                                'services': node_info[3] if len(node_info) > 3 else None,
                                'height': node_info[4] if len(node_info) > 4 else None,
                                'city': node_info[7] if len(node_info) > 7 else None,
                                'country': node_info[8] if len(node_info) > 8 else None,
                                'latitude': node_info[9] if len(node_info) > 9 else None,
                                'longitude': node_info[10] if len(node_info) > 10 else None,
                            })
                except Exception as e:
                    logger.debug(f"Error parsing node {node_addr}: {e}")
                    continue
            
            logger.info(f"Extracted {len(peers)} IPv4 peers")
            
            return {
                'total_discovered': len(peers),
                'total_visited': 0,
                'source': 'bitnodes.io',
                'timestamp': data.get('timestamp'),
                'peers': sorted(peers, key=lambda x: x['ip'])
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limit hit
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit (429). Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("Max retries reached. Rate limit still in effect.")
                    return None
            else:
                logger.error(f"HTTP error from bitnodes.io: {e}")
                return None
        except requests.RequestException as e:
            logger.error(f"Failed to fetch from bitnodes.io: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return None
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return None
    
    return None


def main():
    """Main function."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description='Fetch Bitcoin nodes from bitnodes.io',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--output', type=str, default='peers.json',
                       help='Output JSON file (default: peers.json)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of peers to save (default: all)')
    parser.add_argument('--db', type=str, default='bitcoin_peers.db',
                       help='Database file (default: bitcoin_peers.db)')
    parser.add_argument('--no-db', action='store_true',
                       help='Skip saving to database')
    parser.add_argument('--no-json', action='store_true',
                       help='Skip saving to JSON file')
    parser.add_argument('--use-cached', action='store_true',
                       help='Use cached data from DB if available (skip API call)')
    parser.add_argument('--force-fetch', action='store_true',
                       help='Force API call even if cached data exists')
    
    args = parser.parse_args()
    
    # Check if we should use cached data
    if args.use_cached and not args.force_fetch and os.path.exists(args.db):
        try:
            db = PeersDatabase(args.db)
            cached_data = db.get_latest_snapshot()
            
            if cached_data:
                logger.info(f"✅ Using cached data from database (snapshot from {cached_data.get('created_at')})")
                logger.info(f"Found {len(cached_data['peers'])} peers in cache")
                logger.info("💡 Use --force-fetch to fetch new data from bitnodes.io")
                
                print(f"\n{'='*60}")
                print(f"✅ Using cached data!")
                print(f"Source: Database cache")
                print(f"Total peers: {len(cached_data['peers'])}")
                print(f"Snapshot date: {cached_data.get('created_at')}")
                print(f"Database: {args.db}")
                print(f"💡 Run with --force-fetch to get fresh data")
                print(f"{'='*60}")
                return 0
            else:
                logger.info("No cached data found, fetching from bitnodes.io...")
        except Exception as e:
            logger.warning(f"Could not read cached data: {e}")
            logger.info("Fetching from bitnodes.io...")
    
    # Fetch nodes from API
    results = fetch_bitnodes()
    
    if not results:
        logger.error("Failed to fetch nodes")
        return 1
    
    # Apply limit if specified
    if args.limit and results['peers']:
        results['peers'] = results['peers'][:args.limit]
        results['total_discovered'] = len(results['peers'])
    
    # Save to database (default)
    if not args.no_db:
        try:
            db = PeersDatabase(args.db)
            snapshot_id = db.save_snapshot(results)
            logger.info(f"Saved to database as snapshot {snapshot_id}")
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
    
    # Save to JSON (for backward compatibility)
    if not args.no_json:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved to JSON file: {args.output}")
        except Exception as e:
            logger.error(f"Failed to save to JSON: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ Fetch complete!")
    print(f"Source: bitnodes.io")
    print(f"Total peers: {results['total_discovered']}")
    if not args.no_db:
        print(f"Database: {args.db}")
    if not args.no_json:
        print(f"JSON file: {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    exit(main())

