#!/usr/bin/env python3
"""
Visualize Bitcoin peers on an interactive map.
Requires peers_with_locations.json (created by geolocate_peers.py)
"""

import json
import os
import folium
from folium.plugins import MarkerCluster, HeatMap
from collections import Counter
import logging
from database import PeersDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_peers_map(peers_data: dict, output_file: str = 'bitcoin_peers_map.html', enable_heatmap: bool = True):
    """
    Create an interactive map showing Bitcoin peer locations.
    
    Args:
        peers_data: Dictionary with 'peers' list containing peer data with location
        output_file: Output HTML file path
        enable_heatmap: Whether to add heatmap layer (default: True)
    """
    peers = peers_data.get('peers', [])
    
    # Filter peers with valid location data
    geolocated_peers = [
        p for p in peers 
        if p.get('latitude') and p.get('longitude')
    ]
    
    if not geolocated_peers:
        logger.error("No peers with valid location data found!")
        logger.info("Please run geolocate_maxmind.py first to add location data.")
        return
    
    logger.info(f"Creating map with {len(geolocated_peers)} geolocated peers...")
    
    # Calculate center point (average of all locations)
    lats = [p['latitude'] for p in geolocated_peers]
    lons = [p['longitude'] for p in geolocated_peers]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=2,
        tiles='OpenStreetMap'
    )
    
    # Add different tile layers
    folium.TileLayer('CartoDB positron').add_to(m)
    folium.TileLayer('CartoDB dark_matter').add_to(m)
    
    # Prepare heatmap data
    heat_data = []
    for peer in geolocated_peers:
        lat = peer['latitude']
        lon = peer['longitude']
        heat_data.append([lat, lon])
    
    # Add heatmap layer if enabled
    if enable_heatmap:
        heat_layer = HeatMap(
            heat_data,
            name='Heatmap',
            min_opacity=0.3,
            max_zoom=18,
            radius=15,
            blur=20,
            gradient={0.2: 'blue', 0.4: 'cyan', 0.6: 'lime', 0.8: 'yellow', 1.0: 'red'}
        )
        heat_layer.add_to(m)
    
    # Create marker cluster for better performance
    marker_cluster = MarkerCluster(name='Markers', show=not enable_heatmap).add_to(m)
    
    # Count peers by country for statistics
    country_counts = Counter()
    city_counts = Counter()
    
    # Add markers for each peer
    for peer in geolocated_peers:
        ip = peer.get('ip', 'Unknown')
        port = peer.get('port', 'Unknown')
        
        lat = peer['latitude']
        lon = peer['longitude']
        country = peer.get('country', 'Unknown')
        city = peer.get('city', 'Unknown')
        asn = peer.get('asn', 'Unknown')
        asn_org = peer.get('asn_org', 'Unknown')
        
        country_counts[country] += 1
        if city and city != 'Unknown':
            city_counts[f"{city}, {country}"] += 1
        
        # Create popup content
        popup_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 10px 0; color: #1a1a1a;">Bitcoin Peer</h4>
            <p style="margin: 5px 0;"><strong>IP:</strong> {ip}</p>
            <p style="margin: 5px 0;"><strong>Port:</strong> {port}</p>
            <p style="margin: 5px 0;"><strong>Address:</strong> {ip}:{port}</p>
            <hr style="margin: 10px 0;">
            <p style="margin: 5px 0;"><strong>Location:</strong></p>
            <p style="margin: 5px 0;">{city}</p>
            <p style="margin: 5px 0;">{country}</p>
            <p style="margin: 5px 0;"><strong>ASN:</strong> {asn}</p>
            <p style="margin: 5px 0;"><strong>ISP:</strong> {asn_org}</p>
        </div>
        """
        
        # Create marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{ip} - {city}, {country}",
            icon=folium.Icon(color='blue', icon='server', prefix='fa')
        ).add_to(marker_cluster)
    
    # Add statistics layer
    stats_html = f"""
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 300px; height: auto; 
                background-color: white; z-index:9999; 
                padding: 15px; border-radius: 5px; 
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                font-family: Arial, sans-serif; font-size: 12px;">
        <h3 style="margin: 0 0 10px 0; color: #1a1a1a;">Bitcoin Network Stats</h3>
        <p style="margin: 5px 0;"><strong>Total Peers:</strong> {len(geolocated_peers)}</p>
        <p style="margin: 5px 0;"><strong>Countries:</strong> {len(country_counts)}</p>
        <hr style="margin: 10px 0;">
        <h4 style="margin: 10px 0 5px 0; font-size: 14px;">Top Countries:</h4>
        <ol style="margin: 0; padding-left: 20px;">
    """
    
    for country, count in country_counts.most_common(10):
        stats_html += f'<li style="margin: 2px 0;">{country}: {count}</li>'
    
    stats_html += """
        </ol>
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(stats_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Save map
    m.save(output_file)
    logger.info(f"Map saved to {output_file}")
    
    # Print statistics
    print(f"\n{'='*60}")
    print(f"✅ Map Visualization Complete!")
    print(f"Total geolocated peers: {len(geolocated_peers)}")
    print(f"Countries represented: {len(country_counts)}")
    print(f"\nTop 10 Countries:")
    for country, count in country_counts.most_common(10):
        print(f"  {country}: {count} peers")
    print(f"\nMap saved to: {output_file}")
    print(f"{'='*60}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Visualize Bitcoin peers on an interactive map',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default peers_with_locations.json:
  python3 visualize_peers_map.py
  
  # Use custom input file:
  python3 visualize_peers_map.py --input my_peers.json --output my_map.html
  
  # Use database:
  python3 visualize_peers_map.py --db bitcoin_peers.db --use-db
        """
    )
    
    parser.add_argument('--input', type=str, default='peers_with_locations.json',
                       help='Input file with geolocated peers (default: peers_with_locations.json)')
    parser.add_argument('--output', type=str, default='bitcoin_peers_map.html',
                       help='Output HTML map file (default: bitcoin_peers_map.html)')
    parser.add_argument('--db', type=str, default='bitcoin_peers.db',
                       help='SQLite database file (default: bitcoin_peers.db)')
    parser.add_argument('--use-db', action='store_true',
                       help='Read from SQLite database instead of JSON')
    parser.add_argument('--no-heatmap', action='store_true',
                       help='Disable heatmap layer (default: heatmap enabled)')
    
    args = parser.parse_args()
    
    # Load peers data from database or JSON
    if args.use_db or (not os.path.exists(args.input) and os.path.exists(args.db)):
        # Use database
        logger.info(f"Reading from database: {args.db}")
        peers_db = PeersDatabase(args.db)
        peers_data = peers_db.get_latest_snapshot()
        
        if not peers_data:
            logger.error("No data found in database")
            logger.info("Please run fetch_bitnodes.py first to fetch nodes")
            return
        
        logger.info(f"Loaded peers data from database")
        
    else:
        # Load from JSON file
        try:
            with open(args.input, 'r') as f:
                peers_data = json.load(f)
            
            logger.info(f"Loaded peers data from {args.input}")
            
        except FileNotFoundError:
            logger.error(f"File not found: {args.input}")
            logger.info("Please run geolocate_maxmind.py first to create peers_with_locations.json")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {args.input}: {e}")
            return
    
    # Create map
    create_peers_map(peers_data, args.output, enable_heatmap=not args.no_heatmap)


if __name__ == '__main__':
    main()
