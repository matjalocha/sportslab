-- SportsLab Postgres init
-- Creates extensions needed for the database.
-- Runs automatically on first container start (empty data volume).

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- Timescale dodany później (A-09 migracja SQLite -> Postgres)

-- Dev seed (optional) -- comment out for production
-- \i /docker-entrypoint-initdb.d/seed.sql
