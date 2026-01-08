-- Populate component_type and reference_role fields in dictionary tables
-- Run this in Supabase SQL Editor
--
-- This migration:
-- 0. Creates dictionary tables if they don't exist
-- 1. Adds component_type column to dictionary_components (if not exists)
-- 2. Adds reference_role column to dictionary_references (if not exists)
-- 3. Sets default component_type = 'COMPONENT' for existing components
-- 4. Sets default reference_role = 'CORE' for existing references
-- 5. Adds CHECK constraints and default values
--
-- NOTE: If tables don't exist, they will be created with basic schema.
-- For full schema with all indexes, see: deploy/dictionary_schema.sql

-- ============================================================================
-- Step 0: Create tables if they don't exist
-- ============================================================================

-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create dictionary_components table if it doesn't exist
CREATE TABLE IF NOT EXISTS dictionary_components (
    component_key TEXT PRIMARY KEY,
    display_name_vi TEXT NOT NULL,
    aliases_vi TEXT[] DEFAULT '{}',
    embedding vector(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create dictionary_references table if it doesn't exist
CREATE TABLE IF NOT EXISTS dictionary_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_key TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    evidence_text_vi TEXT,
    source_language TEXT DEFAULT 'vi',
    confidence_score FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'dictionary_references_component_key_fkey'
    ) THEN
        ALTER TABLE dictionary_references
        ADD CONSTRAINT dictionary_references_component_key_fkey
        FOREIGN KEY (component_key) REFERENCES dictionary_components(component_key) ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- Step 1: Add columns if they don't exist
-- ============================================================================

-- Add component_type column to dictionary_components
ALTER TABLE dictionary_components
ADD COLUMN IF NOT EXISTS component_type TEXT;

-- Add reference_role column to dictionary_references
ALTER TABLE dictionary_references
ADD COLUMN IF NOT EXISTS reference_role TEXT;

-- ============================================================================
-- Step 2: Populate component_type in dictionary_components
-- ============================================================================

-- Set default to 'COMPONENT' for all existing rows where component_type is NULL
UPDATE dictionary_components
SET component_type = 'COMPONENT'
WHERE component_type IS NULL;

-- Verify: Check counts
-- SELECT component_type, COUNT(*) FROM dictionary_components GROUP BY component_type;

-- ============================================================================
-- Step 3: Populate reference_role in dictionary_references
-- ============================================================================

-- Set default to 'CORE' for all existing rows where reference_role is NULL
UPDATE dictionary_references
SET reference_role = 'CORE'
WHERE reference_role IS NULL;

-- Verify: Check counts
-- SELECT reference_role, COUNT(*) FROM dictionary_references GROUP BY reference_role;

-- ============================================================================
-- Step 4: Add CHECK constraints and default values
-- ============================================================================

-- Add CHECK constraint for component_type (drop existing if any, then add)
DO $$
BEGIN
    -- Drop existing constraint if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'dictionary_components_component_type_check'
    ) THEN
        ALTER TABLE dictionary_components 
        DROP CONSTRAINT dictionary_components_component_type_check;
    END IF;
END $$;

ALTER TABLE dictionary_components
ADD CONSTRAINT dictionary_components_component_type_check 
CHECK (component_type IN ('COMPONENT', 'GLOBAL_UI'));

-- Add CHECK constraint for reference_role (drop existing if any, then add)
DO $$
BEGIN
    -- Drop existing constraint if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'dictionary_references_reference_role_check'
    ) THEN
        ALTER TABLE dictionary_references 
        DROP CONSTRAINT dictionary_references_reference_role_check;
    END IF;
END $$;

ALTER TABLE dictionary_references
ADD CONSTRAINT dictionary_references_reference_role_check 
CHECK (reference_role IN ('CORE', 'UI', 'GLOBAL_UI', 'META'));

-- Set default value for component_type
ALTER TABLE dictionary_components
ALTER COLUMN component_type SET DEFAULT 'COMPONENT';

-- Set NOT NULL constraint for component_type (after populating)
ALTER TABLE dictionary_components
ALTER COLUMN component_type SET NOT NULL;

-- Set default value for reference_role
ALTER TABLE dictionary_references
ALTER COLUMN reference_role SET DEFAULT 'CORE';

-- Set NOT NULL constraint for reference_role (after populating)
ALTER TABLE dictionary_references
ALTER COLUMN reference_role SET NOT NULL;

-- ============================================================================
-- Verification Queries (run these to verify the migration)
-- ============================================================================

-- Check component_type distribution
-- SELECT 
--     component_type,
--     COUNT(*) as count,
--     ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
-- FROM dictionary_components
-- GROUP BY component_type
-- ORDER BY count DESC;

-- Check reference_role distribution
-- SELECT 
--     reference_role,
--     COUNT(*) as count,
--     ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
-- FROM dictionary_references
-- GROUP BY reference_role
-- ORDER BY count DESC;

-- Check for any remaining NULL values (should return 0 rows)
-- SELECT 'dictionary_components' as table_name, COUNT(*) as null_count
-- FROM dictionary_components WHERE component_type IS NULL
-- UNION ALL
-- SELECT 'dictionary_references', COUNT(*)
-- FROM dictionary_references WHERE reference_role IS NULL;

COMMENT ON COLUMN dictionary_components.component_type IS 
    'Type of component: COMPONENT (gameplay entity) or GLOBAL_UI (UI without component anchor)';

COMMENT ON COLUMN dictionary_references.reference_role IS 
    'Role of reference: CORE (defines component), UI (UI attached to component), GLOBAL_UI (UI without component), META (notes/TODOs)';

