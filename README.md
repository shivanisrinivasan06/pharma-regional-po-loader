# Pharma Regional PO Loader

A batch ingestion pipeline for regional pharmaceutical purchase order (PO) CSV files. It scans a landing folder, validates each file, loads valid records into a SQLite staging table, logs every file result in an audit table, and routes files to `archive/` or `rejected/`.

## Architecture

```
data/incoming/  -->  validate (Gate 1, Gate 2)  -->  stg_regional_po
                            |                               |
                            v                               v
                    data/rejected/                    data/archive/
                            |                               |
                            +------> etl_file_audit_log <---+
```

1. Read paths and database settings from `config/config.ini`.
2. Scan `data/incoming/` for `*.csv` files, sorted alphabetically (no hardcoded filenames).
3. **Gate 1:** reject empty files (`EMPTY_FILE`).
4. **Gate 2:** reject files missing any of the 7 mandatory columns (`MISSING_REQUIRED_COLUMNS`).
5. Calculate `total_po_value = ordered_qty * unit_price_usd`, and add `source_file_name` and `loaded_at` (UTC).
6. Insert into `stg_regional_po` in a transaction (commit on success, rollback on error).
7. Move the file to `data/archive/` (valid) or `data/rejected/` (invalid).
8. Write one row per file into `etl_file_audit_log`.
9. Print a summary in the terminal.

## Project Structure

```
pharma-regional-po-loader/
├── config/
│   └── config.example.ini
├── data/
│   ├── incoming/
│   ├── archive/
│   └── rejected/
├── sql/
│   ├── ddl_schema.sql
│   └── verification_queries.sql
├── src/
│   └── ingest_regional_po.py
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

```bash
git clone  https://github.com/shivanisrinivasan06/pharma-regional-po-loader.git
cd pharma-regional-po-loader
python -m venv venv
venv\Scripts\activate          # Windows (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

1. Copy `config/config.example.ini` to `config/config.ini` (this file is ignored by Git).
2. Create the database tables:
   ```bash
   python -c "import sqlite3; c=sqlite3.connect('pharma_po.db'); c.executescript(open('sql/ddl_schema.sql').read()); c.close()"
   ```
3. Put the regional CSV files in `data/incoming/`.

## Run

```bash
python src/ingest_regional_po.py
```

## Validation Rules

| Gate | Check | Status | Error message |
|---|---|---|---|
| 1 | File is not empty | FAILED | `EMPTY_FILE` |
| 2 | All 7 columns present: `po_number`, `region`, `supplier_id`, `material_code`, `ordered_qty`, `unit_price_usd`, `order_date` | FAILED | `MISSING_REQUIRED_COLUMNS` |

## Sample Output

```
[FAIL] po_bad_schema.csv: MISSING_REQUIRED_COLUMNS
[FAIL] po_empty.csv: EMPTY_FILE
[OK]   po_north.csv: 3 rows loaded
[OK]   po_south.csv: 3 rows loaded
[OK]   po_west.csv: 2 rows loaded
==================================================
BATCH INGESTION EXECUTION SUMMARY
==================================================
Total Files Scanned : 5
Files Succeeded     : 3
Files Failed        : 2
Total Rows Loaded   : 8
==================================================
```

## Verification

Run the queries in `sql/verification_queries.sql` against `pharma_po.db` to check the audit log and regional spend.

## Re-running a test

Delete `pharma_po.db`, recreate the tables, and copy the sample CSV files back into `data/incoming/`. Otherwise you will get duplicate rows.