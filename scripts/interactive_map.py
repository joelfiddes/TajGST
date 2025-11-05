#!/usr/bin/env python3
"""Create an interactive map showing logger locations with links to temperature plots."""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

import folium
from folium import plugins

# Import plotting functionality
import sys
sys.path.append(str(Path(__file__).parent))
from plot_ground_temperature import run as run_plotting


def load_metadata(metadata_path: Path) -> List[Dict[str, str]]:
    """Load logger metadata from CSV file."""
    metadata = []
    if not metadata_path.exists():
        logging.warning("Metadata file not found: %s", metadata_path)
        return metadata
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle different column naming schemes
                # For sangvor: use BLE-ID/Geoprecision column as the main ID
                # For fanmountains: use ID column
                logger_id = ""
                if "BLE-ID/Geoprecision" in row and row["BLE-ID/Geoprecision"]:
                    logger_id = row["BLE-ID/Geoprecision"].strip()
                    # Store waypoint ID in a separate field for sangvor
                    if row.get("ID"):
                        row["WP_ID"] = row["ID"]
                elif row.get("ID"):
                    logger_id = row.get("ID", "").strip()
                
                # Get coordinates with different possible column names
                lat_val = row.get("LAT") or row.get("Y") or ""
                lon_val = row.get("LON") or row.get("X") or ""
                
                # Only include rows with valid coordinates and ID
                if lat_val and lon_val and logger_id and logger_id != "-":
                    try:
                        lat = float(lat_val)
                        lon = float(lon_val)
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            # Normalize the row data with standard column names
                            normalized_row = dict(row)
                            normalized_row["ID"] = logger_id  # Use the correct logger ID
                            normalized_row["LAT"] = lat
                            normalized_row["LON"] = lon
                            
                            # Normalize other common fields
                            if "Altitude" in row and not row.get("ELE"):
                                normalized_row["ELE"] = row["Altitude"]
                            
                            metadata.append(normalized_row)
                    except ValueError:
                        logging.warning("Invalid coordinates for logger %s: lat=%s, lon=%s", logger_id, lat_val, lon_val)
        
        logging.info("Loaded metadata for %d loggers with valid coordinates from %s", len(metadata), metadata_path.name)
    except Exception as e:
        logging.error("Failed to load metadata: %s", e)
    
    return metadata


def load_all_metadata(data_root: Path) -> List[Dict[str, str]]:
    """Load metadata from all metadata files in the data directory."""
    all_metadata = []
    
    # Look for metadata files in the metadata directory
    metadata_dir = data_root / "metadata"
    if metadata_dir.exists():
        for metadata_file in metadata_dir.glob("*.csv"):
            logging.info("Loading metadata from: %s", metadata_file)
            site_metadata = load_metadata(metadata_file)
            all_metadata.extend(site_metadata)
    
    # Also check for legacy location
    legacy_metadata = data_root / "fan_loggers_meta.csv"
    if legacy_metadata.exists():
        logging.info("Loading legacy metadata from: %s", legacy_metadata)
        site_metadata = load_metadata(legacy_metadata)
        all_metadata.extend(site_metadata)
    
    logging.info("Total metadata loaded for %d loggers", len(all_metadata))
    return all_metadata
    """Load logger metadata from CSV file."""
    metadata = []
    if not metadata_path.exists():
        logging.error("Metadata file not found: %s", metadata_path)
        return metadata
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only include rows with valid coordinates
                if row.get("LAT") and row.get("LON") and row.get("ID"):
                    try:
                        lat = float(row["LAT"])
                        lon = float(row["LON"])
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            row["LAT"] = lat
                            row["LON"] = lon
                            metadata.append(row)
                    except ValueError:
                        logging.warning("Invalid coordinates for logger %s", row.get("ID", "unknown"))
        
        logging.info("Loaded metadata for %d loggers with valid coordinates", len(metadata))
    except Exception as e:
        logging.error("Failed to load metadata: %s", e)
    
    return metadata


def find_plot_files(plots_dir: Path) -> Dict[str, Path]:
    """Find all PNG plot files and map them by logger ID."""
    plot_files = {}
    if not plots_dir.exists():
        logging.warning("Plots directory not found: %s", plots_dir)
        return plot_files
    
    for png_file in plots_dir.glob("*.png"):
        # Extract logger ID from filename
        # Handle both old format (A538D8_20220916084244.png) and new format (A538D8_combined.png)
        if "_combined.png" in png_file.name:
            # New format: logger_id_combined.png
            logger_id = png_file.stem.replace("_combined", "")
        else:
            # Old format: extract first part before underscore
            logger_id = png_file.stem.split('_')[0]
        
        # Keep the most recent/relevant file for each logger
        if logger_id not in plot_files:
            plot_files[logger_id] = png_file
        else:
            # Prefer combined files over individual files
            if "_combined" in png_file.name:
                plot_files[logger_id] = png_file
    
    logging.info("Found plot files for %d loggers", len(plot_files))
    return plot_files


def create_popup_content(logger_data: Dict[str, str], plot_file: Optional[Path] = None) -> str:
    """Create HTML content for the popup."""
    logger_id = logger_data.get("ID", "Unknown")
    
    # Handle different metadata column names
    garmin_wp = logger_data.get("GARMIN WP") or logger_data.get("WP") or logger_data.get("WP_ID", "")
    elevation = logger_data.get("ELE") or logger_data.get("Altitude", "")
    surface = logger_data.get("surface") or logger_data.get("material", "")
    notes = logger_data.get("Notes") or logger_data.get("comments", "")
    date = logger_data.get("Date") or logger_data.get("Date installed", "")
    
    # Additional sangvor-specific fields
    ble_type = logger_data.get("Type", "")
    access_code = logger_data.get("Access Code", "")
    
    html = f"""
    <div style="width: 300px;">
        <h4>Logger {logger_id}</h4>
        <table style="width: 100%; font-size: 12px;">
    """
    
    if ble_type:
        html += f"<tr><td><b>Type:</b></td><td>{ble_type}</td></tr>"
    if garmin_wp:
        html += f"<tr><td><b>Waypoint:</b></td><td>{garmin_wp}</td></tr>"
    if elevation:
        try:
            elev_val = float(elevation)
            html += f"<tr><td><b>Elevation:</b></td><td>{elev_val:.0f} m</td></tr>"
        except ValueError:
            html += f"<tr><td><b>Elevation:</b></td><td>{elevation}</td></tr>"
    if surface:
        html += f"<tr><td><b>Surface:</b></td><td>{surface}</td></tr>"
    if access_code:
        html += f"<tr><td><b>Access Code:</b></td><td>{access_code}</td></tr>"
    if date:
        html += f"<tr><td><b>Installed:</b></td><td>{date}</td></tr>"
    if notes:
        html += f"<tr><td><b>Notes:</b></td><td>{notes}</td></tr>"
    
    html += "</table>"
    
    if plot_file and plot_file.exists():
        # Create relative path for the link including the plots directory
        relative_path = f"plots/{plot_file.name}"
        html += f"""
        <div style="margin-top: 10px;">
            <a href="{relative_path}" target="_blank" style="
                background-color: #4CAF50; 
                color: white; 
                padding: 8px 16px; 
                text-decoration: none; 
                border-radius: 4px;
                display: inline-block;
                font-size: 12px;
            ">View Temperature Plot</a>
        </div>
        """
    else:
        # Debug info - show if plot file should exist
        html += f"""
        <div style="margin-top: 10px; font-size: 10px; color: #666;">
            Looking for: {logger_id}_combined.png
        </div>
        """
    
    html += "</div>"
    return html


def get_marker_color(surface: str) -> str:
    """Get marker color based on surface type."""
    surface_lower = surface.lower() if surface else ""
    
    if "block" in surface_lower or "rock" in surface_lower:
        return "gray"
    elif "silt" in surface_lower or "sediment" in surface_lower:
        return "darkred"
    elif "gravel" in surface_lower:
        return "orange"
    elif "sand" in surface_lower:
        return "beige"
    elif "pasture" in surface_lower:
        return "green"
    elif "void" in surface_lower:
        return "black"
    elif "morraine" in surface_lower or "moraine" in surface_lower:
        return "purple"
    else:
        return "blue"


def create_interactive_map(metadata: List[Dict[str, str]], plot_files: Dict[str, Path], 
                          output_path: Path) -> None:
    """Create an interactive folium map with logger locations."""
    
    if not metadata:
        logging.error("No metadata available to create map")
        return
    
    # Calculate map center from logger locations
    lats = [row["LAT"] for row in metadata]
    lons = [row["LON"] for row in metadata]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    # Calculate bounds for auto-zoom to show all points
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    
    # Create base map with wider initial view
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,  # More zoomed out to show both sites
        tiles=None  # We'll add custom tiles
    )
    
    # Add different tile layers
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
        name='OpenTopoMap',
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
        name='Satellite',
        control=True
    ).add_to(m)
    
    # Add markers for each logger
    for logger_data in metadata:
        logger_id = logger_data["ID"]
        lat = logger_data["LAT"]
        lon = logger_data["LON"]
        surface = logger_data.get("surface") or logger_data.get("material", "")
        logger_type = logger_data.get("Type", "")
        
        # Get corresponding plot file
        plot_file = plot_files.get(logger_id)
        
        # Create popup content
        popup_content = create_popup_content(logger_data, plot_file)
        
        # Determine marker color based on surface type
        marker_color = get_marker_color(surface)
        
        # Create tooltip with more info
        tooltip_text = f"Logger {logger_id}"
        if logger_type:
            tooltip_text += f" ({logger_type})"
        if surface:
            tooltip_text += f" - {surface}"
        
        # Create marker
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=350),
            tooltip=tooltip_text,
            icon=folium.Icon(color=marker_color, icon='thermometer-half', prefix='fa')
        ).add_to(m)
    
    # Fit map bounds to show all markers
    if len(metadata) > 1:
        southwest = [min(lats), min(lons)]
        northeast = [max(lats), max(lons)]
        m.fit_bounds([southwest, northeast], padding=(20, 20))
    
    # Add a marker size legend
    legend_html = """
    <div style="position: fixed; 
                top: 10px; right: 10px; width: 200px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <h4>Surface Types</h4>
    <p><i class="fa fa-circle" style="color:gray"></i> Blocks/Rock</p>
    <p><i class="fa fa-circle" style="color:darkred"></i> Silt/Sediment</p>
    <p><i class="fa fa-circle" style="color:orange"></i> Gravel</p>
    <p><i class="fa fa-circle" style="color:beige"></i> Sand</p>
    <p><i class="fa fa-circle" style="color:green"></i> Pasture</p>
    <p><i class="fa fa-circle" style="color:black"></i> Void</p>
    <p><i class="fa fa-circle" style="color:purple"></i> Moraine</p>
    <p><i class="fa fa-circle" style="color:blue"></i> Other</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add fullscreen plugin
    plugins.Fullscreen().add_to(m)
    
    # Add measure plugin
    plugins.MeasureControl().add_to(m)
    
    # Save map
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    logging.info("Interactive map saved to: %s", output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/fan_loggers_meta.csv"),
        help="Path to metadata CSV file with logger information",
    )
    parser.add_argument(
        "--plots-dir",
        type=Path,
        default=Path("plots"),
        help="Directory containing the temperature plot PNG files",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("data"),
        help="Root directory containing CSV data files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("logger_map.html"),
        help="Output HTML file for the interactive map",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    
    # Step 1: Generate/update all temperature plots first
    logging.info("Step 1: Generating temperature plots...")
    try:
        run_plotting(args.data_root, args.plots_dir)
        logging.info("Temperature plots generated successfully")
    except Exception as e:
        logging.error("Failed to generate plots: %s", e)
        return
    
    # Step 2: Load metadata from specified file or auto-discover
    logging.info("Step 2: Loading metadata...")
    if args.metadata and args.metadata.exists():
        metadata = load_metadata(args.metadata)
    else:
        # Auto-discover metadata from data directory structure
        # Try to find data directory relative to plots directory or current working directory
        potential_data_roots = [
            args.data_root,
            args.plots_dir.parent / "data",
            Path.cwd() / "data",
            Path.cwd()
        ]
        
        metadata = []
        for data_root in potential_data_roots:
            if data_root.exists():
                logging.info("Trying data root: %s", data_root)
                metadata = load_all_metadata(data_root)
                if metadata:
                    break
    
    if not metadata:
        logging.error("No valid metadata found")
        return
    
    # Step 3: Find plot files
    logging.info("Step 3: Finding plot files...")
    plot_files = find_plot_files(args.plots_dir)
    
    # Step 4: Create interactive map
    logging.info("Step 4: Creating interactive map...")
    create_interactive_map(metadata, plot_files, args.output)
    
    print(f"\n✅ Interactive map created: {args.output}")
    print(f"📊 Generated plots for {len(plot_files)} loggers")
    print(f"📍 Mapped {len(metadata)} logger locations")
    print(f"🌐 Open {args.output} in your web browser to view the map")


if __name__ == "__main__":
    main()