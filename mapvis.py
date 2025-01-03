import folium
from streamlit_folium import st_folium
import re
from datetime import datetime
import pandas as pd
import streamlit as st

def extract_coordinates(text):
    """Extract coordinates from text using updated regex patterns."""
    pattern = r"(\d+°\d+'\s*[NSns])[,\s]+(\d+°\d+'\s*[EWew])"
    
    coordinates = []
    matches = re.finditer(pattern, text)
    
    for match in matches:
        lat = convert_dms_to_decimal(match.group(1))
        lon = convert_dms_to_decimal(match.group(2))
        
        if lat is not None and lon is not None:
            coordinates.append((lat, lon))
    
    return coordinates

def parse_dtg(dtg_str):
    try:
        date_part = dtg_str[:6]
        time_str = f"{date_part[:2]}:{date_part[2:4]}"
        day = dtg_str[6:8]
        month = dtg_str[9:12]
        year = str(datetime.now().year)
        dtg_parsed = f"{year}-{month}-{day} {time_str}:00"
        return datetime.strptime(dtg_parsed, "%Y-%b-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None


def convert_dms_to_decimal(coord_str):
    """Convert degrees/minutes format to decimal degrees"""
    try:
        parts = re.match(r"(\d+)°\s*(\d+)'\s*([NSEWnsew])", coord_str)
        if parts:
            degrees = float(parts.group(1))
            minutes = float(parts.group(2))
            direction = parts.group(3).upper()
            
            decimal = degrees + (minutes / 60)
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
    except:
        return None

def convert_decimal_degrees(coord_str):
    """Convert decimal degrees format to decimal"""
    try:
        parts = re.match(r"(\d+\.?\d*)°?\s*([NSEWnsew])", coord_str)
        if parts:
            degrees = float(parts.group(1))
            direction = parts.group(2).upper()
            
            if direction in ['S', 'W']:
                degrees = -degrees
            return degrees
    except:
        return None

def extract_contact_info(text):
    """Extract contact information from text"""
    contact_info = {
        'name': None,
        'type': None,
        'speed': None,
        'heading': None,
        'timestamp': None
    }
    
    
    name_pattern = r'(?:vessel|ship|submarine|aircraft)\s+"([^"]+)"|"([^"]+)"'
    name_match = re.search(name_pattern, text, re.IGNORECASE)
    if name_match:
        contact_info['name'] = name_match.group(1) or name_match.group(2)
    
    
    type_pattern = r'(cargo vessel|tanker|fishing vessel|submarine|aircraft|patrol vessel)'
    type_match = re.search(type_pattern, text, re.IGNORECASE)
    if type_match:
        contact_info['type'] = type_match.group(1).title()
    
    
    speed_pattern = r'(\d+(?:\.\d+)?)\s*(?:knots|kts)'
    speed_match = re.search(speed_pattern, text, re.IGNORECASE)
    if speed_match:
        contact_info['speed'] = float(speed_match.group(1))
    
    
    heading_pattern = r'(?:heading|course)\s*(?:of)?\s*(\d+)°'
    heading_match = re.search(heading_pattern, text, re.IGNORECASE)
    if heading_match:
        contact_info['heading'] = int(heading_match.group(1))
    
    
    dtg_pattern = r'"DTG":"([\dA-Z\s]+)"'
    dtg_match = re.search(dtg_pattern, text)
    if dtg_match:
        contact_info['timestamp'] = parse_dtg(dtg_match.group(1))
    
    return contact_info


def plot_on_map(data):
    """Plot maritime contacts on an interactive map"""
    
    m = folium.Map(location=[15, 60], zoom_start=5)
    
    
    relevant_classes = ['SurveillanceLog', 'CommunicationMessage']
    filtered_data = [entry for entry in data if entry['class'] in relevant_classes]
    
    
    st.sidebar.markdown("### Map Filters")
    selected_classes = st.sidebar.multiselect(
        "Contact Types",
        options=relevant_classes,
        default=relevant_classes
    )
    
    
    min_date = datetime.now()
    max_date = datetime.now()
    for entry in filtered_data:
        contact_info = extract_contact_info(str(entry['structure']))
        if contact_info['timestamp']:
            try:
                date = datetime.strptime(contact_info['timestamp'], "%Y-%m-%d %H:%M:%S")
                min_date = min(min_date, date)
                max_date = max(max_date, date)
            except:
                pass
    
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date)
    )
    
    
    for entry in filtered_data:
        if entry['class'] not in selected_classes:
            continue
            
        text = str(entry['structure'])
        
        
        coordinates = extract_coordinates(text)
        contact_info = extract_contact_info(text)
        
        
        for lat, lon in coordinates:
            
            popup_content = f"""
                <b>Contact Information:</b><br>
                Name: {contact_info['name'] or 'Unknown'}<br>
                Type: {contact_info['type'] or 'Unknown'}<br>
                Speed: {contact_info['speed'] or 'Unknown'} knots<br>
                Heading: {contact_info['heading'] or 'Unknown'}°<br>
                Time: {contact_info['timestamp'] or 'Unknown'}<br>
                <br>
                <b>Source:</b> {entry['class']}<br>
                <b>Summary:</b> {entry['summary'][:200]}...
            """
            
            
            icon_color = 'red'
            if contact_info['type']:
                if 'submarine' in contact_info['type'].lower():
                    icon_color = 'blue'
                elif 'aircraft' in contact_info['type'].lower():
                    icon_color = 'green'
            
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=icon_color)
            ).add_to(m)
            
            
            if contact_info['heading']:
                folium.RegularPolygonMarker(
                    location=[lat, lon],
                    number_of_sides=3,
                    rotation=contact_info['heading'],
                    radius=10,
                    color=icon_color,
                    fill=True
                ).add_to(m)
    
    
    st_folium(m, width=800, height=600)
    
    
    st.markdown("### Recent Contacts")
    for entry in filtered_data[:5]:  
        contact_info = extract_contact_info(str(entry['structure']))
        with st.expander(
            f"{contact_info['type'] or 'Unknown Contact'} - {contact_info['timestamp'] or 'Unknown Time'}"
        ):
            st.write(f"Class: {entry['class']}")
            st.write(f"Summary: {entry['summary']}")