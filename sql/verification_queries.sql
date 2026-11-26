-- Query 1: Audit Log Verification
SELECT file_name, rows_loaded, load_status, error_message
FROM etl_file_audit_log
ORDER BY file_name;

-- Query 2: Regional Spend & Order Rollup
SELECT
    region,
    source_file_name,
    COUNT(*) AS po_count,
    SUM(ordered_qty) AS total_units,
    ROUND(SUM(total_po_value), 2) AS total_spend_usd
FROM stg_regional_po
GROUP BY region, source_file_name
ORDER BY total_spend_usd DESC;