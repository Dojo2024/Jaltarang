import streamlit as st
import folium
from folium.plugins import MarkerCluster, HeatMap, TimestampedGeoJson
from streamlit_folium import folium_static
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import re

# Custom styling for different marker types
MARKER_STYLES = {
    'surveillance': {
        'icon': 'ship',
        'color': 'red',
        'prefix': 'fa',
        'popup_style': 'background-color: #ffebee; border-radius: 5px; padding: 10px;'
    },
    'message': {
        'icon': 'envelope',
        'color': 'blue',
        'prefix': 'fa',
        'popup_style': 'background-color: #e3f2fd; border-radius: 5px; padding: 10px;'
    },
    'recon': {
        'icon': 'eye',
        'color': 'green',
        'prefix': 'fa',
        'popup_style': 'background-color: #e8f5e9; border-radius: 5px; padding: 10px;'
    },
    'zone': {
        'color': 'purple',
        'popup_style': 'background-color: #f3e5f5; border-radius: 5px; padding: 10px;'
    }
}

def get_db_connection():
    return sqlite3.connect('data_classification.db')

def load_data():
    conn = get_db_connection()
    
    # Enhanced queries with additional fields and sorting
    surveillance_df = pd.read_sql_query("""
        SELECT date, time, location, coordinates, heading, speed, report, utc_offset,
               COUNT(*) OVER (PARTITION BY location) as location_frequency
        FROM SurveillanceLog
        ORDER BY date DESC, time DESC
    """, conn)
    
    messages_df = pd.read_sql_query("""
        SELECT sender, receiver, priority, dtg, message,
               COUNT(*) OVER (PARTITION BY sender) as sender_frequency
        FROM CommunicationMessage
        ORDER BY dtg DESC
    """, conn)
    
    recon_df = pd.read_sql_query("""
        SELECT date, location, details,
               COUNT(*) OVER (PARTITION BY location) as location_frequency
        FROM ReconnaissanceNotes
        ORDER BY date DESC
    """, conn)
    
    zones_df = pd.read_sql_query("""
        SELECT name, type, significance, coordinates,
               COUNT(*) OVER (PARTITION BY type) as type_frequency
        FROM Zones
    """, conn)
    
    conn.close()
    return surveillance_df, messages_df, recon_df, zones_df
def parse_location_coordinates(location_str):
    """Parse coordinates from location string format used in ReconnaissanceNotes"""
    if pd.isna(location_str):
        return None
        
    pattern = r"(\d+)°(\d+)'([NS]),\s*(\d+)°(\d+)'([EW])"
    match = re.search(pattern, str(location_str))
    
    if match:
        lat_deg, lat_min, lat_dir = match.groups()[:3]
        lon_deg, lon_min, lon_dir = match.groups()[3:]
        
        lat = (float(lat_deg) + float(lat_min)/60) * (1 if lat_dir == 'N' else -1)
        lon = (float(lon_deg) + float(lon_min)/60) * (1 if lon_dir == 'E' else -1)
        return [lat, lon]
    
    return None

def create_heatmap_data(df):
    coordinates = []
    for coord_str in df['coordinates'].dropna():
        coords = parse_location_coordinates(coord_str)
        if coords is not None:  # Changed condition
            coordinates.append(coords + [1.0])  # Adding weight of 1.0
    return coordinates

def create_time_series_chart(df, date_column='date'):
    if df.empty:
        return None
    
    daily_counts = df[date_column].value_counts().sort_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_counts.index,
        y=daily_counts.values,
        mode='lines+markers',
        name='Daily Activity'
    ))
    fig.update_layout(
        title='Activity Timeline',
        xaxis_title='Date',
        yaxis_title='Number of Events',
        height=300
    )
    return fig

def create_priority_distribution(messages_df):
    if messages_df.empty:
        return None
    
    priority_counts = messages_df['priority'].value_counts()
    fig = go.Figure(data=[go.Pie(
        labels=priority_counts.index,
        values=priority_counts.values,
        hole=.3
    )])
    fig.update_layout(
        title='Message Priority Distribution',
        height=300
    )
    return fig

def main():
    # Custom CSS with responsive design
    st.markdown("""
        <style>
        .main {
            padding: 0rem 1rem;
        }
        .stButton>button {
            width: 100%;
        }
        .reportview-container {
            margin-top: -2em;
        }
        .stats-box {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
        }
        /* Responsive layout adjustments */
        @media screen and (max-width: 768px) {
            .row-widget.stHorizontal {
                flex-direction: column;
            }
            .row-widget.stHorizontal > div {
                width: 100% !important;
                margin-bottom: 1rem;
            }
        }
        /* Map container responsive styling */
        .folium-map {
            width: 100% !important;
            height: auto !important;
            min-height: 400px;
        }
        /* Dashboard sections spacing */
        .dashboard-section {
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Advanced Maritime Surveillance Dashboard")
    
    # Load data
    surveillance_df, messages_df, recon_df, zones_df = load_data()
    
    # Make sidebar collapsible for mobile
    with st.sidebar:
        st.title("Controls & Filters")
        
        # Date range filter with improved layout
        st.subheader("Time Range")
        date_range = st.selectbox(
            "Select Time Range",
            ["Last 24 Hours", "Last Week", "Last Month", "Custom Range"]
        )
        
        if date_range == "Custom Range":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
            with col2:
                end_date = st.date_input("End Date", datetime.now())
        
        # Layer controls in a more compact layout
        st.subheader("Map Layers")
        show_surveillance = st.checkbox("Surveillance Reports", True)
        show_messages = st.checkbox("Communication Messages", True)
        show_recon = st.checkbox("Reconnaissance Reports", True)
        show_zones = st.checkbox("Zones", True)
        show_heatmap = st.checkbox("Activity Heatmap", False)
    
    # Create responsive layout
    # Main content area with automatic width adjustment
    container = st.container()
    with container:
        # Map Section
        st.subheader("Maritime Activity Map")
        m = folium.Map(location=[15, 73], zoom_start=5, prefer_canvas=True)
        
        # Add clusters only once
        clusters = {
            'surveillance': MarkerCluster(name="Surveillance Reports"),
            'recon': MarkerCluster(name="Reconnaissance Reports"),
            'message': MarkerCluster(name="Communication Messages")
        }
        
        # Add markers based on filters
        if show_surveillance:
            add_surveillance_markers(surveillance_df, clusters['surveillance'])
        if show_messages:
            add_message_markers(messages_df, clusters['message'])
        if show_recon:
            add_recon_markers(recon_df, clusters['recon'])
        
        # Add all clusters to map (only once)
        for cluster in clusters.values():
            cluster.add_to(m)
            
        # Add heatmap if enabled
        if show_heatmap:
            heatmap_data = create_heatmap_data(surveillance_df)
            HeatMap(heatmap_data).add_to(m)
        
        # Add layer control (only once)
        folium.LayerControl().add_to(m)
        
        # Display map with responsive width
        folium_static(m, width=None, height=500)
        
        # Analytics Section with dynamic columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Activity Timeline")
            timeline_chart = create_time_series_chart(surveillance_df)
            if timeline_chart:
                st.plotly_chart(timeline_chart, use_container_width=True)
        
        with col2:
            st.subheader("Message Priority")
            priority_chart = create_priority_distribution(messages_df)
            if priority_chart:
                st.plotly_chart(priority_chart, use_container_width=True)
        
        # Tabs Section with improved spacing
        st.markdown("<div class='dashboard-section'>", unsafe_allow_html=True)
        tabs = st.tabs(["Surveillance", "Messages", "Reconnaissance", "Zones"])
        
        with tabs[0]:
            if not surveillance_df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    display_surveillance_stats(surveillance_df)
                with col2:
                    display_surveillance_trends(surveillance_df)
        
        with tabs[1]:
            if not messages_df.empty:
                display_message_summary(messages_df)
        
        with tabs[2]:
            if not recon_df.empty:
                display_recon_summary(recon_df)
        
        with tabs[3]:
            if not zones_df.empty:
                display_zone_summary(zones_df)
        st.markdown("</div>", unsafe_allow_html=True)

def display_surveillance_stats(df):
    latest = df.iloc[0]
    st.markdown("""
        <div class="stats-box">
            <h4>Latest Surveillance</h4>
            <p><b>Location:</b> {}</p>
            <p><b>Time:</b> {}</p>
            <p><b>Speed:</b> {}</p>
        </div>
    """.format(latest['location'], latest['time'], latest['speed']), unsafe_allow_html=True)

def display_surveillance_trends(df):
    # Add any trend analysis visualizations here
    pass

def display_message_summary(df):
    st.markdown("""
        <div class="stats-box">
            <h4>Message Statistics</h4>
            <p><b>Total Messages:</b> {}</p>
            <p><b>Priority Messages:</b> {}</p>
        </div>
    """.format(len(df), len(df[df['priority'] == 'HIGH'])), unsafe_allow_html=True)

def display_recon_summary(df):
    st.markdown("""
        <div class="stats-box">
            <h4>Reconnaissance Summary</h4>
            <p><b>Total Reports:</b> {}</p>
            <p><b>Latest Update:</b> {}</p>
        </div>
    """.format(len(df), df.iloc[0]['date']), unsafe_allow_html=True)

def display_zone_summary(df):
    st.markdown("""
        <div class="stats-box">
            <h4>Zone Overview</h4>
            <p><b>Total Zones:</b> {}</p>
            <p><b>Zone Types:</b> {}</p>
        </div>
    """.format(len(df), len(df['type'].unique())), unsafe_allow_html=True)

# Add marker helper functions
def add_surveillance_markers(df, cluster):
    for _, row in df.iterrows():
        coords = parse_location_coordinates(row['coordinates'])
        if coords is not None:
            popup_html = create_surveillance_popup(row)
            create_marker(coords, popup_html, 'surveillance', cluster)

def add_message_markers(df, cluster):
    for _, row in df.iterrows():
        coords = parse_location_coordinates(row.get('location', None))
        if coords is not None:
            popup_html = create_message_popup(row)
            create_marker(coords, popup_html, 'message', cluster)

def add_recon_markers(df, cluster):
    for _, row in df.iterrows():
        coords = parse_location_coordinates(row['location'])
        if coords is not None:
            popup_html = create_recon_popup(row)
            create_marker(coords, popup_html, 'recon', cluster)

def create_marker(coords, popup_html, marker_type, cluster):
    folium.Marker(
        coords,
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(
            color=MARKER_STYLES[marker_type]['color'],
            icon=MARKER_STYLES[marker_type]['icon'],
            prefix=MARKER_STYLES[marker_type]['prefix']
        )
    ).add_to(cluster)

def create_surveillance_popup(row):
    """
    Creates a formatted HTML popup for surveillance markers
    Args:
        row: DataFrame row containing surveillance data
    Returns:
        str: Formatted HTML for the popup
    """
    return f"""
    <div style="{MARKER_STYLES['surveillance']['popup_style']}">
        <h4 style="margin:0 0 10px 0;color:#d32f2f;">Surveillance Report</h4>
        <div style="margin-bottom:5px;">
            <strong>Location:</strong> {row['location']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Date:</strong> {row['date']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Time:</strong> {row['time']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Heading:</strong> {row.get('heading', 'N/A')}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Speed:</strong> {row.get('speed', 'N/A')}
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #ffcdd2;">
            <strong>Report:</strong><br>
            <div style="max-height:100px;overflow-y:auto;">
                {row.get('report', 'No report available')}
            </div>
        </div>
    </div>
    """

def create_message_popup(row):
    """
    Creates a formatted HTML popup for communication message markers
    Args:
        row: DataFrame row containing message data
    Returns:
        str: Formatted HTML for the popup
    """
    # Define priority colors
    priority_colors = {
        'HIGH': '#d32f2f',
        'MEDIUM': '#f57c00',
        'LOW': '#388e3c',
        'IMMEDIATE': '#c2185b'
    }
    
    priority = row.get('priority', 'MEDIUM')
    priority_color = priority_colors.get(priority, '#000000')
    
    return f"""
    <div style="{MARKER_STYLES['message']['popup_style']}">
        <h4 style="margin:0 0 10px 0;color:#1565c0;">Communication Message</h4>
        <div style="margin-bottom:5px;">
            <strong>From:</strong> {row['sender']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>To:</strong> {row['receiver']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Priority:</strong> 
            <span style="color:{priority_color};font-weight:bold;">
                {priority}
            </span>
        </div>
        <div style="margin-bottom:5px;">
            <strong>Time:</strong> {row['dtg']}
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #bbdefb;">
            <strong>Message:</strong><br>
            <div style="max-height:100px;overflow-y:auto;white-space:pre-wrap;">
                {row.get('message', 'No message content available')}
            </div>
        </div>
    </div>
    """

def create_recon_popup(row):
    """
    Creates a formatted HTML popup for reconnaissance markers
    Args:
        row: DataFrame row containing reconnaissance data
    Returns:
        str: Formatted HTML for the popup
    """
    return f"""
    <div style="{MARKER_STYLES['recon']['popup_style']}">
        <h4 style="margin:0 0 10px 0;color:#2e7d32;">Reconnaissance Report</h4>
        <div style="margin-bottom:5px;">
            <strong>Location:</strong> {row['location']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Date:</strong> {row['date']}
        </div>
        <div style="margin-bottom:5px;">
            <strong>Frequency:</strong> {row.get('location_frequency', 'N/A')} reports at this location
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid #c8e6c9;">
            <strong>Details:</strong><br>
            <div style="max-height:100px;overflow-y:auto;">
                {row.get('details', 'No details available')}
            </div>
        </div>
    </div>
    """

# Helper function to safely get nested dictionary values
def get_safe_value(dictionary, *keys, default='N/A'):
    """
    Safely get nested dictionary values without raising KeyError
    Args:
        dictionary: The dictionary to search in
        *keys: The keys to search for
        default: Default value if key not found
    Returns:
        The value if found, otherwise the default value
    """
    temp_dict = dictionary
    for key in keys:
        try:
            temp_dict = temp_dict[key]
        except (KeyError, TypeError):
            return default
    return temp_dict
    
main()