-- ============================================================
-- Complex Queries — Restaurant Reservation System
-- ============================================================


-- ============================================================
-- QUERY 1: CTE — Find Available Tables for a Given Time Slot
-- ============================================================
-- This answers: "What tables are available at Restaurant 1
-- for 4 people starting at 7pm tonight for 2 hours?"
--
-- Uses a CTE to cleanly separate logic into readable steps:
--   Step A: Find all tables that have CONFLICTING reservations
--   Step B: Find all tables that are NOT in that conflicting set
-- ============================================================

WITH

-- CTE Part A: Identify tables that are BUSY during the requested slot
-- A table is busy if any confirmed reservation overlaps with our window.
-- Overlap condition: existing.starts_at < our.ends_at
--                AND existing.ends_at   > our.starts_at
busy_tables AS (
    SELECT DISTINCT r.table_id
    FROM reservations r
    WHERE r.restaurant_id = 1              -- target restaurant
      AND r.status = 'confirmed'           -- ignore cancelled/completed
      AND r.starts_at < '2026-04-06 21:00:00+00'::TIMESTAMPTZ  -- our end time
      AND r.ends_at   > '2026-04-06 19:00:00+00'::TIMESTAMPTZ  -- our start time
),

-- CTE Part B: Find tables that are available AND big enough
available_tables AS (
    SELECT
        t.table_id,
        t.table_number,
        t.capacity,
        r.name        AS restaurant_name
    FROM tables t
    JOIN restaurants r ON t.restaurant_id = r.restaurant_id
    -- Exclude busy tables using NOT IN (the CTE above)
    WHERE t.restaurant_id = 1
      AND t.is_active = TRUE
      AND t.capacity >= 4                  -- must fit the party size
      AND t.table_id NOT IN (SELECT table_id FROM busy_tables)
)

-- Final result: show available tables sorted by smallest suitable first
SELECT
    table_id,
    table_number,
    capacity,
    restaurant_name,
    -- Label waste: how many extra seats beyond party size
    capacity - 4  AS extra_seats
FROM available_tables
ORDER BY capacity ASC;  -- prefer smaller tables (less waste)


-- ============================================================
-- QUERY 2: RANK() Window Function
-- Rank restaurants by average rating within each city
-- ============================================================
-- For each city, rank restaurants from best to worst by
-- average customer rating. Uses RANK() so ties get the same rank.
--
-- Example: If two restaurants both average 4.5 in Kigali,
-- they both get RANK 1, and the next restaurant gets RANK 3.
-- ============================================================

SELECT
    r.restaurant_id,
    r.name                                          AS restaurant_name,
    r.city,
    r.cuisine_type,
    COUNT(rv.review_id)                             AS review_count,
    ROUND(AVG(rv.rating), 2)                        AS avg_rating,

    -- RANK() window function:
    -- PARTITION BY city: ranking is reset for each city independently
    -- ORDER BY avg_rating DESC: highest rating = rank 1
    -- RANK() (not ROW_NUMBER): ties share the same rank
    RANK() OVER (
        PARTITION BY r.city
        ORDER BY AVG(rv.rating) DESC
    )                                               AS city_rank

FROM restaurants r
-- LEFT JOIN: include restaurants with zero reviews (AVG will be NULL)
LEFT JOIN reviews rv ON r.restaurant_id = rv.restaurant_id

GROUP BY r.restaurant_id, r.name, r.city, r.cuisine_type

-- Only rank restaurants that have at least 1 review
HAVING COUNT(rv.review_id) >= 1

ORDER BY r.city, city_rank;


-- ============================================================
-- QUERY 3: Location-Based Search using PostGIS
-- Find restaurants within X km of a given point
-- ============================================================
-- Uses the GiST index on the location column.
-- ST_DWithin checks if two geography objects are within N metres.
-- ST_Distance returns the actual distance in metres.
-- ============================================================

SELECT
    restaurant_id,
    name,
    city,
    cuisine_type,
    ROUND(
        ST_Distance(
            location,
            ST_MakePoint(30.0619, -1.9441)::GEOGRAPHY  -- reference point (Kigali city centre)
        ) / 1000.0,
        2
    )                                               AS distance_km

FROM restaurants

-- ST_DWithin uses the GiST index for fast spatial filtering
-- 5000 = 5 km radius (in metres, because column is GEOGRAPHY)
WHERE ST_DWithin(
    location,
    ST_MakePoint(30.0619, -1.9441)::GEOGRAPHY,
    5000
)

ORDER BY distance_km ASC;


-- ============================================================
-- QUERY 4: JSONB Query — Get Opening Hours for Today
-- ============================================================
-- Extract structured data from the JSONB operating_hours column.
-- ->> extracts the value as text; -> extracts it as JSONB.
-- ============================================================

SELECT
    name,
    city,
    -- Extract today's hours using the lowercase day name as a key
    operating_hours -> LOWER(TO_CHAR(NOW(), 'Day'))    AS today_hours_json,
    operating_hours ->> 'friday'                        AS friday_hours_text,

    -- Check if the restaurant is open on Sundays
    CASE
        WHEN (operating_hours -> 'sunday') ? 'closed' THEN 'Closed Sundays'
        WHEN operating_hours -> 'sunday' IS NOT NULL   THEN 'Open Sundays'
        ELSE 'Hours not listed'
    END                                               AS sunday_status

FROM restaurants
ORDER BY name;


-- ============================================================
-- QUERY 5: EXPLAIN ANALYZE on the Availability Query
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
WITH busy_tables AS (
    SELECT DISTINCT r.table_id
    FROM reservations r
    WHERE r.restaurant_id = 1
      AND r.status = 'confirmed'
      AND r.starts_at < '2026-04-06 21:00:00+00'::TIMESTAMPTZ
      AND r.ends_at   > '2026-04-06 19:00:00+00'::TIMESTAMPTZ
)
SELECT t.table_id, t.table_number, t.capacity
FROM tables t
WHERE t.restaurant_id = 1
  AND t.is_active = TRUE
  AND t.capacity >= 4
  AND t.table_id NOT IN (SELECT table_id FROM busy_tables)
ORDER BY t.capacity ASC;


-- ============================================================
-- QUERY 6: Reservation History with Running Total (WINDOW)
-- ============================================================
-- For each customer, show their reservation history and a
-- running count of how many reservations they've made so far.
-- Uses ROW_NUMBER() and COUNT() as window functions.
-- ============================================================

SELECT
    c.full_name,
    r.name                                         AS restaurant_name,
    res.starts_at,
    res.party_size,
    res.status,

    -- Running count of this customer's reservations up to this point
    COUNT(*) OVER (
        PARTITION BY res.customer_id
        ORDER BY res.starts_at
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                              AS reservation_number,

    -- Rank among all customers by number of reservations
    RANK() OVER (
        ORDER BY COUNT(res2.reservation_id) DESC
    )                                              AS loyalty_rank

FROM reservations res
JOIN customers c   ON res.customer_id   = c.customer_id
JOIN restaurants r ON res.restaurant_id = r.restaurant_id
JOIN reservations res2 ON res2.customer_id = res.customer_id
GROUP BY c.full_name, r.name, res.reservation_id, res.starts_at,
         res.party_size, res.status, res.customer_id
ORDER BY c.full_name, res.starts_at;


-- ============================================================
-- QUERY 7: Menu Price Analysis using JSONB Functions
-- ============================================================
-- Use jsonb_array_elements() to expand the menu JSON array
-- and compute statistics like average price per category.
-- ============================================================

SELECT
    r.name                                        AS restaurant_name,
    menu_category.key                             AS category,
    COUNT(item.value)                             AS item_count,
    ROUND(AVG((item.value->>'price')::NUMERIC), 0) AS avg_price_rwf,
    MIN((item.value->>'price')::NUMERIC)          AS min_price,
    MAX((item.value->>'price')::NUMERIC)          AS max_price

FROM restaurants r,
     -- jsonb_each() turns each top-level key (starters/mains/drinks) into a row
     jsonb_each(r.menu) AS menu_category,
     -- jsonb_array_elements() expands each array into individual item rows
     jsonb_array_elements(menu_category.value) AS item(value)

WHERE r.menu IS NOT NULL

GROUP BY r.name, menu_category.key
ORDER BY r.name, category;
