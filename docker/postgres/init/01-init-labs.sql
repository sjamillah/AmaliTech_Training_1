-- Create users for LAB 3 and LAB 4.
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lab3_user') THEN
      CREATE ROLE lab3_user LOGIN PASSWORD 'lab3pass';
   END IF;

   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'lab4_user') THEN
      CREATE ROLE lab4_user LOGIN PASSWORD 'lab4pass';
   END IF;
END
$$;

-- Create databases for each lab.
CREATE DATABASE learning_platform OWNER lab3_user;
CREATE DATABASE restaurant_reservation_system OWNER lab4_user;

-- Ensure privileges are set.
GRANT ALL PRIVILEGES ON DATABASE learning_platform TO lab3_user;
GRANT ALL PRIVILEGES ON DATABASE restaurant_reservation_system TO lab4_user;

\connect restaurant_reservation_system
CREATE EXTENSION IF NOT EXISTS postgis;
