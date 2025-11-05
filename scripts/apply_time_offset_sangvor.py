#!/usr/bin/env python3
"""
Apply a fixed time offset to all timestamps in sangvor-format logger files.

Usage:
  python apply_time_offset_sangvor.py --input-dir /path/to/shifted20042025 --offset '438d 3h 29min 29sec'

Writes new files with '_offset' appended to the filename in the same directory.
"""
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import re

# Default sangvor skip lines
SKIP_LINES = 22
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"


def parse_offset(offset_str: str) -> timedelta:
    """Parse offset string like '438d 3h 29min 29sec' into timedelta."""
    pattern = r"(?:(\d+)d)?\s*(?:(\d+)h)?\s*(?:(\d+)min)?\s*(?:(\d+)sec)?"
    match = re.match(pattern, offset_str.replace(' ', ''))
    if not match:
        raise ValueError(f"Invalid offset string: {offset_str}")
    days, hours, minutes, seconds = (int(x) if x else 0 for x in match.groups())
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def process_file(file_path: Path, offset: timedelta) -> None:
    output_path = file_path.parent / (file_path.stem + "_offset" + file_path.suffix)
    with file_path.open("r", encoding="utf-8", errors="ignore") as infile, \
         output_path.open("w", encoding="utf-8") as outfile:
        for i, line in enumerate(infile, 1):
            if i <= SKIP_LINES:
                outfile.write(line)
                continue
            line = line.rstrip("\n")
            if not line or ';' not in line:
                outfile.write(line + "\n")
                continue
            parts = line.split(';')
            if len(parts) < 2:
                outfile.write(line + "\n")
                continue
            try:
                dt = datetime.strptime(parts[0].strip(), DATE_FORMAT)
                dt_shifted = dt + offset
                new_line = dt_shifted.strftime(DATE_FORMAT) + ";" + ";".join(parts[1:])
                outfile.write(new_line + "\n")
            except Exception:
                outfile.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(description="Apply a fixed time offset to sangvor logger files.")
    parser.add_argument('--input-dir', type=Path, required=True, help='Directory containing sangvor-format CSV files')
    parser.add_argument('--offset', type=str, default='438d 3h 29min 29sec', help='Offset to add (e.g. "438d 3h 29min 29sec")')
    args = parser.parse_args()

    offset = parse_offset(args.offset)
    files = list(args.input_dir.glob('*.csv'))
    print(f"Processing {len(files)} files in {args.input_dir} with offset {offset}")
    for file_path in files:
        print(f"  Processing {file_path.name}")
        process_file(file_path, offset)
    print("Done.")

if __name__ == "__main__":
    main()
