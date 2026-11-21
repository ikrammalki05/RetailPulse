-- 1. Identifier les tables Silver disponibles
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'silver'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 2. Examiner les transactions du produit inhabituel
SELECT
    sale_id,
    invoice,
    stock_code,
    description,
    quantity,
    price,
    customer_id,
    invoice_date,
    line_amount,
    transaction_type,
    sales_quantity,
    sales_revenue
FROM gold.sales
WHERE stock_code = '23843'
ORDER BY invoice_date
LIMIT 20;

-- 3. Vérifier les clients manquants par type de transaction
SELECT
    transaction_type,
    COUNT(*) AS total_lines,
    COUNT(*) FILTER (
        WHERE customer_id IS NULL
    ) AS missing_customers,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE customer_id IS NULL
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS missing_customer_pct
FROM gold.sales
GROUP BY transaction_type
ORDER BY transaction_type;

-- 4. Vérifier les types de transactions du produit
SELECT
    transaction_type,
    COUNT(*) AS total_lines,
    SUM(quantity) AS raw_quantity,
    SUM(sales_quantity) AS sales_quantity,
    ROUND(SUM(sales_revenue), 2) AS revenue
FROM gold.sales
WHERE stock_code = '23843'
GROUP BY transaction_type
ORDER BY transaction_type;