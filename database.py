#!/usr/bin/env python3
"""
Database module for storing Bitcoin node data.
Uses SQLite for efficient storage that can be committed to git.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PeersDatabase:
    """Database for storing and retrieving Bitcoin peer data."""
    
    def __init__(self, db_path: str = "bitcoin_peers.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create snapshots table to track different crawls
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    source TEXT,
                    total_discovered INTEGER,
                    total_visited INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create peers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS peers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER,
                    ip TEXT NOT NULL,
                    port INTEGER,
                    address TEXT,
                    protocol INTEGER,
                    user_agent TEXT,
                    connected_since INTEGER,
                    services TEXT,
                    height INTEGER,
                    city TEXT,
                    country TEXT,
                    country_code TEXT,
                    latitude REAL,
                    longitude REAL,
                    timezone TEXT,
                    asn TEXT,
                    asn_org TEXT,
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_peers_snapshot 
                ON peers(snapshot_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_peers_ip 
                ON peers(ip)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_peers_country 
                ON peers(country_code)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_peers_location 
                ON peers(latitude, longitude)
            """)
            
            logger.info(f"Database initialized at {self.db_path}")
    
    def save_snapshot(self, data: Dict) -> int:
        """Save a complete snapshot of peers data.
        
        Args:
            data: Dictionary containing 'peers' list and metadata
            
        Returns:
            snapshot_id: ID of the created snapshot
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create snapshot record
            cursor.execute("""
                INSERT INTO snapshots (timestamp, source, total_discovered, total_visited)
                VALUES (?, ?, ?, ?)
            """, (
                data.get('timestamp'),
                data.get('source', 'unknown'),
                data.get('total_discovered', 0),
                data.get('total_visited', 0)
            ))
            
            snapshot_id = cursor.lastrowid
            
            # Insert all peers
            peers = data.get('peers', [])
            for peer in peers:
                cursor.execute("""
                    INSERT INTO peers (
                        snapshot_id, ip, port, address, protocol, user_agent,
                        connected_since, services, height, city, country, 
                        country_code, latitude, longitude, timezone, asn, asn_org
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot_id,
                    peer.get('ip'),
                    peer.get('port'),
                    peer.get('address'),
                    peer.get('protocol'),
                    peer.get('user_agent'),
                    peer.get('connected_since'),
                    peer.get('services'),
                    peer.get('height'),
                    peer.get('city'),
                    peer.get('country'),
                    peer.get('country_code'),
                    peer.get('latitude'),
                    peer.get('longitude'),
                    peer.get('timezone'),
                    peer.get('asn'),
                    peer.get('asn_org')
                ))
            
            logger.info(f"Saved snapshot {snapshot_id} with {len(peers)} peers")
            return snapshot_id
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent snapshot with all peers.
        
        Returns:
            Dictionary containing snapshot metadata and peers list
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get latest snapshot
            cursor.execute("""
                SELECT * FROM snapshots 
                ORDER BY created_at DESC 
                LIMIT 1
            """)
            
            snapshot_row = cursor.fetchone()
            if not snapshot_row:
                logger.warning("No snapshots found in database")
                return None
            
            snapshot = dict(snapshot_row)
            snapshot_id = snapshot['id']
            
            # Get all peers for this snapshot
            cursor.execute("""
                SELECT * FROM peers 
                WHERE snapshot_id = ?
                ORDER BY ip
            """, (snapshot_id,))
            
            peers = []
            for row in cursor.fetchall():
                peer = dict(row)
                # Remove internal fields
                peer.pop('id', None)
                peer.pop('snapshot_id', None)
                peers.append(peer)
            
            result = {
                'timestamp': snapshot['timestamp'],
                'source': snapshot['source'],
                'total_discovered': snapshot['total_discovered'],
                'total_visited': snapshot['total_visited'],
                'created_at': snapshot['created_at'],
                'peers': peers
            }
            
            logger.info(f"Retrieved snapshot {snapshot_id} with {len(peers)} peers")
            return result
    
    def get_snapshot_by_id(self, snapshot_id: int) -> Optional[Dict]:
        """Get a specific snapshot by ID.
        
        Args:
            snapshot_id: ID of the snapshot to retrieve
            
        Returns:
            Dictionary containing snapshot metadata and peers list
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,))
            snapshot_row = cursor.fetchone()
            
            if not snapshot_row:
                logger.warning(f"Snapshot {snapshot_id} not found")
                return None
            
            snapshot = dict(snapshot_row)
            
            cursor.execute("""
                SELECT * FROM peers 
                WHERE snapshot_id = ?
                ORDER BY ip
            """, (snapshot_id,))
            
            peers = []
            for row in cursor.fetchall():
                peer = dict(row)
                peer.pop('id', None)
                peer.pop('snapshot_id', None)
                peers.append(peer)
            
            return {
                'timestamp': snapshot['timestamp'],
                'source': snapshot['source'],
                'total_discovered': snapshot['total_discovered'],
                'total_visited': snapshot['total_visited'],
                'created_at': snapshot['created_at'],
                'peers': peers
            }
    
    def list_snapshots(self) -> List[Dict]:
        """List all available snapshots.
        
        Returns:
            List of snapshot metadata dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, COUNT(p.id) as peer_count
                FROM snapshots s
                LEFT JOIN peers p ON s.id = p.snapshot_id
                GROUP BY s.id
                ORDER BY s.created_at DESC
            """)
            
            snapshots = []
            for row in cursor.fetchall():
                snapshots.append(dict(row))
            
            return snapshots
    
    def get_stats(self) -> Dict:
        """Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM snapshots")
            snapshot_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM peers")
            peer_count = cursor.fetchone()['count']
            
            cursor.execute("""
                SELECT COUNT(DISTINCT country_code) as count 
                FROM peers 
                WHERE country_code IS NOT NULL
            """)
            country_count = cursor.fetchone()['count']
            
            return {
                'total_snapshots': snapshot_count,
                'total_peers': peer_count,
                'countries_represented': country_count
            }
    
    def delete_old_snapshots(self, keep_latest: int = 5):
        """Delete old snapshots, keeping only the most recent ones.
        
        Args:
            keep_latest: Number of snapshots to keep
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get IDs of snapshots to delete
            cursor.execute("""
                SELECT id FROM snapshots 
                ORDER BY created_at DESC 
                LIMIT -1 OFFSET ?
            """, (keep_latest,))
            
            old_ids = [row['id'] for row in cursor.fetchall()]
            
            if old_ids:
                placeholders = ','.join('?' * len(old_ids))
                cursor.execute(f"DELETE FROM peers WHERE snapshot_id IN ({placeholders})", old_ids)
                cursor.execute(f"DELETE FROM snapshots WHERE id IN ({placeholders})", old_ids)
                
                logger.info(f"Deleted {len(old_ids)} old snapshots")
            else:
                logger.info("No old snapshots to delete")


def main():
    """Test the database functionality."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bitcoin Peers Database Manager')
    parser.add_argument('--db', default='bitcoin_peers.db', help='Database file path')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--list', action='store_true', help='List all snapshots')
    parser.add_argument('--export', type=int, metavar='ID', help='Export snapshot to JSON')
    parser.add_argument('--import', type=str, metavar='FILE', dest='import_file', 
                       help='Import JSON file to database')
    
    args = parser.parse_args()
    
    db = PeersDatabase(args.db)
    
    if args.stats:
        stats = db.get_stats()
        print("\n📊 Database Statistics:")
        print(f"   Total snapshots: {stats['total_snapshots']}")
        print(f"   Total peers: {stats['total_peers']}")
        print(f"   Countries: {stats['countries_represented']}")
        print()
    
    if args.list:
        snapshots = db.list_snapshots()
        print("\n📋 Available Snapshots:")
        for snap in snapshots:
            print(f"   ID {snap['id']}: {snap['source']} - "
                  f"{snap['peer_count']} peers - {snap['created_at']}")
        print()
    
    if args.export:
        data = db.get_snapshot_by_id(args.export)
        if data:
            filename = f"snapshot_{args.export}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Exported snapshot {args.export} to {filename}")
        else:
            print(f"❌ Snapshot {args.export} not found")
    
    if args.import_file:
        with open(args.import_file, 'r') as f:
            data = json.load(f)
        snapshot_id = db.save_snapshot(data)
        print(f"✅ Imported {args.import_file} as snapshot {snapshot_id}")


if __name__ == '__main__':
    main()


