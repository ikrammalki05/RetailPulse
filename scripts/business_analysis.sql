-- RetailPulse | Business Analytics
-- Source : gold.sales, gold.daily_sales, gold.product_performance
-- Les KPI de chiffre d'affaires ci-dessous portent sur les lignes classees
-- comme ventes valides par le pipeline Gold. Retours et annulations sont
-- presentes separement et ne sont pas deduits du chiffre d'affaires.

-- 1. Tableau de bord executif : ventes, commandes, clients et panier moyen.
WITH sales AS (
    SELECT *
    FROM gold.sales
    WHERE transaction_type = 'sale'
)
SELECT
    COUNT(*) AS transaction_lines,
    COUNT(DISTINCT invoice) AS orders,
    COUNT(DISTINCT customer_id) AS identified_customers,
    SUM(sales_quantity) AS units_sold,
    ROUND(SUM(sales_revenue), 2) AS gross_sales_revenue,
    ROUND(
        SUM(sales_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2
    ) AS average_order_value,
    MIN(sale_date) AS first_sale_date,
    MAX(sale_date) AS last_sale_date
FROM sales;

-- 2. Qualite du chiffre d'affaires : mix ventes, retours et autres lignes.
SELECT
    transaction_type,
    COUNT(*) AS transaction_lines,
    COUNT(DISTINCT invoice) AS invoices,
    SUM(quantity) AS signed_quantity,
    ROUND(SUM(line_amount), 2) AS signed_line_amount
FROM gold.sales
GROUP BY transaction_type
ORDER BY transaction_lines DESC;

-- 3. Tendance mensuelle : chiffre d'affaires valide et variation mensuelle.
WITH monthly AS (
    SELECT
        DATE_TRUNC('month', sale_date)::date AS sale_month,
        COUNT(DISTINCT invoice) AS orders,
        COUNT(DISTINCT customer_id) AS customers,
        SUM(sales_quantity) AS units_sold,
        SUM(sales_revenue) AS revenue
    FROM gold.sales
    WHERE transaction_type = 'sale'
    GROUP BY 1
)
SELECT
    sale_month,
    orders,
    customers,
    units_sold,
    ROUND(revenue, 2) AS revenue,
    ROUND(revenue / NULLIF(orders, 0), 2) AS average_order_value,
    ROUND(
        100.0 * (revenue - LAG(revenue) OVER (ORDER BY sale_month))
        / NULLIF(LAG(revenue) OVER (ORDER BY sale_month), 0),
        2
    ) AS revenue_change_pct
FROM monthly
ORDER BY sale_month;

-- 4. Reachat clients : commandes et chiffre d'affaires par client identifie.
WITH customer_sales AS (
    SELECT
        customer_id,
        COUNT(DISTINCT invoice) AS orders,
        SUM(sales_revenue) AS revenue,
        MIN(sale_date) AS first_order_date,
        MAX(sale_date) AS last_order_date
    FROM gold.sales
    WHERE transaction_type = 'sale'
      AND customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT
    CASE WHEN orders = 1 THEN '1 commande' ELSE '2 commandes ou plus' END
        AS customer_segment,
    COUNT(*) AS customers,
    SUM(orders) AS orders,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2)
        AS customer_share_pct,
    ROUND(100.0 * SUM(revenue) / NULLIF(SUM(SUM(revenue)) OVER (), 0), 2)
        AS revenue_share_pct
FROM customer_sales
GROUP BY 1
ORDER BY MIN(orders);

-- 5. Top 10 produits par chiffre d'affaires valide.
SELECT
    stock_code,
    product_description,
    revenue,
    quantity_sold,
    distinct_invoices,
    distinct_customers
FROM gold.product_performance
ORDER BY revenue DESC NULLS LAST
LIMIT 10;

-- 6. Concentration du CA produit : part cumulee des 10 premiers produits.
WITH ranked_products AS (
    SELECT
        stock_code,
        product_description,
        revenue,
        SUM(revenue) OVER (
            ORDER BY revenue DESC, stock_code, product_description
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,
        SUM(revenue) OVER () AS total_revenue,
        ROW_NUMBER() OVER (
            ORDER BY revenue DESC, stock_code, product_description
        ) AS revenue_rank
    FROM gold.product_performance
)
SELECT
    revenue_rank,
    stock_code,
    product_description,
    ROUND(revenue, 2) AS revenue,
    ROUND(100.0 * revenue / NULLIF(total_revenue, 0), 2) AS revenue_share_pct,
    ROUND(100.0 * cumulative_revenue / NULLIF(total_revenue, 0), 2)
        AS cumulative_revenue_share_pct
FROM ranked_products
WHERE revenue_rank <= 10
ORDER BY revenue_rank;

-- 7. Performance par pays (ventes valides seulement).
SELECT
    country,
    COUNT(DISTINCT invoice) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    SUM(sales_quantity) AS units_sold,
    ROUND(SUM(sales_revenue), 2) AS revenue,
    ROUND(
        SUM(sales_revenue) / NULLIF(COUNT(DISTINCT invoice), 0), 2
    ) AS average_order_value
FROM gold.sales
WHERE transaction_type = 'sale'
GROUP BY country
ORDER BY revenue DESC NULLS LAST
LIMIT 15;

-- 8. Activite quotidienne : jours les plus forts en chiffre d'affaires.
SELECT
    sale_date,
    transaction_lines,
    distinct_invoices AS orders,
    distinct_customers AS customers,
    quantity_sold AS units_sold,
    ROUND(revenue, 2) AS revenue
FROM gold.daily_sales
ORDER BY revenue DESC NULLS LAST
LIMIT 10;

-- 9. Controle de coherence des agregats journaliers par rapport aux ventes.
SELECT
    'gold.sales' AS source_table,
    COUNT(*) AS transaction_lines,
    SUM(sales_quantity)::bigint AS quantity_sold,
    ROUND(SUM(sales_revenue), 2) AS revenue
FROM gold.sales
WHERE transaction_type = 'sale'

UNION ALL

SELECT
    'gold.daily_sales' AS source_table,
    SUM(transaction_lines)::bigint AS transaction_lines,
    SUM(quantity_sold)::bigint AS quantity_sold,
    ROUND(SUM(revenue), 2) AS revenue
FROM gold.daily_sales;
