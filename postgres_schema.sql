-- ====================================================================
-- PostgreSQL Database Schema for Premium Internship Discovery Platform
-- Target: Supabase / Neon / Local PostgreSQL 15+
-- ====================================================================

-- 1. Enable any required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Drop existing tables if they exist (for clean migrations)
DROP TABLE IF EXISTS internships CASCADE;
DROP TABLE IF EXISTS internship_rejections CASCADE;
DROP TABLE IF EXISTS source_health CASCADE;

-- 3. Create 'internships' table
CREATE TABLE internships (
    id BIGSERIAL PRIMARY KEY,
    apply_link VARCHAR(500) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    stipend VARCHAR(100),
    paid BOOLEAN DEFAULT FALSE NOT NULL,
    location VARCHAR(255),
    remote BOOLEAN DEFAULT FALSE NOT NULL,
    duration VARCHAR(100),
    skills VARCHAR(500), -- Comma-separated skills
    source VARCHAR(100) NOT NULL,
    legitimacy_score INTEGER DEFAULT 50 NOT NULL,
    confidence_score INTEGER DEFAULT 50 NOT NULL,
    stipend_numeric INTEGER DEFAULT 0 NOT NULL,
    posted_at TIMESTAMP,
    freshness_score INTEGER DEFAULT 0 NOT NULL,
    confidence VARCHAR(50) DEFAULT 'HIGH' NOT NULL,
    confidence_tier VARCHAR(50) DEFAULT 'HIGH_CONFIDENCE' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    inactive_reason VARCHAR(255),
    last_seen TIMESTAMP DEFAULT NOW() NOT NULL,
    deactivated_at TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0 NOT NULL,
    description VARCHAR(5000),
    relevance_score INTEGER DEFAULT 0 NOT NULL,
    relevance_tier VARCHAR(50) DEFAULT 'IRRELEVANT' NOT NULL,
    role_category VARCHAR(50) DEFAULT 'Other' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- 4. Create composite and column-level indexes for internships
-- Optimizes GET /api/internships queries sorted by posted_at, created_at, or stipend_numeric
CREATE INDEX ix_internships_active_category_posted ON internships (is_active, role_category, posted_at DESC);
CREATE INDEX ix_internships_active_category_created ON internships (is_active, role_category, created_at DESC);
CREATE INDEX ix_internships_active_category_stipend ON internships (is_active, role_category, stipend_numeric DESC);
CREATE INDEX ix_internships_active_company ON internships (is_active, company_name);
CREATE INDEX ix_internships_active_source ON internships (is_active, source);

-- Individual index columns for filtering
CREATE INDEX ix_internships_posted_at ON internships (posted_at);
CREATE INDEX ix_internships_created_at ON internships (created_at);
CREATE INDEX ix_internships_stipend_numeric ON internships (stipend_numeric);
CREATE INDEX ix_internships_legitimacy_score ON internships (legitimacy_score);
CREATE INDEX ix_internships_relevance_score ON internships (relevance_score);
CREATE INDEX ix_internships_source ON internships (source);

-- 5. Create GIN index for PostgreSQL Full-Text Search (FTS)
-- Combines company_name, role, skills, and description for rapid text searches
CREATE INDEX ix_internships_fts ON internships USING gin (
    to_tsvector('english', 
        coalesce(company_name, '') || ' ' || 
        coalesce(role, '') || ' ' || 
        coalesce(skills, '') || ' ' || 
        coalesce(description, '')
    )
);

-- 6. Create 'internship_rejections' table
CREATE TABLE internship_rejections (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    source VARCHAR(100) NOT NULL,
    reasons VARCHAR(500) NOT NULL, -- Comma-separated reasons
    relevance_score INTEGER DEFAULT 0 NOT NULL,
    legitimacy_score INTEGER DEFAULT 0 NOT NULL,
    confidence_score INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX ix_internship_rejections_created_at ON internship_rejections (created_at);
CREATE INDEX ix_internship_rejections_source ON internship_rejections (source);

-- 7. Create 'source_health' table
CREATE TABLE source_health (
    source VARCHAR(100) PRIMARY KEY,
    last_successful_scrape TIMESTAMP,
    last_failure TIMESTAMP,
    health_status VARCHAR(50) DEFAULT 'UNKNOWN' NOT NULL,
    last_jobs_found INTEGER DEFAULT 0 NOT NULL,
    last_jobs_saved INTEGER DEFAULT 0 NOT NULL,
    success_count INTEGER DEFAULT 0 NOT NULL,
    failure_count INTEGER DEFAULT 0 NOT NULL
);
