-- 1. Comparaison des ventes avec les agrégats quotidiens
SELECT
    COUNT(*) AS sale_lines,
    COUNT(DISTINCT invoice) AS invoices,
    SUM(sales_quantity) AS quantity_sold,
    ROUND(SUM(sales_revenue), 2) AS revenue
FROM gold.sales
WHERE transaction_type = 'sale';

SELECT
    SUM(transaction_lines) AS daily_lines,
    SUM(quantity_sold) AS quantity_sold,
    ROUND(SUM(revenue), 2) AS revenue
FROM gold.daily_sales;

-- 2. Vérifier les produits aux volumes ou statistiques inhabituels
SELECT
    stock_code,
    product_description,
    quantity_sold,
    revenue,
    transaction_lines,
    distinct_invoices,
    distinct_customers
FROM gold.product_performance
WHERE distinct_invoices <= 1
   OR distinct_customers <= 1
ORDER BY revenue DESC NULLS LAST
LIMIT 20;

-- 3. Vérifier les valeurs nulles dans les ventes
SELECT
    COUNT(*) FILTER (WHERE sale_date IS NULL) AS missing_sale_date,
    COUNT(*) FILTER (WHERE stock_code IS NULL) AS missing_stock_code,
    COUNT(*) FILTER (WHERE customer_id IS NULL) AS missing_customer_id,
    COUNT(*) FILTER (WHERE sales_revenue IS NULL) AS missing_revenue
FROM gold.sales;