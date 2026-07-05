#!/usr/bin/env python3
"""
Organize raw Sensor Logger exports into data/train and data/test using a
manifest that maps each raw recording to an activity/split/index.

Setup:
  1. Export each recording from Sensor Logger as a .zip (or unzip it yourself)
     and drop it into raw_exports/.
  2. Fill in manifest.csv (copy manifest_template.csv) with one row per
     recording: which raw file/folder it is, which activity it is, whether
     it's train or test, and a running index per activity+split.
  3. Run:
       python scripts/organize_recordings.py --manifest manifest.csv

Manifest columns:
  source    name of the exported recording folder or .zip file inside raw_exports/
  activity  standing | walking | jumping | still
  split     train | test
  index     integer used to number the output file (1, 2, 3, ...)
  notes     optional free text (phone position, pace, location, etc.)

For each row this script:
  1. Locates the recording in raw_exports/ (folder or .zip).
  2. Extracts it if it's a .zip.
  3. Finds Accelerometer.csv and Gyroscope.csv inside it.
  4. Copies them to:
       data/<split>/<activity>_<split>_<index>_accel.csv
       data/<split>/<activity>_<split>_<index>_gyro.csv
  5. Computes actual recorded duration from each file's timestamp column.
  6. Writes/updates recording_log.csv with one row per recording.
"""
import argparse
import csv
import shutil
import zipfile
from pathlib import Path

SENSOR_FILES = {
    "accel": "Accelerometer.csv",
    "gyro": "Gyroscope.csv",
}


def find_recording_dir(raw_dir: Path, source: str) -> Path:
    candidate = raw_dir / source
    if candidate.is_dir():
        return candidate

    zip_candidate = raw_dir / source
    if zip_candidate.suffix != ".zip":
        zip_candidate = raw_dir / f"{source}.zip"
    if zip_candidate.exists():
        extract_to = raw_dir / zip_candidate.stem
        if not extract_to.exists():
            with zipfile.ZipFile(zip_candidate) as zf:
                zf.extractall(extract_to)
        return extract_to

    raise FileNotFoundError(
        f"Could not find recording '{source}' as a folder or .zip in {raw_dir}"
    )


def find_sensor_csv(recording_dir: Path, filename: str) -> Path:
    matches = list(recording_dir.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"{filename} not found under {recording_dir}")
    return matches[0]


def compute_duration_seconds(csv_path: Path) -> float:
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return float("nan")
        timestamp_col = next(
            (c for c in reader.fieldnames if "time" in c.lower()), None
        )
        if timestamp_col is None:
            return float("nan")
        timestamps = [
            float(row[timestamp_col]) for row in reader if row.get(timestamp_col)
        ]
    if not timestamps:
        return float("nan")
    span = max(timestamps) - min(timestamps)
    if span > 1e6:  # nanoseconds since epoch -> seconds
        span /= 1e9
    return round(span, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("raw_exports"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--log", type=Path, default=Path("recording_log.csv"))
    args = parser.parse_args()

    with open(args.manifest, newline="") as f:
        manifest_rows = list(csv.DictReader(f))

    log_rows = []
    errors = []

    for row in manifest_rows:
        source = row["source"].strip()
        activity = row["activity"].strip().lower()
        split = row["split"].strip().lower()
        index = int(row["index"])
        notes = row.get("notes", "").strip()

        try:
            recording_dir = find_recording_dir(args.raw_dir, source)
            out_dir = args.data_dir / split
            out_dir.mkdir(parents=True, exist_ok=True)

            durations = []
            for kind, filename in SENSOR_FILES.items():
                src_csv = find_sensor_csv(recording_dir, filename)
                dest_name = f"{activity}_{split}_{index:02d}_{kind}.csv"
                dest_path = out_dir / dest_name
                shutil.copy2(src_csv, dest_path)
                durations.append(compute_duration_seconds(src_csv))
                print(f"  {source} -> {dest_path}")

            valid_durations = [d for d in durations if d == d]  # drop NaN
            duration = round(max(valid_durations), 2) if valid_durations else ""

            log_rows.append(
                {
                    "filename_prefix": f"{activity}_{split}_{index:02d}",
                    "activity": activity,
                    "split": split,
                    "source": source,
                    "duration_s": duration,
                    "notes": notes,
                }
            )
        except FileNotFoundError as e:
            errors.append(f"{source}: {e}")

    fieldnames = ["filename_prefix", "activity", "split", "source", "duration_s", "notes"]
    with open(args.log, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"\nDone. {len(log_rows)}/{len(manifest_rows)} recordings organized.")
    print(f"Log written to {args.log}")
    if errors:
        print("\nSkipped due to errors:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
