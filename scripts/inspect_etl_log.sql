SELECT
    load_id,
    pipeline_name,
    source_name,
    target_table,
    rows_loaded,
    status,
    started_at,
    completed_at,
    error_message
FROM gold.etl_load_log
ORDER BY started_at DESC
LIMIT 20;