#!/usr/bin/env python3
"""
Load Bitcoin node data from local database.
No external API calls - uses cached data only.
"""

import json
import logging
import os
from database import PeersDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_from_database(db_path='bitcoin_peers.db'):
    """Load Bitcoin nodes from local database.
    
    Args:
        db_path: Path to SQLite database file
    
    Returns:
        Dictionary with peers data or None if database doesn't exist
    """
    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        logger.info("Database must exist with peer data.")
        return None
    
    try:
        db = PeersDatabase(db_path)
        data = db.get_latest_snapshot()
        
        if not data:
            logger.error("No snapshots found in database")
            return None
        
        logger.info(f"✅ Loaded snapshot from {data.get('created_at')}")
        logger.info(f"   Source: {data.get('source', 'unknown')}")
        logger.info(f"   Peers: {len(data.get('peers', []))}")
        
        return data
        
    except Exception as e:
        logger.error(f"Failed to load from database: {e}")
        return None


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Load Bitcoin nodes from local database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script loads Bitcoin peer data from the local SQLite database.
No external API calls are made - uses cached data only.

Examples:
  python3 fetch_bitnodes.py --db bitcoin_peers.db
  python3 fetch_bitnodes.py --db bitcoin_peers.db --output peers.json
        """
    )
    
    parser.add_argument('--output', type=str, default=None,
                       help='Optional: Export to JSON file')
    parser.add_argument('--db', type=str, default='bitcoin_peers.db',
                       help='Database file (default: bitcoin_peers.db)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of peers (default: all)')
    
    args = parser.parse_args()
    
    # Load from database
    logger.info(f"Loading Bitcoin nodes from database: {args.db}")
    results = load_from_database(args.db)
    
    if not results:
        logger.error("Failed to load nodes from database")
        logger.info("Make sure bitcoin_peers.db exists with peer data")
        return 1
    
    # Apply limit if specified
    if args.limit and results.get('peers'):
        results['peers'] = results['peers'][:args.limit]
        results['total_discovered'] = len(results['peers'])
    
    # Export to JSON if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"✅ Exported to JSON file: {args.output}")
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return 1
    
    print(f"\n{'='*60}")
    print(f"✅ Data loaded from database!")
    print(f"Source: {results.get('source', 'database')}")
    print(f"Snapshot date: {results.get('created_at')}")
    print(f"Total peers: {len(results.get('peers', []))}")
    print(f"Database: {args.db}")
    if args.output:
        print(f"Exported to: {args.output}")
    print(f"{'='*60}")
    
    return 0


if __name__ == '__main__':
    exit(main())
