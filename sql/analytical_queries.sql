-- ==============================================================================
-- DataPulse AI - Analytical Warehouse SQL Queries
-- Production SQL queries for business intelligence, sales KPIs, growth, and data quality.
-- ==============================================================================

-- 1. Headline Sales KPIs (Total Revenue, Transactions, AOV, Total Units)
SELECT
    COALESCE(SUM(f.net_sales), 0.0) AS total_revenue,
    COUNT(f.fact_id) AS total_transactions,
    ROUND(COALESCE(SUM(f.net_sales), 0.0) / NULLIF(COUNT(f.fact_id), 0), 2) AS average_order_value,
    COALESCE(SUM(f.quantity), 0) AS total_units_sold,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    COUNT(DISTINCT f.product_id) AS unique_products
FROM fact_sales f;

-- 2. Daily Sales Revenue and Order Volume
SELECT
    d.full_date AS sale_date,
    SUM(f.net_sales) AS daily_revenue,
    COUNT(f.fact_id) AS transactions_count,
    SUM(f.quantity) AS units_sold
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.full_date
ORDER BY d.full_date ASC;

-- 3. Monthly Revenue Trajectory
SELECT
    d.year,
    d.month,
    d.month_name,
    SUM(f.net_sales) AS monthly_revenue,
    COUNT(f.fact_id) AS transactions_count
FROM fact_sales f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year ASC, d.month ASC;

-- 4. Revenue Share by Product Category
SELECT
    p.category,
    SUM(f.net_sales) AS category_revenue,
    COUNT(f.fact_id) AS transactions_count,
    SUM(f.quantity) AS units_sold,
    ROUND((SUM(f.net_sales) / (SELECT SUM(net_sales) FROM fact_sales)) * 100, 2) AS revenue_share_pct
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category
ORDER BY category_revenue DESC;

-- 5. Regional Sales Performance & Customer Penetration
SELECT
    c.region,
    SUM(f.net_sales) AS region_revenue,
    COUNT(f.fact_id) AS transactions_count,
    COUNT(DISTINCT f.customer_id) AS unique_customers,
    ROUND((SUM(f.net_sales) / (SELECT SUM(net_sales) FROM fact_sales)) * 100, 2) AS regional_share_pct
FROM fact_sales f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.region
ORDER BY region_revenue DESC;

-- 6. Top 10 Best-Selling Products by Net Revenue
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(f.net_sales) AS total_revenue,
    SUM(f.quantity) AS units_sold,
    COUNT(f.fact_id) AS order_count
FROM fact_sales f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;

-- 7. Month-over-Month (MoM) Revenue Growth Rate (Window Function)
WITH monthly_sales AS (
    SELECT
        d.year,
        d.month,
        d.month_name,
        SUM(f.net_sales) AS current_revenue
    FROM fact_sales f
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.year, d.month, d.month_name
)
SELECT
    year,
    month,
    month_name,
    current_revenue,
    LAG(current_revenue, 1) OVER (ORDER BY year, month) AS prior_month_revenue,
    ROUND(
        ((current_revenue - LAG(current_revenue, 1) OVER (ORDER BY year, month))
         / NULLIF(LAG(current_revenue, 1) OVER (ORDER BY year, month), 0)) * 100,
        2
    ) AS mom_growth_pct
FROM monthly_sales
ORDER BY year ASC, month ASC;

-- 8. Data Quality Health & Violation Breakdown
SELECT
    rule_violated,
    COUNT(issue_id) AS quarantined_count,
    ROUND(
        (COUNT(issue_id)::NUMERIC / NULLIF((SELECT COUNT(*) FROM data_quality_issues), 0)) * 100,
        2
    ) AS share_of_violations_pct
FROM data_quality_issues
GROUP BY rule_violated
ORDER BY quarantined_count DESC;
