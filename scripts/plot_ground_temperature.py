#!/usr/bin/env python3
"""Generate ground temperature plots for each logger CSV file."""

from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt

DATE_FORMAT = "%d.%m.%Y %H:%M:%S"


def group_files_by_logger_id(csv_files: List[Path]) -> Dict[str, List[Path]]:
    """Group CSV files by logger ID to handle multiple files per logger."""
    grouped = {}
    
    for csv_file in csv_files:
        # Skip metadata files
        if "metadata" in str(csv_file) or csv_file.name.endswith("meta.csv"):
            continue
            
        # Extract logger ID from filename
        if "sangvor" in str(csv_file).lower():
            # For sangvor files: 2005-0070_20220907_0332.csv -> 2005-0070
            logger_id = csv_file.stem.split('_')[0]
        else:
            # For fanmountains files: A538D8_20220916084244.csv -> A538D8
            # Or from directory structure: A538D8/raw/filename.csv -> A538D8
            logger_id = csv_file.stem.split('_')[0]
            if not logger_id or len(logger_id) < 3:
                # Try to get from parent directory
                if csv_file.parent.parent.name and len(csv_file.parent.parent.name) > 3:
                    logger_id = csv_file.parent.parent.name
        
        if logger_id:
            if logger_id not in grouped:
                grouped[logger_id] = []
            grouped[logger_id].append(csv_file)
    
    # Sort files within each group by filename (approximate chronological order)
    for logger_id in grouped:
        grouped[logger_id].sort()
        
    logging.info("Grouped %d files into %d logger groups", sum(len(files) for files in grouped.values()), len(grouped))
    return grouped


def concatenate_timeseries(file_group: List[Path]) -> Tuple[List[datetime], List[float]]:
    """Concatenate multiple files for the same logger into one timeseries."""
    all_timestamps = []
    all_temperatures = []
    
    for csv_file in file_group:
        logging.info("  Reading %s", csv_file.name)
        skip_lines = determine_skip_lines(csv_file)
        timestamps, temps = parse_logger_file(csv_file, skip_lines)
        
        # Combine data
        all_timestamps.extend(timestamps)
        all_temperatures.extend(temps)
    
    if not all_timestamps:
        return [], []
    
    # Sort by timestamp to handle files that might be out of order
    combined = list(zip(all_timestamps, all_temperatures))
    combined.sort(key=lambda x: x[0])
    
    # Remove duplicates (same timestamp)
    unique_data = []
    last_timestamp = None
    for timestamp, temp in combined:
        if timestamp != last_timestamp:
            unique_data.append((timestamp, temp))
            last_timestamp = timestamp
    
    timestamps, temperatures = zip(*unique_data) if unique_data else ([], [])
    
    logging.info("  Combined into %d unique data points", len(timestamps))
    return list(timestamps), list(temperatures)


def determine_skip_lines(csv_file: Path) -> int:
    """Determine how many lines to skip based on the site/folder structure."""
    # Check if this is a sangvor site file
    if "sangvor" in str(csv_file).lower():
        return 22
    # Default for fanmountains and other sites
    return 12


def load_metadata(metadata_path: Path) -> Dict[str, Dict[str, str]]:
    """Load logger metadata from CSV file."""
    metadata = {}
    if not metadata_path.exists():
        logging.warning("Metadata file not found: %s", metadata_path)
        return metadata
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                logger_id = row.get("ID", "").strip()
                if logger_id:
                    metadata[logger_id] = row
        logging.info("Loaded metadata for %d loggers from %s", len(metadata), metadata_path.name)
    except Exception as e:
        logging.error("Failed to load metadata from %s: %s", metadata_path, e)
    
    return metadata


def load_all_metadata(data_root: Path) -> Dict[str, Dict[str, str]]:
    """Load metadata from all metadata files in the data directory."""
    all_metadata = {}
    
    # Look for metadata files in the metadata directory
    metadata_dir = data_root / "metadata"
    if metadata_dir.exists():
        for metadata_file in metadata_dir.glob("*.csv"):
            logging.info("Loading metadata from: %s", metadata_file)
            site_metadata = load_metadata(metadata_file)
            all_metadata.update(site_metadata)
    
    # Also check for legacy location
    legacy_metadata = data_root / "fan_loggers_meta.csv"
    if legacy_metadata.exists():
        logging.info("Loading legacy metadata from: %s", legacy_metadata)
        site_metadata = load_metadata(legacy_metadata)
        all_metadata.update(site_metadata)
    
    logging.info("Total metadata loaded for %d loggers", len(all_metadata))
    return all_metadata
    """Load logger metadata from CSV file."""
    metadata = {}
    if not metadata_path.exists():
        logging.warning("Metadata file not found: %s", metadata_path)
        return metadata
    
    try:
        with metadata_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                logger_id = row.get("ID", "").strip()
                if logger_id:
                    metadata[logger_id] = row
        logging.info("Loaded metadata for %d loggers", len(metadata))
    except Exception as e:
        logging.error("Failed to load metadata: %s", e)
    
    return metadata


def find_csv_files(root: Path) -> List[Path]:
    """Return all CSV files under *root* sorted by path."""
    return sorted(p for p in root.rglob("*.csv") if p.is_file())


def parse_logger_file(path: Path, skip_lines: int = 12) -> Tuple[List[datetime], List[float]]:
    """Extract timestamps and temperatures from a logger CSV file."""
    timestamps: List[datetime] = []
    temperatures: List[float] = []
    
    # Detect if this is a sangvor file (different format)
    is_sangvor = "sangvor" in str(path).lower()
    
    if is_sangvor:
        return parse_sangvor_file(path, skip_lines)
    else:
        return parse_fanmountains_file(path, skip_lines)


def parse_sangvor_file(path: Path, skip_lines: int = 22) -> Tuple[List[datetime], List[float]]:
    """Parse sangvor BLE logger files with semicolon separator."""
    timestamps: List[datetime] = []
    temperatures: List[float] = []
    
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for row_num, line in enumerate(handle, 1):
            # Skip header lines
            if row_num <= skip_lines:
                continue
                
            line = line.strip()
            if not line or ';' not in line:
                continue
                
            parts = line.split(';')
            if len(parts) < 2:
                continue
                
            try:
                # Format is: DD.MM.YYYY HH:MM:SS;temperature
                datetime_str = parts[0].strip()
                temperature_str = parts[1].strip()
                
                # Parse German date format DD.MM.YYYY HH:MM:SS
                timestamp = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M:%S")
                temperature = float(temperature_str)
                
                timestamps.append(timestamp)
                temperatures.append(temperature)
                
            except ValueError as e:
                logging.debug("Skipping unparsable row at line %d in %s: %s (error: %s)", row_num, path, line, e)
                continue
    
    logging.info("Parsed %d data points from %s", len(timestamps), path.name)
    return timestamps, temperatures


def parse_fanmountains_file(path: Path, skip_lines: int = 12) -> Tuple[List[datetime], List[float]]:
    """Parse fanmountains logger files with comma separator."""
    timestamps: List[datetime] = []
    temperatures: List[float] = []

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        reader = csv.reader(handle)
        for row_num, row in enumerate(reader, 1):
            # Skip specified number of header/metadata rows
            if row_num <= skip_lines:
                continue
                
            if not row:
                continue
            first = row[0].strip()
            if not first or first.startswith("<"):
                # Skip metadata rows such as <TIME: ...>
                continue
            if first.upper() == "NO":
                # Skip header line.
                logging.debug("Skipping header row at line %d: %s", row_num, row)
                continue

            try:
                # Rows are in the form NO,TIME,#1:oC,HK-BAT:V (battery optional).
                datetime_str = row[1].strip()
                temperature_str = row[2].strip()
            except IndexError:
                logging.debug("Skipping malformed row at line %d in %s: %s", row_num, path, row)
                continue

            try:
                timestamps.append(datetime.strptime(datetime_str, DATE_FORMAT))
                temperatures.append(float(temperature_str))
            except ValueError as e:
                logging.debug("Skipping unparsable row at line %d in %s: %s (error: %s)", row_num, path, row, e)
                continue

    logging.info("Parsed %d data points from %s", len(timestamps), path.name)
    
    # Ensure arrays are the same length
    min_length = min(len(timestamps), len(temperatures))
    if min_length < len(timestamps) or min_length < len(temperatures):
        logging.warning("Mismatched data points in %s: %d timestamps, %d temperatures. Using first %d points.", 
                       path.name, len(timestamps), len(temperatures), min_length)
        timestamps = timestamps[:min_length]
        temperatures = temperatures[:min_length]
    
    return timestamps, temperatures


def build_plot(times: List[datetime], temps: List[float], title: str, output_path: Path, 
               metadata: Optional[Dict[str, str]] = None) -> None:
    """Create and save a temperature time-series plot."""
    if not times:
        logging.warning("No data points available for %s, skipping plot", output_path.stem)
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(times, temps, color="tab:blue", linewidth=1.0)
    
    # Enhanced title with metadata
    plot_title = title
    if metadata:
        location_info = []
        if metadata.get("ELE"):
            location_info.append(f"{float(metadata['ELE']):.0f}m")
        if metadata.get("surface"):
            location_info.append(metadata["surface"])
        if metadata.get("Notes"):
            location_info.append(metadata["Notes"])
        
        if location_info:
            plot_title += f"\n{' | '.join(location_info)}"
    
    ax.set_title(plot_title, fontsize=12)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.6)
    
    # Add summary statistics
    if temps:
        min_temp, max_temp = min(temps), max(temps)
        avg_temp = sum(temps) / len(temps)
        ax.text(0.02, 0.98, f"Min: {min_temp:.1f}°C\nMax: {max_temp:.1f}°C\nAvg: {avg_temp:.1f}°C", 
                transform=ax.transAxes, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    fig.autofmt_xdate()
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def infer_title(logger_id: str, file_group: List[Path], metadata_dict: Dict[str, Dict[str, str]]) -> Tuple[str, Optional[Dict[str, str]]]:
    """Generate a human-friendly title from the logger ID and return associated metadata."""
    
    # Try direct match first
    metadata = metadata_dict.get(logger_id)
    
    if metadata:
        garmin_wp = metadata.get("GARMIN WP") or metadata.get("WP", "")
        title = f"Logger {logger_id} (WP {garmin_wp})" if garmin_wp else f"Logger {logger_id}"
        
        # Add file count info
        if len(file_group) > 1:
            title += f" ({len(file_group)} files)"
            
        return title, metadata
    else:
        # Fallback to basic title
        title = f"Logger {logger_id}"
        if len(file_group) > 1:
            title += f" ({len(file_group)} files)"
        return title, None


def run(csv_root: Path, output_dir: Path, metadata_path: Optional[Path] = None) -> None:
    csv_files = find_csv_files(csv_root)
    if not csv_files:
        logging.error("No CSV files found under %s", csv_root)
        return

    # Load metadata from all available sources
    if metadata_path and metadata_path.exists():
        metadata_dict = load_metadata(metadata_path)
    else:
        metadata_dict = load_all_metadata(csv_root)

    # Group files by logger ID
    grouped_files = group_files_by_logger_id(csv_files)
    
    logging.info("Found %d CSV files grouped into %d loggers", len(csv_files), len(grouped_files))

    for logger_id, file_group in grouped_files.items():
        logging.info("Processing logger %s (%d files)", logger_id, len(file_group))
        
        # Concatenate all files for this logger
        timestamps, temps = concatenate_timeseries(file_group)
        if not timestamps:
            logging.warning("No data found for logger %s", logger_id)
            continue
            
        title, metadata = infer_title(logger_id, file_group, metadata_dict)
        plot_name = f"{logger_id}_combined.png"
        output_path = output_dir / plot_name
        build_plot(timestamps, temps, title, output_path, metadata)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Root directory to scan for logger CSV files (default: repository root)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "plots",
        help="Directory where plot images will be stored",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        help="Path to metadata CSV file with logger information",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s")
    
    run(args.data_root, args.output_dir, args.metadata)


if __name__ == "__main__":
    main()
