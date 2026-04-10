-- ============================================================
-- Restaurant Reservation System
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ── Drop everything cleanly ───────────────────────────────────
DROP TABLE IF EXISTS reviews          CASCADE;
DROP TABLE IF EXISTS reservations     CASCADE;
DROP TABLE IF EXISTS tables           CASCADE;
DROP TABLE IF EXISTS restaurants      CASCADE;
DROP TABLE IF EXISTS customers        CASCADE;

-- ── Table 1: customers ────────────────────────────────────────
-- Independent table — no foreign keys
CREATE TABLE customers (
    customer_id SERIAL       PRIMARY KEY,
    full_name   VARCHAR(200) NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    phone       VARCHAR(30),
    created_at  TIMESTAMPTZ  DEFAULT NOW()
);

-- ── Table 2: restaurants ──────────────────────────────────────
-- Stores structured data (name, city, cuisine) AND unstructured
-- data (hours, menu) using a JSONB column.
-- The location column uses PostGIS GEOGRAPHY for GiST indexing.
CREATE TABLE restaurants (
    restaurant_id SERIAL       PRIMARY KEY,
    name          VARCHAR(300) NOT NULL,
    city          VARCHAR(100) NOT NULL,
    address       TEXT         NOT NULL,
    cuisine_type  VARCHAR(100),
    phone         VARCHAR(30),
    -- GEOGRAPHY stores lat/lon as a geographic point on a sphere
    -- Enables distance calculations and GiST spatial indexing
    location      GEOGRAPHY(POINT, 4326),
    -- JSONB stores operating hours and menu as flexible JSON
    -- No fixed schema — each restaurant can have different structures
    operating_hours JSONB,
    menu            JSONB,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Table 3: tables ──────────────────────────────────────────
-- Physical tables inside a restaurant.
-- A restaurant has many tables (one-to-many).
CREATE TABLE tables (
    table_id      SERIAL  PRIMARY KEY,
    restaurant_id INT     NOT NULL REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    table_number  INT     NOT NULL,                -- e.g. Table 5
    capacity      INT     NOT NULL CHECK (capacity > 0),  -- max seats
    is_active     BOOLEAN DEFAULT TRUE,            -- can be marked inactive for maintenance
    UNIQUE (restaurant_id, table_number)           -- no two tables with same number in a restaurant
);

-- ── Table 4: reservations ─────────────────────────────────────
-- The core junction — links customers to tables at specific times.
-- Each reservation occupies a table for a time slot.
CREATE TABLE reservations (
    reservation_id SERIAL      PRIMARY KEY,
    customer_id    INT         NOT NULL REFERENCES customers(customer_id),
    table_id       INT         NOT NULL REFERENCES tables(table_id),
    restaurant_id  INT         NOT NULL REFERENCES restaurants(restaurant_id),
    party_size     INT         NOT NULL CHECK (party_size > 0),
    -- Time slot: start time and end time define the reservation window
    starts_at      TIMESTAMPTZ NOT NULL,
    ends_at        TIMESTAMPTZ NOT NULL CHECK (ends_at > starts_at),
    status         VARCHAR(20) DEFAULT 'confirmed'
                               CHECK (status IN ('confirmed','cancelled','completed','no_show')),
    special_requests TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    -- A table cannot have two overlapping reservations
    -- Enforced by the booking transaction + index; EXCLUDE also works with btree_gist
    CONSTRAINT no_double_booking UNIQUE (table_id, starts_at)
);

-- ── Table 5: reviews ─────────────────────────────────────────
-- Structured rating data (stars, dates) lives here in PostgreSQL.
-- Long-form unstructured text reviews live in MongoDB.
-- The mongo_id column links the two records together.
CREATE TABLE reviews (
    review_id     SERIAL      PRIMARY KEY,
    customer_id   INT         NOT NULL REFERENCES customers(customer_id),
    restaurant_id INT         NOT NULL REFERENCES restaurants(restaurant_id),
    reservation_id INT        REFERENCES reservations(reservation_id),
    rating        NUMERIC(2,1) NOT NULL CHECK (rating BETWEEN 1.0 AND 5.0),
    -- mongo_id links to the full text review stored in MongoDB
    mongo_id      VARCHAR(24),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    -- A customer can only review a restaurant once per reservation
    UNIQUE (customer_id, reservation_id)
);


-- ============================================================
-- PERFORMANCE INDEXES
-- ============================================================

-- Speed up: "find all reservations for a customer"
CREATE INDEX idx_reservations_customer ON reservations(customer_id);

-- Speed up: "find all reservations for a table" (availability check)
CREATE INDEX idx_reservations_table ON reservations(table_id);

-- Speed up: "find all reservations in a time window" (key for availability)
CREATE INDEX idx_reservations_starts_at ON reservations(starts_at);

-- Speed up: "find tables in a restaurant"
CREATE INDEX idx_tables_restaurant ON tables(restaurant_id);

-- Speed up: "find tables by capacity" (party size filter)
CREATE INDEX idx_tables_capacity ON tables(capacity);

-- Speed up: "find restaurants by city" (city-based ranking query)
CREATE INDEX idx_restaurants_city ON restaurants(city);

-- Speed up: "find average ratings per restaurant"
CREATE INDEX idx_reviews_restaurant ON reviews(restaurant_id);

-- GiST index for location-based distance queries
-- Allows fast: "find restaurants within X km of a point"
CREATE INDEX idx_restaurants_location ON restaurants USING GIST(location);

-- GIN index for JSONB queries on operating hours / menu
CREATE INDEX idx_restaurants_jsonb ON restaurants USING GIN(operating_hours);


-- ============================================================
-- SAMPLE DATA
-- ============================================================

-- Customers
INSERT INTO customers (full_name, email, phone) VALUES
    ('Alice Uwimana',    'alice@example.com',   '+250788100001'),
    ('Bob Habimana',     'bob@example.com',     '+250788100002'),
    ('Claire Mukamana',  'claire@example.com',  '+250788100003'),
    ('David Nkurunziza', 'david@example.com',   '+250788100004'),
    ('Eve Ingabire',     'eve@example.com',     '+250788100005');

-- Restaurants (with location using PostGIS ST_MakePoint, and JSONB hours/menu)
INSERT INTO restaurants (name, city, address, cuisine_type, phone, location, operating_hours, menu)
VALUES
(
    'Repub Lounge',
    'Kigali',
    'KG 9 Ave, Kiyovu',
    'International',
    '+250252501234',
    ST_MakePoint(30.0619, -1.9441)::GEOGRAPHY,
    '{
        "monday":    {"open": "11:00", "close": "23:00"},
        "tuesday":   {"open": "11:00", "close": "23:00"},
        "wednesday": {"open": "11:00", "close": "23:00"},
        "thursday":  {"open": "11:00", "close": "23:00"},
        "friday":    {"open": "11:00", "close": "00:00"},
        "saturday":  {"open": "12:00", "close": "00:00"},
        "sunday":    {"open": "12:00", "close": "22:00"}
    }'::JSONB,
    '{
        "starters": [
            {"name": "Spring Rolls",  "price": 4500},
            {"name": "Beef Brochette","price": 5000}
        ],
        "mains": [
            {"name": "Grilled Tilapia",  "price": 9500},
            {"name": "Pasta Carbonara",  "price": 8000},
            {"name": "Brochette Platter","price": 11000}
        ],
        "drinks": [
            {"name": "Fresh Juice", "price": 2500},
            {"name": "Primus Beer", "price": 1800}
        ]
    }'::JSONB
),
(
    'Heaven Restaurant',
    'Kigali',
    'KN 29 St, Kacyiru',
    'African Fusion',
    '+250788200001',
    ST_MakePoint(30.0756, -1.9358)::GEOGRAPHY,
    '{
        "monday":    {"open": "12:00", "close": "22:30"},
        "tuesday":   {"open": "12:00", "close": "22:30"},
        "wednesday": {"open": "12:00", "close": "22:30"},
        "thursday":  {"open": "12:00", "close": "22:30"},
        "friday":    {"open": "12:00", "close": "23:30"},
        "saturday":  {"open": "12:00", "close": "23:30"},
        "sunday":    {"closed": true}
    }'::JSONB,
    '{
        "starters": [
            {"name": "Sambaza Fish",    "price": 6000},
            {"name": "Avocado Salad",   "price": 3500}
        ],
        "mains": [
            {"name": "Ugali & Stew",    "price": 7500},
            {"name": "Whole Tilapia",   "price": 12000},
            {"name": "Mixed Grill",     "price": 15000}
        ]
    }'::JSONB
),
(
    'Kigali Marriott Cafe',
    'Kigali',
    'KN 3 Ave, Nyarugenge',
    'Continental',
    '+250788300001',
    ST_MakePoint(30.0590, -1.9500)::GEOGRAPHY,
    '{
        "monday":    {"open": "06:30", "close": "23:00"},
        "tuesday":   {"open": "06:30", "close": "23:00"},
        "wednesday": {"open": "06:30", "close": "23:00"},
        "thursday":  {"open": "06:30", "close": "23:00"},
        "friday":    {"open": "06:30", "close": "23:00"},
        "saturday":  {"open": "07:00", "close": "23:00"},
        "sunday":    {"open": "07:00", "close": "22:00"}
    }'::JSONB,
    NULL  -- menu managed separately
),
(
    'Meze Fresh',
    'Nairobi',
    'Westlands, Nairobi',
    'Mediterranean',
    '+254700123456',
    ST_MakePoint(36.8219, -1.2921)::GEOGRAPHY,
    '{
        "monday":    {"open": "10:00", "close": "22:00"},
        "friday":    {"open": "10:00", "close": "23:00"},
        "saturday":  {"open": "10:00", "close": "23:00"},
        "sunday":    {"open": "10:00", "close": "21:00"}
    }'::JSONB,
    NULL
);

-- Tables for Restaurant 1 (Repub Lounge)
INSERT INTO tables (restaurant_id, table_number, capacity) VALUES
    (1, 1, 2), (1, 2, 2), (1, 3, 4), (1, 4, 4),
    (1, 5, 6), (1, 6, 6), (1, 7, 8), (1, 8, 10);

-- Tables for Restaurant 2 (Heaven)
INSERT INTO tables (restaurant_id, table_number, capacity) VALUES
    (2, 1, 2), (2, 2, 4), (2, 3, 4), (2, 4, 6), (2, 5, 8);

-- Tables for Restaurant 3 (Marriott)
INSERT INTO tables (restaurant_id, table_number, capacity) VALUES
    (3, 1, 2), (3, 2, 2), (3, 3, 4), (3, 4, 6), (3, 5, 10);

-- Tables for Restaurant 4 (Nairobi)
INSERT INTO tables (restaurant_id, table_number, capacity) VALUES
    (4, 1, 2), (4, 2, 4), (4, 3, 4), (4, 4, 8);

-- Reservations (some past, some upcoming)
INSERT INTO reservations (customer_id, table_id, restaurant_id, party_size, starts_at, ends_at, status) VALUES
    (1, 3, 1, 4, NOW() - INTERVAL '7 days', NOW() - INTERVAL '7 days' + INTERVAL '2 hours', 'completed'),
    (2, 4, 1, 3, NOW() - INTERVAL '5 days', NOW() - INTERVAL '5 days' + INTERVAL '2 hours', 'completed'),
    (3, 7, 1, 5, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days' + INTERVAL '2 hours', 'completed'),
    (4, 9, 2, 2, NOW() - INTERVAL '2 days', NOW() - INTERVAL '2 days' + INTERVAL '2 hours', 'completed'),
    (5, 10, 2, 4, NOW() - INTERVAL '1 day',  NOW() - INTERVAL '1 day' + INTERVAL '2 hours',  'completed'),
    (1, 3,  1, 3, NOW() + INTERVAL '1 day',  NOW() + INTERVAL '1 day' + INTERVAL '2 hours',  'confirmed'),
    (2, 11, 3, 2, NOW() + INTERVAL '2 days', NOW() + INTERVAL '2 days' + INTERVAL '2 hours', 'confirmed');

-- Reviews (structured rating in PostgreSQL; long text lives in MongoDB)
INSERT INTO reviews (customer_id, restaurant_id, reservation_id, rating, mongo_id) VALUES
    (1, 1, 1, 4.5, NULL),   -- Alice reviewed Repub Lounge
    (2, 1, 2, 4.0, NULL),   -- Bob reviewed Repub Lounge
    (3, 1, 3, 5.0, NULL),   -- Claire reviewed Repub Lounge
    (4, 2, 4, 3.5, NULL),   -- David reviewed Heaven
    (5, 2, 5, 4.0, NULL);   -- Eve reviewed Heaven
