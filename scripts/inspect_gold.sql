SELECT
    table_name,
    column_name,
    data_type,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'gold'
  AND table_name IN (
      'sales',
      'daily_sales',
      'product_performance'
  )
ORDER BY table_name, ordinal_position;
