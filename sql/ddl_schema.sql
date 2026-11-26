CREATE TABLE IF NOT EXISTS stg_regional_po (
    po_number        VARCHAR(50)    NOT NULL,
    region           VARCHAR(20)    NOT NULL,
    supplier_id      VARCHAR(50)    NOT NULL,
    material_code    VARCHAR(50)    NOT NULL,
    ordered_qty      INTEGER        NOT NULL,
    unit_price_usd   NUMERIC(10,2)  NOT NULL,
    total_po_value   NUMERIC(12,2)  NOT NULL,
    order_date       DATE           NOT NULL,
    source_file_name VARCHAR(255)   NOT NULL,
    loaded_at        TIMESTAMP      NOT NULL
);

CREATE TABLE IF NOT EXISTS etl_file_audit_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name     VARCHAR(255) NOT NULL,
    rows_loaded   INTEGER      NOT NULL,
    load_status   VARCHAR(20)  NOT NULL,
    error_message VARCHAR(255),
    processed_at  TIMESTAMP    NOT NULL
);