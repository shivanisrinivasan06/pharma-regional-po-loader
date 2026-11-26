###############################################################################
# Script Name    : ingest_regional_po.py
# Description    : Dynamically scan the landing folder for regional purchase
#                  order CSV files, validate each file against business gates,
#                  load valid records into a SQLite staging table with audit
#                  metadata, log every file result to an audit control table,
#                  and route files to archive or rejected folders.
# Created By     : Shivani
# Created Date   : 26/11/2026
# Modified Date  : 26/11/2026
# Modified By    : Shivani
# Comments       : Config-driven paths. No hardcoded filenames.
###############################################################################

"""
Pseudocode :

Step 1 : Read database and folder paths from config/config.ini.
Step 2 : Scan the incoming folder for CSV files and sort them alphabetically.
Step 3 : Gate 1: reject empty files with status FAILED and error EMPTY_FILE.
Step 4 : Gate 2: reject files missing any of the 7 mandatory columns with error MISSING_REQUIRED_COLUMNS.
Step 5 : Calculate total_po_value and add source_file_name and loaded_at (UTC) columns.
Step 6 : Insert valid records into stg_regional_po with commit on success and rollback on error.
Step 7 : Move valid files to data/archive/ and failed files to data/rejected/.
Step 8 : Insert one audit row per file into etl_file_audit_log.
Step 9 : Print the batch execution summary in the terminal.

"""

import configparser
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "po_number", "region", "supplier_id", "material_code",
    "ordered_qty", "unit_price_usd", "order_date",
]


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_config(path="config/config.ini"):
    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg


def validate_file(file_path):
    """Returns (dataframe, None) if valid, else (None, error_code)."""
    # Gate 1: non-empty
    if file_path.stat().st_size == 0:
        return None, "EMPTY_FILE"
    try:
        df = pd.read_csv(file_path)
    except pd.errors.EmptyDataError:
        return None, "EMPTY_FILE"
    if df.empty:
        return None, "EMPTY_FILE"

    # Gate 2: required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return None, "MISSING_REQUIRED_COLUMNS"
    return df, None


def load_to_db(conn, df, file_name):
    """Insert rows into staging. Caller handles commit/rollback."""
    df = df.copy()
    df["total_po_value"] = (df["ordered_qty"] * df["unit_price_usd"]).round(2)
    df["source_file_name"] = file_name
    df["loaded_at"] = utc_now()

    cols = ["po_number", "region", "supplier_id", "material_code",
            "ordered_qty", "unit_price_usd", "total_po_value",
            "order_date", "source_file_name", "loaded_at"]
    rows = [tuple(r) for r in df[cols].astype(object).itertuples(index=False)]
    conn.executemany(
        f"INSERT INTO stg_regional_po ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})", rows)
    return len(rows)


def log_audit(conn, file_name, rows_loaded, status, error_message):
    conn.execute(
        "INSERT INTO etl_file_audit_log "
        "(file_name, rows_loaded, load_status, error_message, processed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (file_name, rows_loaded, status, error_message, utc_now()))
    conn.commit()


def main():
    cfg = read_config()
    incoming = Path(cfg["paths"]["incoming_dir"])
    archive = Path(cfg["paths"]["archive_dir"])
    rejected = Path(cfg["paths"]["rejected_dir"])
    archive.mkdir(parents=True, exist_ok=True)
    rejected.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(cfg["database"]["db_path"])
    files = sorted(incoming.glob("*.csv"))
    succeeded = failed = total_rows = 0

    for f in files:
        df, error = validate_file(f)
        rows = 0

        if error is None:
            try:
                rows = load_to_db(conn, df, f.name)
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = f"LOAD_ERROR: {e}"[:255]

        if error is None:
            shutil.move(str(f), str(archive / f.name))
            log_audit(conn, f.name, rows, "SUCCESS", None)
            succeeded += 1
            total_rows += rows
            print(f"[OK]   {f.name}: {rows} rows loaded")
        else:
            shutil.move(str(f), str(rejected / f.name))
            log_audit(conn, f.name, 0, "FAILED", error)
            failed += 1
            print(f"[FAIL] {f.name}: {error}")

    conn.close()

    print("=" * 50)
    print("BATCH INGESTION EXECUTION SUMMARY")
    print("=" * 50)
    print(f"Total Files Scanned : {len(files)}")
    print(f"Files Succeeded     : {succeeded}")
    print(f"Files Failed        : {failed}")
    print(f"Total Rows Loaded   : {total_rows}")
    print("=" * 50)


if __name__ == "__main__":
    main()