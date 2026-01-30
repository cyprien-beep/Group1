sql
USE library_dw;

-- Query 1: Monthly Usage Trends
SELECT 
    d.year,
    d.month_name,
    f.usage_type,
    COUNT(*) as total_transactions
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month_number, d.month_name, f.usage_type
ORDER BY d.year, d.month_number;

-- Query 2: Department Usage Ranking
SELECT 
    s.department,
    COUNT(*) as total_usage,
    RANK() OVER (ORDER BY COUNT(*) DESC) as usage_rank
FROM fact_library_usage f
    JOIN dim_student s ON f.student_key = s.student_key
WHERE s.department != 'Unknown'
GROUP BY s.department
ORDER BY total_usage DESC;

#Query 3: Peak Times for Room Bookings
SELECT 
    d.day_of_week,
    t.time_slot_name,
    COUNT(*) as booking_count,
    AVG(f.booking_duration_hours) as avg_duration_hours
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_time_slot t ON f.time_slot_key = t.time_slot_key
WHERE f.usage_type = 'ROOM_BOOKING'
GROUP BY d.day_of_week, t.time_slot_name
ORDER BY booking_count DESC;

-- Query 4: Top 10 Resources
SELECT 
    r.resource_type,
    r.resource_title,
    COUNT(*) as usage_count
FROM fact_library_usage f
    JOIN dim_resource r ON f.resource_key = r.resource_key
WHERE r.resource_id != 'UNKNOWN'
GROUP BY r.resource_type, r.resource_title
ORDER BY usage_count DESC
LIMIT 10;

-- Query 5: DRILL-DOWN Analysis (Year to Month)
SELECT 
    d.year,
    d.quarter,
    d.month_name,
    COUNT(*) as total_usage
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.quarter, d.month_name, d.month_number
ORDER BY d.year, d.month_number;

SELECT 
    d.year,
    d.quarter,
    COUNT(*) as total_usage,
    f.usage_type,
    COUNT(DISTINCT f.student_key) as unique_students
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2024
GROUP BY d.year, d.quarter, f.usage_type
ORDER BY d.quarter, f.usage_type;

#Drill down to daily: January 2024
SELECT 
    d.full_date,
    d.day_of_week,
    COUNT(*) as total_usage,
    f.usage_type

FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
WHERE d.year = 2024 AND d.month_number = 1
GROUP BY d.full_date, d.day_of_week, f.usage_type
ORDER BY d.full_date, f.usage_type;


-- Query 6: ROLL-UP Analysis (Day → Week → Month → Quarter)
-- Business Question: Aggregate daily room bookings into higher levels
-- Daily bookings
CREATE TEMPORARY TABLE daily_bookings AS
SELECT 
    d.full_date,
    d.week_of_year,
    d.month_number,
    d.quarter,
    COUNT(*) as booking_count
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
WHERE f.usage_type = 'ROOM_BOOKING'
GROUP BY d.full_date, d.week_of_year, d.month_number, d.quarter;

-- Roll up to weekly
SELECT 
    week_of_year,
    SUM(booking_count) as weekly_bookings
FROM daily_bookings
GROUP BY week_of_year
ORDER BY week_of_year;

-- Roll up to monthly
SELECT 
    month_number,
    SUM(booking_count) as monthly_bookings
FROM daily_bookings
GROUP BY month_number
ORDER BY month_number;

-- Roll up to quarterly
SELECT 
    quarter,
    SUM(booking_count) as quarterly_bookings
FROM daily_bookings
GROUP BY quarter
ORDER BY quarter;

-- Query 7: SLICING - Specific Time Period Analysis
-- Business Question: View all data for Q1 2024 only
SELECT 
    d.full_date,
    s.department,
    r.resource_type,
    f.usage_type,
    COUNT(*) as transaction_count
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_student s ON f.student_key = s.student_key
    JOIN dim_resource r ON f.resource_key = r.resource_key
WHERE d.year = 2024 
  AND d.quarter = 1
GROUP BY d.full_date, s.department, r.resource_type, f.usage_type
ORDER BY d.full_date;

-- Query 8: DICING - Multi-dimensional Analysis
-- Business Question: Engineering students' digital downloads in March 2024
SELECT 
    d.full_date,
    s.student_id,
    r.resource_title,
    r.resource_type,
    f.download_count,
    f.reading_duration_minutes
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
    JOIN dim_student s ON f.student_key = s.student_key
    JOIN dim_resource r ON f.resource_key = r.resource_key
WHERE d.year = 2024
  AND d.month_number = 3
  AND s.department = 'Engineering'
  AND f.usage_type = 'DIGITAL_DOWNLOAD'
ORDER BY d.full_date, f.download_count DESC;

-- Query 9: PIVOT Analysis - Cross-tabulation
-- Business Question: Compare resource types across departments in matrix format
SELECT 
    s.department,
    SUM(CASE WHEN r.resource_type = 'Physical Book' THEN 1 ELSE 0 END) as physical_books,
    SUM(CASE WHEN r.resource_type = 'E-book' THEN 1 ELSE 0 END) as ebooks,
    SUM(CASE WHEN r.resource_type = 'Journal' THEN 1 ELSE 0 END) as journals,
    SUM(CASE WHEN r.resource_type = 'Article' THEN 1 ELSE 0 END) as articles,
    COUNT(*) as total_usage
FROM fact_library_usage f
    JOIN dim_student s ON f.student_key = s.student_key
    JOIN dim_resource r ON f.resource_key = r.resource_key
WHERE s.department != 'Unknown'
GROUP BY s.department
ORDER BY total_usage DESC;

-- ============================================================================
-- LEVEL 3: ADVANCED ANALYTICS
-- ============================================================================

-- Query 11: Correlation Analysis
-- Business Question: Do students who borrow more books also download more journals?
WITH student_behavior AS (
    SELECT 
        s.student_id,
        s.department,
        SUM(CASE WHEN f.usage_type = 'BOOK_CHECKOUT' THEN 1 ELSE 0 END) as books_borrowed,
        SUM(CASE WHEN f.usage_type = 'DIGITAL_DOWNLOAD' THEN f.download_count ELSE 0 END) as journals_downloaded
    FROM fact_library_usage f
        JOIN dim_student s ON f.student_key = s.student_key
    GROUP BY s.student_id, s.department
    HAVING books_borrowed > 0 AND journals_downloaded > 0
)
SELECT 
    department,
    COUNT(*) as student_count,
    ROUND(AVG(books_borrowed), 2) as avg_books,
    ROUND(AVG(journals_downloaded), 2) as avg_journals,
    -- Simple correlation indicator
    CASE 
        WHEN AVG(books_borrowed) > 5 AND AVG(journals_downloaded) > 10 THEN 'High Correlation'
        WHEN AVG(books_borrowed) > 3 AND AVG(journals_downloaded) > 5 THEN 'Moderate Correlation'
        ELSE 'Low Correlation'
    END as correlation_level
FROM student_behavior
GROUP BY department
ORDER BY avg_books DESC;

-- Query 12: Trend Analysis with Moving Averages
-- Business Question: Identify usage trends over time
SELECT 
    d.full_date,
    COUNT(*) as daily_usage,
    AVG(COUNT(*)) OVER (
        ORDER BY d.full_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as weekly_moving_avg,
    AVG(COUNT(*)) OVER (
        ORDER BY d.full_date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as monthly_moving_avg
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.full_date
ORDER BY d.full_date;

-- Query 13: Anomaly Detection
-- Business Question: Identify unusual patterns (sudden drops/spikes in usage)
WITH daily_stats AS (
    SELECT 
        d.full_date,
        d.day_of_week,
        COUNT(*) as usage_count,
        AVG(COUNT(*)) OVER () as overall_avg,
        STDDEV(COUNT(*)) OVER () as overall_stddev
    FROM fact_library_usage f
        JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY d.full_date, d.day_of_week
)
SELECT 
    full_date,
    day_of_week,
    usage_count,
    ROUND(overall_avg, 2) as average_usage,
    CASE 
        WHEN usage_count > overall_avg + (2 * overall_stddev) THEN 'SPIKE'
        WHEN usage_count < overall_avg - (2 * overall_stddev) THEN 'DROP'
        ELSE 'NORMAL'
    END as anomaly_status,
    ROUND((usage_count - overall_avg) / overall_stddev, 2) as std_deviations
FROM daily_stats
WHERE usage_count > overall_avg + (2 * overall_stddev)
   OR usage_count < overall_avg - (2 * overall_stddev)
ORDER BY full_date;

-- Query 14: Resource Utilization Efficiency
-- Business Question: Which resources have best usage-to-availability ratio?
SELECT 
    r.resource_type,
    r.resource_category,
    COUNT(DISTINCT r.resource_key) as total_resources,
    COUNT(*) as total_usage,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT r.resource_key), 2) as usage_per_resource,
    RANK() OVER (ORDER BY COUNT(*) * 1.0 / COUNT(DISTINCT r.resource_key) DESC) as efficiency_rank
FROM fact_library_usage f
    JOIN dim_resource r ON f.resource_key = r.resource_key
WHERE r.resource_id != 'UNKNOWN'
GROUP BY r.resource_type, r.resource_category
ORDER BY usage_per_resource DESC;

-- Query 15: Student Engagement Score
-- Business Question: Calculate engagement score based on multiple factors
WITH student_engagement AS (
    SELECT 
        s.student_id,
        s.department,
        s.student_type,
        COUNT(*) as total_interactions,
        COUNT(DISTINCT DATE(d.full_date)) as days_active,
        SUM(CASE WHEN f.usage_type = 'BOOK_CHECKOUT' THEN 2 ELSE 0 END) as book_points,
        SUM(CASE WHEN f.usage_type = 'DIGITAL_DOWNLOAD' THEN f.download_count ELSE 0 END) as digital_points,
        SUM(CASE WHEN f.usage_type = 'ROOM_BOOKING' THEN f.booking_duration_hours ELSE 0 END) as study_hours
    FROM fact_library_usage f
        JOIN dim_student s ON f.student_key = s.student_key
        JOIN dim_date d ON f.date_key = d.date_key
    WHERE s.student_id != 'UNKNOWN'
    GROUP BY s.student_id, s.department, s.student_type
)
SELECT 
    student_id,
    department,
    student_type,
    total_interactions,
    days_active,
    -- Engagement score formula: weighted sum of activities
    (book_points + digital_points + (study_hours * 2)) as engagement_score,
    CASE 
        WHEN (book_points + digital_points + (study_hours * 2)) >= 100 THEN 'Highly Engaged'
        WHEN (book_points + digital_points + (study_hours * 2)) >= 50 THEN 'Moderately Engaged'
        WHEN (book_points + digital_points + (study_hours * 2)) >= 20 THEN 'Lightly Engaged'
        ELSE 'Minimally Engaged'
    END as engagement_level
FROM student_engagement
ORDER BY engagement_score DESC
LIMIT 20;

-- ============================================================================
-- PERFORMANCE COMPARISON QUERIES
-- ============================================================================

-- Query 16: Year-over-Year Comparison
SELECT 
    d.year,
    d.month_name,
    COUNT(*) as current_year_usage,
    LAG(COUNT(*), 12) OVER (ORDER BY d.year, d.month_number) as previous_year_usage,
    ROUND(
        (COUNT(*) - LAG(COUNT(*), 12) OVER (ORDER BY d.year, d.month_number)) * 100.0 / 
        NULLIF(LAG(COUNT(*), 12) OVER (ORDER BY d.year, d.month_number), 0),
        2
    ) as yoy_growth_percentage
FROM fact_library_usage f
    JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month_number, d.month_name
ORDER BY d.year, d.month_number;

-- ============================================================================
-- DASHBOARD KPI QUERIES (Quick Summary Metrics)
-- ============================================================================

-- Query 17: Executive Dashboard KPIs
SELECT 
    'Total Transactions' as metric,
    COUNT(*) as value,
    CONCAT(ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_library_usage), 2), '%') as percentage
FROM fact_library_usage
UNION ALL
SELECT 
    'Active Students',
    COUNT(DISTINCT student_key),
    CONCAT(ROUND(COUNT(DISTINCT student_key) * 100.0 / 
        (SELECT COUNT(*) FROM dim_student WHERE student_id != 'UNKNOWN'), 2), '%')
FROM fact_library_usage
UNION ALL
SELECT 
    'Total Resources Used',
    COUNT(DISTINCT resource_key),
    CONCAT(ROUND(COUNT(DISTINCT resource_key) * 100.0 / 
        (SELECT COUNT(*) FROM dim_resource WHERE resource_id != 'UNKNOWN'), 2), '%')
FROM fact_library_usage
UNION ALL
SELECT 
    'Average Daily Transactions',
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT date_key), 2),
    '-'
FROM fact_library_usage;
