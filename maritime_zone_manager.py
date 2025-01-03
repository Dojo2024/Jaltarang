import json
import re
from pathlib import Path
import folium
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class ZoneCoordinate:
    lat: float
    lon: float
    timestamp: Optional[datetime] = None

@dataclass
class MaritimeZone:
    name: str
    type: str
    coordinates: List[ZoneCoordinate]
    significance: str = ""
    active_period: Optional[Tuple[datetime, datetime]] = None
    status: str = "active"
    category: str = ""

class MaritimeZoneManager:
    def __init__(self):
        self.zones = {
            'air_defense': [],
            'air_patrol': [],
            'amphibious_ops': [],
            'asw': [],
            'mio': [],
            'mine_warfare': [],
            'naval_ops': [],
            'special_ops': [],
            'surveillance': [],
            'strategic': []
        }
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)       
        
        self.zone_styles = {
            'air_defense': {
                'color': '#0000FF',
                'fillColor': '#0000FF',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '5, 5',
                'weight': 2
            },
            'air_patrol': {
                'color': '#00FF00',
                'fillColor': '#00FF00',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'weight': 2
            },
            'amphibious_ops': {
                'color': '#FFA500',
                'fillColor': '#FFA500',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '10, 5',
                'weight': 2
            },
            'asw': {
                'color': '#800080',
                'fillColor': '#800080',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '5, 10',
                'weight': 2
            },
            'mio': {
                'color': '#008080',
                'fillColor': '#008080',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'weight': 2
            },
            'mine_warfare': {
                'color': '#FF69B4',
                'fillColor': '#FF69B4',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '15, 5',
                'weight': 2
            },
            'naval_ops': {
                'color': '#000000',
                'fillColor': '#000000',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'weight': 2
            },
            'special_ops': {
                'color': '#FF0000',
                'fillColor': '#FF0000',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '5, 5, 15, 5',
                'weight': 2
            },
            'surveillance': {
                'color': '#4B0082',
                'fillColor': '#4B0082',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'weight': 2
            },
            'strategic': {
                'color': '#8B4513',
                'fillColor': '#8B4513',
                'opacity': 0.8,
                'fillOpacity': 0.1,
                'dashArray': '10, 10',
                'weight': 2
            }
        }

        self.loading_status = {
            'files_found': 0,
            'zones_loaded': 0,
            'errors': []
        }
        
        self._load_zones_from_files()

    def _validate_coordinates(self, coordinates: List[dict]) -> List[ZoneCoordinate]:
        """Validate and clean coordinates"""
        valid_coords = []
        for coord in coordinates:
            try:
                lat = float(coord['lat'])
                lon = float(coord['lon'])
                
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    valid_coords.append(ZoneCoordinate(lat=lat, lon=lon))
            except (ValueError, KeyError):
                continue
        return valid_coords

    def _smooth_coordinates(self, coordinates: List[List[float]], smoothing_factor: int = 3) -> List[List[float]]:
        """Smooth the zone boundaries with improved interpolation"""
        if len(coordinates) < 3:
            return coordinates
            
        smoothed = []
        for i in range(len(coordinates)):
            current = coordinates[i]
            next_point = coordinates[(i + 1) % len(coordinates)]
            
            smoothed.append(current)
            
            
            for j in range(1, smoothing_factor):
                t = j / smoothing_factor
                lat = current[0] + (next_point[0] - current[0]) * t
                lon = current[1] + (next_point[1] - current[1]) * t
                smoothed.append([lat, lon])
                
        return smoothed

    def _parse_markdown_zones(self, md_content: str) -> List[Dict]:
        """Parse zones with improved error handling"""
        json_pattern = r"```json\s*(.*?)\s*```"
        json_matches = re.finditer(json_pattern, md_content, re.DOTALL)
        
        zones = []
        for match in json_matches:
            try:
                zone_data = json.loads(match.group(1))
                if isinstance(zone_data, list):
                    zones.extend(zone_data)
                else:
                    zones.append(zone_data)
            except json.JSONDecodeError:
                continue
        
        return zones

    def _load_zones_from_files(self):
        """Load zones from markdown files with improved path resolution."""
        try:
            current_dir = Path(__file__).resolve().parent
            zones_dir = current_dir / "zones"
            
            if not zones_dir.exists():
                zones_dir = Path(__file__).resolve().parent / "zones"
                if not zones_dir.exists():
                    self.logger.error(f"Zones directory not found at {zones_dir}")
                    return
            
            print(f"Loading zones from: {zones_dir}")  

            filename_mappings = {
                'air_defense': 'indian-navy-air-defense-exercise-areas',
                'air_patrol': 'indian-navy-air-patrol-zones',
                'amphibious_ops': 'indian-navy-amphibious-operation-areas',
                'asw': 'indian-navy-asw-exercise-areas',
                'mio': 'indian-navy-maritime-interdiction-operation-areas',
                'naval_ops': 'indian-navy-operation-zones',
                'mine_warfare': 'indian-navy-mine-warfare-exercise-areas',
                'special_ops': 'indian-navy-special-operations-exercise-areas',
                'strategic': 'indian-navy-strategic-maritime-zones'
            }

            for category, filename_prefix in filename_mappings.items():
                matching_files = list(zones_dir.glob(f"{filename_prefix}*.md"))
                self.loading_status['files_found'] += len(matching_files)
                
                if not matching_files:
                    continue
                
                for md_file in matching_files:
                    try:
                        with md_file.open('r', encoding='utf-8') as f:
                            content = f.read()
                            raw_zones = self._parse_markdown_zones(content)
                            
                            if not raw_zones:
                                print(f"No zones found in {md_file}")
                                continue
                            
                            for raw_zone in raw_zones:
                                try:
                                    coordinates = self._validate_coordinates(raw_zone.get('coordinates', []))
                                    
                                    if not coordinates:
                                        print(f"No valid coordinates found in zone from {md_file}")
                                        continue
                                    
                                    maritime_zone = MaritimeZone(
                                        name=raw_zone.get('name', 'Unnamed Zone'),
                                        type=raw_zone.get('type', ''),
                                        coordinates=coordinates,
                                        significance=raw_zone.get('significance', ''),
                                        status=raw_zone.get('status', 'active'),
                                        category=category 
                                    )
                                    
                                    self.zones[category].append(maritime_zone)
                                    self.loading_status['zones_loaded'] += 1
                                    
                                except (KeyError, ValueError) as e:
                                    self.loading_status['errors'].append(
                                        f"Error processing zone in {md_file.name}: {e}"
                                    )
                                    print(f"Error processing zone: {e}")
                                    continue
                                    
                    except Exception as e:
                        self.loading_status['errors'].append(f"Error loading file {md_file.name}: {e}")
                        print(f"Error loading file: {e}")
                        continue

        except Exception as e:
            self.loading_status['errors'].append(f"Critical error in zone loading: {e}")
            print(f"Critical error: {e}")

    def add_zones_to_map(self, folium_map: folium.Map):
        """Add zones to the map with proper type display"""
        for zone_category, zones in self.zones.items():
            if not zones:
                continue
                
            feature_group = folium.FeatureGroup(
                name=f"{zone_category.replace('_', ' ').title()}",
                show=True,
                control=True
            )
            
            zone_style = self.zone_styles.get(zone_category, {})
            
            for zone in zones:
                try:
                    coords = [[coord.lat, coord.lon] for coord in zone.coordinates]
                    
                    if len(coords) < 3:
                        continue
                    
                    # Format coordinates table
                    coords_table = """
                    <table style='width:100%; border-collapse: collapse;'>
                        <tr>
                            <th style='border:1px solid #ddd; padding:4px;'>Latitude</th>
                            <th style='border:1px solid #ddd; padding:4px;'>Longitude</th>
                        </tr>
                    """
                    for coord in zone.coordinates:
                        coords_table += f"""
                        <tr>
                            <td style='border:1px solid #ddd; padding:4px;'>{coord.lat:.4f}°</td>
                            <td style='border:1px solid #ddd; padding:4px;'>{coord.lon:.4f}°</td>
                        </tr>
                        """
                    coords_table += "</table>"
                    
                    popup_html = f"""
                    <div style='width: 300px; max-height: 400px; overflow-y: auto;'>
                        <div style='background: {zone_style.get("color", "#3388ff")}22; 
                                   border-left: 4px solid {zone_style.get("color", "#3388ff")};
                                   padding: 10px;'>
                            <h4 style='margin:0; color: {zone_style.get("color", "#3388ff")};'>{zone.name}</h4>
                        </div>
                        
                        <div style='padding: 10px;'>
                            <p><strong>Type:</strong><br>
                               <span style='color: #666;'>{zone.type}</span></p>
                            
                            <p><strong>Category:</strong><br>
                               <span style='color: #666;'>{zone_category.replace('_', ' ').title()}</span></p>
                            
                            <p><strong>Status:</strong><br>
                               <span style='color: {"#28a745" if zone.status == "active" else "#dc3545"};
                                          padding: 2px 6px;
                                          border-radius: 3px;
                                          background: {"#28a74522" if zone.status == "active" else "#dc354522"};'>
                               {zone.status.title()}</span></p>
                            
                            <p><strong>Significance:</strong><br>
                               <span style='color: #666;'>{zone.significance}</span></p>
                            
                            <div style='margin-top: 10px;'>
                                <p><strong>Coordinates:</strong></p>
                                <div style='max-height: 150px; overflow-y: auto;'>
                                    {coords_table}
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    
                    folium.Polygon(
                        locations=coords,
                        popup=folium.Popup(popup_html, max_width=350),
                        tooltip=f"{zone.name}",
                        color=zone_style.get('color', '#3388ff'),
                        weight=zone_style.get('weight', 2),
                        fill=True,
                        fill_color=zone_style.get('fillColor', '#3388ff'),
                        fill_opacity=zone_style.get('fillOpacity', 0.1),
                        opacity=zone_style.get('opacity', 0.8),
                        dash_array=zone_style.get('dashArray'),
                        smooth_factor=1.5
                    ).add_to(feature_group)
                    
                except Exception as e:
                    print(f"Error adding zone {zone.name}: {e}")
                    continue
            
            feature_group.add_to(folium_map)

        folium.LayerControl(
            position='topright',
            collapsed=False
        ).add_to(folium_map)

    def get_zone_bounds(self) -> List[List[float]]:
        """Calculate the bounds of all zones with padding."""
        all_coords = []
        for zones in self.zones.values():
            for zone in zones:
                all_coords.extend([[coord.lat, coord.lon] for coord in zone.coordinates])
        
        if not all_coords:
            return [[0, 0], [0, 0]]
        
        lats = [coord[0] for coord in all_coords]
        lons = [coord[1] for coord in all_coords]
        
        
        padding = 1.0  
        return [
            [min(lats) - padding, min(lons) - padding],
            [max(lats) + padding, max(lons) + padding]
        ]

    def get_zones_summary(self) -> pd.DataFrame:
        """Create a detailed summary DataFrame of all zones."""
        zone_data = []
        for zone_type, zones in self.zones.items():
            for zone in zones:
                center_lat = sum(coord.lat for coord in zone.coordinates) / len(zone.coordinates)
                center_lon = sum(coord.lon for coord in zone.coordinates) / len(zone.coordinates)
                
                zone_data.append({
                    'name': zone.name,
                    'type': zone.type,
                    'zone_category': zone_type,
                    'significance': zone.significance,
                    'status': zone.status,
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'num_vertices': len(zone.coordinates)
                })
        
        return pd.DataFrame(zone_data)