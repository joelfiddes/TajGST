# TajGST - Tajikistan Ground Surface Temperature Analysis

This project analyzes ground surface temperature data from temperature loggers deployed in the Fan Mountains, Tajikistan, and Sangvor region. The data is used to study ground temperature patterns and create interactive visualizations for scientific research.

## Project Structure

```
TajGST/
├── data/
│   ├── fanmountains/          # Temperature logger data from Fan Mountains
│   │   ├── A538D8/           # Individual logger directories
│   │   │   ├── par/          # Parameter files (.f2p)
│   │   │   └── raw/          # Raw data files (.csv, .f2b)
│   │   └── ...               # Additional logger directories
│   ├── sangvor/              # Temperature data from Sangvor region
│   └── metadata/             # Logger metadata and location information
│       ├── BLE_sangvor_loggers.csv
│       └── fan_loggers_meta.csv
├── plots/                    # Generated temperature plots
├── scripts/                  # Analysis and visualization scripts
│   ├── interactive_map.py    # Creates interactive map with logger locations
│   ├── plot_ground_temperature.py  # Generates temperature plots
│   └── apply_time_offset_sangvor.py  # Time offset correction utility
└── logger_map.html          # Interactive map output
```

## Features

### Interactive Map
- **Location Visualization**: Shows all temperature logger locations on an interactive map
- **Data Integration**: Links logger positions with temperature data plots
- **Metadata Display**: Shows logger details including elevation, installation date, and surface type

### Temperature Analysis
- **Multi-Logger Support**: Processes data from multiple temperature loggers
- **Time Series Plotting**: Generates temperature plots over time for each logger
- **Data Grouping**: Automatically groups multiple files per logger ID
- **Format Support**: Handles different data formats (Fan Mountains and Sangvor formats)

### Data Processing
- **Time Offset Correction**: Applies time corrections to Sangvor format data
- **Automated Processing**: Batch processing of multiple logger files
- **Quality Control**: Handles missing data and format variations

## Usage

### Generate Interactive Map
```bash
python scripts/interactive_map.py
```
This creates `logger_map.html` with an interactive map showing all logger locations.

### Plot Temperature Data
```bash
python scripts/plot_ground_temperature.py
```
Generates individual temperature plots for each logger and saves them in the `plots/` directory.

### Apply Time Offset (Sangvor Data)
```bash
python scripts/apply_time_offset_sangvor.py --input-dir data/sangvor --offset "438d 3h 29min 29sec"
```
Applies time corrections to Sangvor format files, creating new files with `_offset` suffix.

## Data Formats

### Fan Mountains Data
- **Parameter files** (`.f2p`): Logger configuration and metadata
- **Raw data files** (`.csv`, `.f2b`): Temperature measurements with timestamps
- **Directory structure**: Organized by logger UUID (e.g., A538D8, A538DB)

### Sangvor Data
- **CSV format**: Temperature data with timestamp format `DD.MM.YYYY HH:MM:SS`
- **File naming**: `{logger_id}_{date}_{time}.csv` (e.g., `2005-0070_20220907_0332.csv`)
- **Skip lines**: First 22 lines contain metadata

### Metadata
- **Logger locations**: GPS coordinates, elevation, installation details
- **Surface types**: Description of ground surface at logger location
- **Access codes**: Logger-specific identification codes

## Requirements

### Python Dependencies
- `folium` - Interactive map generation
- `matplotlib` - Temperature plot generation
- `pandas` (implied) - Data processing
- Standard library: `csv`, `datetime`, `pathlib`, `argparse`

### Data Requirements
- Logger metadata files in `data/metadata/`
- Temperature data files in appropriate directory structure
- GPS coordinates for logger locations

## Research Context

This project supports ground surface temperature research in high-altitude environments of Central Asia. The temperature loggers collect data to study:
- **Permafrost dynamics** in mountain environments
- **Climate change impacts** on ground temperatures
- **Spatial temperature variations** across different elevations and surface types
- **Long-term temperature trends** in remote mountain locations

## File Formats and Standards

- **Timestamps**: Various formats supported (DD.MM.YYYY HH:MM:SS for Sangvor, others for Fan Mountains)
- **Coordinates**: Decimal degrees (WGS84)
- **Temperature**: Degrees Celsius
- **Elevation**: Meters above sea level

## Contributing

When adding new data:
1. Place logger data in appropriate directory structure under `data/`
2. Update metadata files with logger location and installation details
3. Run analysis scripts to generate updated plots and maps
4. Ensure consistent file naming conventions

## Output

- **Interactive Map**: `logger_map.html` - Browse logger locations and access plots
- **Temperature Plots**: Individual PNG files in `plots/` directory
- **Processed Data**: Time-corrected data files with `_offset` suffix