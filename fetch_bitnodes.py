#!/usr/bin/env python3
"""
Fetch Bitcoin node list from bitnodes.io API.
This is a more reliable way to get a large list of Bitcoin nodes.
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_bitnodes():
    """Fetch current Bitcoin nodes from bitnodes.io API."""
    url = "https://bitnodes.io/api/v1/snapshots/latest/"
    
    logger.info(f"Fetching Bitcoin nodes from {url}")
    
    try:
        response = requests.get(url, timeout=30)
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
        
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from bitnodes.io: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return None


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Bitcoin nodes from bitnodes.io',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--output', type=str, default='peers.json',
                       help='Output file (default: peers.json)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of peers to save (default: all)')
    
    args = parser.parse_args()
    
    # Fetch nodes
    results = fetch_bitnodes()
    
    if not results:
        logger.error("Failed to fetch nodes")
        return 1
    
    # Apply limit if specified
    if args.limit and results['peers']:
        results['peers'] = results['peers'][:args.limit]
        results['total_discovered'] = len(results['peers'])
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Fetch complete!")
    print(f"Source: bitnodes.io")
    print(f"Total peers: {results['total_discovered']}")
    print(f"Results saved to {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    exit(main())

