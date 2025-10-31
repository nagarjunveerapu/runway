-- Runway Finance PostgreSQL Database Setup
-- Run this script as a PostgreSQL superuser to create the database and user

-- Create database
CREATE DATABASE runway_finance;

-- Create user with password (change password in production!)
CREATE USER runway_user WITH PASSWORD 'runway_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE runway_finance TO runway_user;

-- Connect to the new database and grant schema privileges
\c runway_finance
GRANT ALL ON SCHEMA public TO runway_user;

-- Enable extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Output completion message
\echo 'PostgreSQL database setup complete!'
\echo 'Database: runway_finance'
\echo 'User: runway_user'
\echo ''
\echo 'Connection string:'
\echo 'postgresql://runway_user:runway_password@localhost:5432/runway_finance'
\echo ''
\echo 'Remember to update DATABASE_URL in your .env file!'

