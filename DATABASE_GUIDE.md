# Database Guide

## Overview

This project uses **SQLite** to store Bitcoin peer data efficiently. The database approach offers several advantages over large JSON files:

- ✅ **Commitable**: Database file is much smaller than JSON (can be committed to git)
- ✅ **Fast queries**: Query specific data without loading everything
- ✅ **Versioned snapshots**: Keep multiple crawls and compare over time
- ✅ **No server needed**: SQLite is just a file (included in Python)

## Database Schema

### `snapshots` Table
Stores metadata about each crawl:
- `id`: Unique snapshot ID
- `timestamp`: Unix timestamp from bitnodes
- `source`: Data source (e.g., "bitnodes.io")
- `total_discovered`: Number of peers discovered
- `total_visited`: Number of peers visited
- `created_at`: When the snapshot was created

### `peers` Table
Stores individual peer information:
- `id`: Unique peer ID
- `snapshot_id`: Links to snapshot
- `ip`: IP address
- `port`: Port number
- `address`: Full address (ip:port)
- `protocol`: Protocol version
- `user_agent`: Client software
- `connected_since`: Connection timestamp
- `services`: Node services
- `height`: Blockchain height
- `city`: City name (from geolocation)
- `country`: Country name
- `country_code`: ISO country code
- `latitude`: Geographic latitude
- `longitude`: Geographic longitude
- `timezone`: Timezone
- `asn`: Autonomous System Number
- `asn_org`: ASN organization name

## Usage

### Automatic (Recommended)

The pipeline script automatically uses the database:

```bash
./run_pipeline.sh
```

This will:
1. Fetch nodes → save to database
2. Geolocate nodes → update database
3. Visualize → read from database

### Manual Usage

#### 1. Fetch Nodes

```bash
# Save to database (default)
python3 fetch_bitnodes.py --db bitcoin_peers.db

# Also save JSON for backward compatibility
python3 fetch_bitnodes.py --db bitcoin_peers.db --output peers.json
```

#### 2. Geolocate Nodes

```bash
# Read from and write to database
python3 geolocate_maxmind.py --db bitcoin_peers.db --use-db --no-json

# Or use JSON files (legacy)
python3 geolocate_maxmind.py --input peers.json --output peers_with_locations.json
```

#### 3. Visualize

```bash
# Read from database
python3 visualize_peers_map.py --db bitcoin_peers.db --use-db

# Or use JSON file (legacy)
python3 visualize_peers_map.py --input peers_with_locations.json
```

## Database Management

The `database.py` module provides management tools:

### View Statistics

```bash
python3 database.py --db bitcoin_peers.db --stats
```

Output:
```
📊 Database Statistics:
   Total snapshots: 5
   Total peers: 125,432
   Countries: 87
```

### List Snapshots

```bash
python3 database.py --db bitcoin_peers.db --list
```

Output:
```
📋 Available Snapshots:
   ID 5: bitnodes.io - 25,086 peers - 2025-12-07 17:00:00
   ID 4: bitnodes.io - 24,872 peers - 2025-12-06 15:30:00
   ID 3: bitnodes.io - 25,201 peers - 2025-12-05 12:00:00
```

### Export Snapshot to JSON

```bash
python3 database.py --db bitcoin_peers.db --export 5
```

Creates `snapshot_5.json` with all data.

### Import JSON to Database

```bash
python3 database.py --db bitcoin_peers.db --import peers.json
```

## Programmatic Usage

```python
from database import PeersDatabase

# Initialize database
db = PeersDatabase('bitcoin_peers.db')

# Save a snapshot
data = {
    'timestamp': 1701964800,
    'source': 'bitnodes.io',
    'total_discovered': 25000,
    'total_visited': 0,
    'peers': [...]
}
snapshot_id = db.save_snapshot(data)

# Get latest snapshot
latest = db.get_latest_snapshot()
print(f"Latest snapshot has {len(latest['peers'])} peers")

# Get specific snapshot
snapshot = db.get_snapshot_by_id(5)

# List all snapshots
snapshots = db.list_snapshots()

# Get statistics
stats = db.get_stats()
print(f"Total peers across all snapshots: {stats['total_peers']}")

# Clean up old snapshots (keep latest 5)
db.delete_old_snapshots(keep_latest=5)
```

## Why SQLite Instead of JSON?

| Feature | SQLite | JSON Files |
|---------|--------|-----------|
| File size | ~5-10 MB | ~50-100 MB |
| Load time | Instant (query only what you need) | Slow (load entire file) |
| Git-friendly | ✅ Yes | ❌ Too large |
| Query specific data | ✅ Fast | ❌ Load everything |
| Version history | ✅ Built-in snapshots | ❌ Manual |
| Setup required | ❌ No (built into Python) | ❌ No |

## Migration from JSON

If you have existing JSON files:

```bash
# Import existing data
python3 database.py --db bitcoin_peers.db --import peers.json
python3 database.py --db bitcoin_peers.db --import peers_with_locations.json

# Verify import
python3 database.py --db bitcoin_peers.db --stats --list
```

The JSON files are still supported for backward compatibility, but the database is now the default.

## Best Practices

1. **Commit the database**: The `.db` file is small enough to commit to git
2. **Keep multiple snapshots**: Track network changes over time
3. **Clean up old data**: Use `delete_old_snapshots()` to save space
4. **Export for sharing**: Use `--export` to create JSON for external tools

## Database File Size

Typical sizes:
- 1 snapshot (~25k peers): ~2-3 MB
- 5 snapshots: ~10-15 MB  
- 10 snapshots: ~20-30 MB

This is much smaller than JSON files (50-100 MB per snapshot) and includes indexes for fast queries.

