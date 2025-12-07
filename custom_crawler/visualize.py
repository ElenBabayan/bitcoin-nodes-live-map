#!/usr/bin/env python3
"""
Beautiful Bitcoin Network Heatmap Visualization
Creates stunning interactive maps from DuckDB crawler data.

Features:
- Gradient heatmap showing node density
- Interactive markers with peer details
- Country/city statistics overlay
- Dark/light theme support
- Multiple tile layer options
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import BitcoinNodesDB

# Try to import visualization libraries
try:
    import folium
    from folium.plugins import HeatMap, MarkerCluster, MiniMap, Fullscreen
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    logger.warning("folium not installed. Run: pip install folium")

try:
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly/pandas not installed. Run: pip install plotly pandas")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         COLOR SCHEMES & THEMES                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Cyberpunk-inspired gradient for heatmap
HEATMAP_GRADIENT_CYBER = {
    0.0: '#0d0221',   # Deep purple-black
    0.2: '#0f084b',   # Dark indigo
    0.4: '#26086c',   # Purple
    0.6: '#6b0f6c',   # Magenta
    0.8: '#f21f51',   # Hot pink
    1.0: '#fabc2a'    # Bright gold
}

# Bitcoin orange gradient
HEATMAP_GRADIENT_BITCOIN = {
    0.0: '#1a1a2e',   # Dark blue-gray
    0.2: '#16213e',   # Navy
    0.4: '#0f3460',   # Blue
    0.6: '#e94560',   # Red-pink
    0.8: '#f77f00',   # Orange
    1.0: '#f5a623'    # Bitcoin orange
}

# Neon blue gradient
HEATMAP_GRADIENT_NEON = {
    0.0: '#000814',   # Almost black
    0.2: '#001d3d',   # Dark blue
    0.4: '#003566',   # Navy
    0.6: '#00b4d8',   # Cyan
    0.8: '#00f5d4',   # Bright teal
    1.0: '#f0fff0'    # White-green
}

GRADIENTS = {
    'cyber': HEATMAP_GRADIENT_CYBER,
    'bitcoin': HEATMAP_GRADIENT_BITCOIN,
    'neon': HEATMAP_GRADIENT_NEON
}


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                      FOLIUM MAP VISUALIZER                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

class BitcoinNetworkMap:
    """
    Creates beautiful interactive maps of Bitcoin network nodes.
    """
    
    def __init__(self, redis_host: str = None, redis_port: int = None, redis_db: int = None):
        """
        Initialize with database connection.
        
        Args:
            redis_host: Redis host (default: localhost)
            redis_port: Redis port (default: 6379)
            redis_db: Redis database number (default: 1)
        """
        if not FOLIUM_AVAILABLE:
            raise ImportError("folium is required. Install with: pip install folium")
        
        self.db = BitcoinNodesDB(host=redis_host, port=redis_port, db=redis_db)
        logger.info("📊 Connected to Redis for visualization")
    
    def create_heatmap(
        self,
        output_path: str = 'bitcoin_network_heatmap.html',
        theme: str = 'bitcoin',
        show_markers: bool = True,
        show_stats: bool = True
    ) -> str:
        """
        Create a stunning heatmap visualization of Bitcoin nodes.
        
        Args:
            output_path: Output HTML file path
            theme: Color theme ('cyber', 'bitcoin', 'neon')
            show_markers: Whether to show individual node markers
            show_stats: Whether to show statistics overlay
            
        Returns:
            Path to generated HTML file
        """
        logger.info("🗺️  Generating Bitcoin network heatmap...")
        
        # Get geolocated peers
        peers = self.db.get_geolocated_peers()
        
        if not peers:
            logger.error("❌ No geolocated peers found!")
            logger.info("   Run geolocate.py first to add location data.")
            return None
        
        logger.info(f"   Found {len(peers):,} geolocated peers")
        
        # Calculate center point
        lats = [p['latitude'] for p in peers if p['latitude']]
        lons = [p['longitude'] for p in peers if p['longitude']]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Create base map with dark theme
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=2,
            tiles=None,  # We'll add custom tiles
            prefer_canvas=True
        )
        
        # Add tile layers (dark theme first as default)
        folium.TileLayer(
            'CartoDB dark_matter',
            name='🌙 Dark Mode',
            attr='CartoDB'
        ).add_to(m)
        
        folium.TileLayer(
            'CartoDB positron',
            name='☀️ Light Mode',
            attr='CartoDB'
        ).add_to(m)
        
        folium.TileLayer(
            'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
            name='🗺️ Detailed',
            attr='CartoDB Voyager'
        ).add_to(m)
        
        # Prepare heatmap data with intensity
        heat_data = []
        for peer in peers:
            lat = peer['latitude']
            lon = peer['longitude']
            # Weight successful handshakes higher
            weight = 1.5 if peer.get('successful') else 1.0
            heat_data.append([lat, lon, weight])
        
        # Select gradient
        gradient = GRADIENTS.get(theme, HEATMAP_GRADIENT_BITCOIN)
        
        # Add heatmap layer
        heatmap = HeatMap(
            heat_data,
            name='🔥 Node Density Heatmap',
            min_opacity=0.4,
            max_zoom=18,
            radius=20,
            blur=25,
            gradient=gradient
        )
        heatmap.add_to(m)
        
        # Add markers with clustering if enabled
        if show_markers:
            self._add_markers(m, peers)
        
        # Add statistics overlay
        if show_stats:
            self._add_stats_overlay(m, peers)
        
        # Add minimap
        minimap = MiniMap(
            toggle_display=True,
            tile_layer='CartoDB dark_matter'
        )
        m.add_child(minimap)
        
        # Add fullscreen button
        Fullscreen().add_to(m)
        
        # Add layer control
        folium.LayerControl(collapsed=False).add_to(m)
        
        # Add custom CSS for styling
        self._add_custom_css(m)
        
        # Save map
        m.save(output_path)
        logger.info(f"✅ Heatmap saved to: {output_path}")
        
        return output_path
    
    def _add_markers(self, m: folium.Map, peers: List[Dict]):
        """Add clustered markers for each peer."""
        marker_cluster = MarkerCluster(
            name='📍 Individual Nodes',
            show=False,  # Hidden by default (heatmap shows first)
            options={
                'maxClusterRadius': 50,
                'disableClusteringAtZoom': 8
            }
        )
        
        # Count for statistics
        country_counts = Counter()
        city_counts = Counter()
        
        for peer in peers:
            ip = peer['ip']
            port = peer['port']
            lat = peer['latitude']
            lon = peer['longitude']
            country = peer.get('country', 'Unknown')
            city = peer.get('city', 'Unknown')
            region = peer.get('region', '')
            user_agent = peer.get('user_agent', 'Unknown')
            isp = peer.get('isp', 'Unknown')
            successful = peer.get('successful', False)
            
            country_counts[country] += 1
            if city and city != 'Unknown':
                city_counts[f"{city}, {country}"] += 1
            
            # Create popup content with modern styling
            status_icon = '✅' if successful else '⚪'
            status_text = 'Online' if successful else 'Discovered'
            
            popup_html = f"""
            <div style="
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                width: 280px;
                padding: 0;
            ">
                <div style="
                    background: linear-gradient(135deg, #f5a623 0%, #f77f00 100%);
                    color: white;
                    padding: 12px 15px;
                    border-radius: 8px 8px 0 0;
                    margin: -1px -1px 0 -1px;
                ">
                    <h4 style="margin: 0; font-size: 14px; font-weight: 600;">
                        ₿ Bitcoin Testnet Node
                    </h4>
                    <span style="font-size: 11px; opacity: 0.9;">{status_icon} {status_text}</span>
                </div>
                
                <div style="padding: 12px 15px; background: #1a1a2e; color: #e0e0e0;">
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">
                            Address
                        </div>
                        <div style="font-family: 'SF Mono', Monaco, monospace; font-size: 12px; color: #00f5d4;">
                            {ip}:{port}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">
                            Location
                        </div>
                        <div style="font-size: 12px;">
                            📍 {city}, {region}<br>
                            🌍 {country}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">
                            User Agent
                        </div>
                        <div style="font-size: 11px; font-family: 'SF Mono', Monaco, monospace; word-break: break-all;">
                            {user_agent[:50]}{'...' if len(str(user_agent)) > 50 else ''}
                        </div>
                    </div>
                    
                    <div>
                        <div style="font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">
                            ISP
                        </div>
                        <div style="font-size: 11px;">
                            🏢 {isp[:40]}{'...' if len(str(isp)) > 40 else ''}
                        </div>
                    </div>
                </div>
            </div>
            """
            
            # Choose marker color based on status
            icon_color = 'orange' if successful else 'lightgray'
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{ip} • {city}, {country}",
                icon=folium.Icon(color=icon_color, icon='server', prefix='fa')
            ).add_to(marker_cluster)
        
        marker_cluster.add_to(m)
    
    def _add_stats_overlay(self, m: folium.Map, peers: List[Dict]):
        """Add statistics overlay panel."""
        # Calculate statistics
        total_peers = len(peers)
        successful = sum(1 for p in peers if p.get('successful'))
        
        country_counts = Counter(p.get('country', 'Unknown') for p in peers)
        top_countries = country_counts.most_common(8)
        
        # Build stats HTML
        countries_html = ''.join([
            f'<div style="display:flex;justify-content:space-between;margin:4px 0;">'
            f'<span>{c}</span><span style="color:#f5a623;font-weight:600;">{n:,}</span></div>'
            for c, n in top_countries
        ])
        
        stats_html = f"""
        <div id="stats-panel" style="
            position: fixed;
            top: 15px;
            right: 15px;
            width: 260px;
            background: rgba(26, 26, 46, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            z-index: 9999;
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #e0e0e0;
            overflow: hidden;
            border: 1px solid rgba(245, 166, 35, 0.3);
        ">
            <!-- Header -->
            <div style="
                background: linear-gradient(135deg, #f5a623 0%, #f77f00 100%);
                padding: 15px;
                text-align: center;
            ">
                <div style="font-size: 24px; margin-bottom: 5px;">₿</div>
                <h3 style="margin: 0; font-size: 16px; font-weight: 600; color: white;">
                    Bitcoin Testnet Network
                </h3>
                <div style="font-size: 11px; opacity: 0.9; color: white;">
                    Live Node Distribution
                </div>
            </div>
            
            <!-- Stats Body -->
            <div style="padding: 15px;">
                <!-- Main Stats -->
                <div style="
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 10px;
                    margin-bottom: 15px;
                ">
                    <div style="
                        background: rgba(245, 166, 35, 0.1);
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                    ">
                        <div style="font-size: 22px; font-weight: 700; color: #f5a623;">
                            {total_peers:,}
                        </div>
                        <div style="font-size: 10px; color: #888; text-transform: uppercase;">
                            Total Nodes
                        </div>
                    </div>
                    <div style="
                        background: rgba(0, 245, 212, 0.1);
                        border-radius: 8px;
                        padding: 10px;
                        text-align: center;
                    ">
                        <div style="font-size: 22px; font-weight: 700; color: #00f5d4;">
                            {successful:,}
                        </div>
                        <div style="font-size: 10px; color: #888; text-transform: uppercase;">
                            Reachable
                        </div>
                    </div>
                </div>
                
                <!-- Countries Count -->
                <div style="
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 15px;
                    text-align: center;
                ">
                    <span style="font-size: 18px; font-weight: 600; color: #e94560;">
                        {len(country_counts)}
                    </span>
                    <span style="font-size: 12px; color: #888; margin-left: 8px;">
                        Countries
                    </span>
                </div>
                
                <!-- Top Countries -->
                <div>
                    <div style="
                        font-size: 10px;
                        color: #888;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        margin-bottom: 8px;
                    ">
                        🌍 Top Countries
                    </div>
                    <div style="font-size: 12px;">
                        {countries_html}
                    </div>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="
                padding: 10px 15px;
                background: rgba(0, 0, 0, 0.2);
                font-size: 10px;
                color: #666;
                text-align: center;
            ">
                Powered by Redis • Bitcoin Testnet Crawler
            </div>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(stats_html))
    
    def _add_custom_css(self, m: folium.Map):
        """Add custom CSS for better styling."""
        css = """
        <style>
            /* Custom popup styling */
            .leaflet-popup-content-wrapper {
                background: transparent !important;
                box-shadow: none !important;
                padding: 0 !important;
            }
            .leaflet-popup-content {
                margin: 0 !important;
                width: auto !important;
            }
            .leaflet-popup-tip {
                background: #1a1a2e !important;
            }
            
            /* Layer control styling */
            .leaflet-control-layers {
                background: rgba(26, 26, 46, 0.95) !important;
                border: 1px solid rgba(245, 166, 35, 0.3) !important;
                border-radius: 8px !important;
                color: #e0e0e0 !important;
            }
            .leaflet-control-layers-toggle {
                background-color: #f5a623 !important;
            }
            
            /* Fullscreen button */
            .leaflet-control-fullscreen a {
                background-color: rgba(26, 26, 46, 0.95) !important;
                color: #f5a623 !important;
            }
            
            /* Attribution */
            .leaflet-control-attribution {
                background: rgba(26, 26, 46, 0.8) !important;
                color: #888 !important;
            }
            .leaflet-control-attribution a {
                color: #f5a623 !important;
            }
        </style>
        """
        m.get_root().html.add_child(folium.Element(css))
    
    def create_3d_globe(
        self,
        output_path: str = 'bitcoin_network_globe.html'
    ) -> Optional[str]:
        """
        Create an interactive 3D globe visualization using Plotly.
        
        Args:
            output_path: Output HTML file path
            
        Returns:
            Path to generated HTML file
        """
        if not PLOTLY_AVAILABLE:
            logger.error("Plotly is required for 3D globe. Install with: pip install plotly pandas")
            return None
        
        logger.info("🌐 Generating 3D globe visualization...")
        
        # Get data
        peers = self.db.get_geolocated_peers()
        
        if not peers:
            logger.error("❌ No geolocated peers found!")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(peers)
        
        # Get country stats for bubble sizes
        country_stats = df.groupby(['country', 'country_code']).agg({
            'ip': 'count',
            'latitude': 'mean',
            'longitude': 'mean',
            'successful': 'sum'
        }).reset_index()
        country_stats.columns = ['country', 'country_code', 'count', 'lat', 'lon', 'successful']
        
        # Create figure
        fig = go.Figure()
        
        # Add scatter geo points
        fig.add_trace(go.Scattergeo(
            lat=country_stats['lat'],
            lon=country_stats['lon'],
            mode='markers',
            marker=dict(
                size=country_stats['count'].apply(lambda x: min(50, max(8, x / 5))),
                color=country_stats['successful'],
                colorscale='YlOrRd',
                opacity=0.8,
                line=dict(width=1, color='rgba(245, 166, 35, 0.5)')
            ),
            text=country_stats.apply(
                lambda r: f"{r['country']}<br>Nodes: {r['count']:,}<br>Reachable: {int(r['successful']):,}",
                axis=1
            ),
            hoverinfo='text',
            name='Bitcoin Nodes'
        ))
        
        # Update layout for dark theme
        fig.update_layout(
            title=dict(
                text='<b>₿ Bitcoin Testnet Network</b><br><sup>Global Node Distribution</sup>',
                font=dict(size=24, color='#f5a623', family='SF Pro Display, sans-serif'),
                x=0.5
            ),
            geo=dict(
                showland=True,
                landcolor='rgb(20, 20, 40)',
                showocean=True,
                oceancolor='rgb(10, 10, 30)',
                showcountries=True,
                countrycolor='rgb(50, 50, 80)',
                showcoastlines=True,
                coastlinecolor='rgb(80, 80, 120)',
                projection_type='orthographic',
                bgcolor='rgba(0,0,0,0)'
            ),
            paper_bgcolor='rgb(15, 15, 35)',
            plot_bgcolor='rgb(15, 15, 35)',
            font=dict(color='#e0e0e0'),
            margin=dict(l=0, r=0, t=80, b=0),
            annotations=[
                dict(
                    text=f"Total Nodes: {len(peers):,} | Countries: {len(country_stats)}",
                    xref='paper', yref='paper',
                    x=0.5, y=-0.02,
                    showarrow=False,
                    font=dict(size=12, color='#888')
                )
            ]
        )
        
        # Save
        fig.write_html(output_path, include_plotlyjs=True, full_html=True)
        logger.info(f"✅ 3D Globe saved to: {output_path}")
        
        return output_path
    
    def close(self):
        """Close database connection."""
        self.db.close()


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                              MAIN ENTRY                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Create beautiful Bitcoin network visualizations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Visualization Themes:
  bitcoin  - Orange/gold Bitcoin-inspired gradient (default)
  cyber    - Purple/pink cyberpunk gradient
  neon     - Blue/teal neon gradient

Examples:
  # Create default heatmap:
  python3 visualize.py
  
  # Create with specific theme:
  python3 visualize.py --theme cyber --output cyber_map.html
  
  # Create 3D globe:
  python3 visualize.py --globe --output globe.html
  
  # Create both heatmap and globe:
  python3 visualize.py --all

Environment Variables:
  REDIS_HOST  - Redis host (default: localhost)
  REDIS_PORT  - Redis port (default: 6379)
  REDIS_DB    - Redis database (default: 1)
        """
    )
    
    parser.add_argument('--output', '-o', type=str, default='bitcoin_network_heatmap.html',
                       help='Output HTML file path (default: bitcoin_network_heatmap.html)')
    parser.add_argument('--theme', '-t', type=str, default='bitcoin',
                       choices=['bitcoin', 'cyber', 'neon'],
                       help='Color theme for heatmap (default: bitcoin)')
    parser.add_argument('--no-markers', action='store_true',
                       help='Disable individual node markers')
    parser.add_argument('--no-stats', action='store_true',
                       help='Disable statistics overlay')
    parser.add_argument('--globe', action='store_true',
                       help='Create 3D globe visualization instead of heatmap')
    parser.add_argument('--all', action='store_true',
                       help='Create both heatmap and 3D globe')
    
    args = parser.parse_args()
    
    try:
        viz = BitcoinNetworkMap()
    except ImportError as e:
        logger.error(str(e))
        return 1
    
    try:
        if args.globe:
            viz.create_3d_globe(args.output)
        elif args.all:
            viz.create_heatmap(
                output_path='bitcoin_network_heatmap.html',
                theme=args.theme,
                show_markers=not args.no_markers,
                show_stats=not args.no_stats
            )
            viz.create_3d_globe('bitcoin_network_globe.html')
        else:
            viz.create_heatmap(
                output_path=args.output,
                theme=args.theme,
                show_markers=not args.no_markers,
                show_stats=not args.no_stats
            )
        
        # Print summary
        stats = viz.db.get_stats_summary()
        
        print()
        print("╔" + "═" * 60 + "╗")
        print("║" + "  🗺️  VISUALIZATION COMPLETE!".center(60) + "║")
        print("╠" + "═" * 60 + "╣")
        print(f"║  Total peers visualized: {stats['geolocated_peers']:,}".ljust(61) + "║")
        print(f"║  Countries represented: {stats['countries']}".ljust(61) + "║")
        print("╠" + "═" * 60 + "╣")
        print(f"║  📁 Output: {args.output}".ljust(61) + "║")
        print("║  🌐 Open in browser to explore the map!".ljust(61) + "║")
        print("╚" + "═" * 60 + "╝")
        
    finally:
        viz.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

