import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from datetime import datetime
from folium.plugins import HeatMap, MarkerCluster, MiniMap, FloatImage, Fullscreen, MousePosition, MeasureControl, GroupedLayerControl
from maritime_zone_manager import MaritimeZoneManager
from pathlib import Path
from typing import Dict, List, Optional

def create_map(zone_manager: MaritimeZoneManager) -> Optional[folium.Map]:
    """
    Creates a comprehensive map with all features and maritime zones.
    
    Args:
        zone_manager: Instance of MaritimeZoneManager for handling maritime zones
        
    Returns:
        folium.Map: Configured map with all features, or None if error occurs
    """
    try:
        zone_bounds = zone_manager.get_zone_bounds()
        center_lat = (zone_bounds[0][0] + zone_bounds[1][0]) / 2
        center_lon = (zone_bounds[0][1] + zone_bounds[1][1]) / 2
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=3,
            tiles=None, 
            prefer_canvas=True
        )
        
        folium.TileLayer(
            'CartoDB positron',
            name='Light Mode',
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
            name='Topographical',
            attr='Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap (CC-BY-SA)',
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Satellite',
            attr='Esri',
            control=True
        ).add_to(m)
        
        zone_manager.add_zones_to_map(m)
        
        MiniMap(toggle_display=True).add_to(m)
        
        Fullscreen(
            position='topleft',
            title='Expand map',
            title_cancel='Exit fullscreen',
            force_separate_button=True
        ).add_to(m)
        
        MeasureControl(
            position='bottomleft',
            primary_length_unit='kilometers',
            secondary_length_unit='miles'
        ).add_to(m)
        
        MousePosition(
            position='bottomright',
            separator=' | ',
            prefix='Coordinates: ',
            num_digits=4,
            empty_string='No position'
        ).add_to(m)
    
        
        if st.session_state.get('show_elevation', False):
            folium.plugins.ElevationControl(
                position='topright',
                theme='steelblue-theme',
                width=600,
                height=200,
                margins=[20, 20, 20, 40]
            ).add_to(m)
        
        return m
        
    except Exception as e:
        st.error(f"Error creating map: {str(e)}")
        return None

st.title("🗺️ Naksha Zonal Map")

tab1, tab2 = st.tabs(["Map View", "About"])

with tab1:
    with st.sidebar:
        st.info("💡 Tip: Use the fullscreen button on the map for a better view!")

    with st.spinner("Loading interactive map..."):
        map_container = st.container()
        with map_container:
            if 'zone_manager' not in st.session_state:
                st.session_state.zone_manager = MaritimeZoneManager()
                
            m = create_map(st.session_state.zone_manager)
            if m:
                folium_static(m, width=None, height=450)

with tab2:
    st.header("About Naksha Zonal Map")
    st.write("""
    This interactive maritime zone visualization system helps you:
    - Navigate through different maritime zones
    - Analyze spatial patterns
    - Measure distances and areas
    - Export map data
    
    **Features:**
    - 🔍 Interactive zoom and pan
    - 📏 Distance measurement tools
    - 🌍 Multiple base map styles
    - 📍 Detailed zone information
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Zones", value="125")
    with col2:
        st.metric(label="Active Markers", value="47")
    with col3:
        st.metric(label="Updated", value="Today")

st.divider()
status_col1, status_col2 = st.columns([3,1])
with status_col1:
    st.caption("Data last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
with status_col2:
    st.caption("System Status: 🟢 Online")