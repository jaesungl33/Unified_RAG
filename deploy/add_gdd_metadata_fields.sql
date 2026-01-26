-- Add GDD Metadata Fields to keyword_documents Table
-- This migration adds version, author, and date fields to store extracted GDD metadata
-- Run this in your Supabase SQL Editor

-- Add version field (e.g., "v1.5", "1.1", "1.2.0")
ALTER TABLE keyword_documents
ADD COLUMN IF NOT EXISTS gdd_version TEXT;

-- Add author field (e.g., "phucth12", "QuocTA", "Kent")
ALTER TABLE keyword_documents
ADD COLUMN IF NOT EXISTS gdd_author TEXT;

-- Add date field (e.g., "28 - 07 - 2025", "22/09/2025")
ALTER TABLE keyword_documents
ADD COLUMN IF NOT EXISTS gdd_date TEXT;

-- Add comments to document the fields
COMMENT ON COLUMN keyword_documents.gdd_version IS 'GDD document version extracted from first chunks (e.g., "v1.5", "1.1")';
COMMENT ON COLUMN keyword_documents.gdd_author IS 'GDD document author/creator extracted from first chunks (e.g., "phucth12", "QuocTA")';
COMMENT ON COLUMN keyword_documents.gdd_date IS 'GDD document creation/update date extracted from first chunks (e.g., "28 - 07 - 2025")';

-- Note: All fields are nullable (NULL) to handle cases where metadata is not found
-- This is expected behavior when:
-- 1. Document doesn't have metadata in the first chunks
-- 2. Metadata format doesn't match expected patterns
-- 3. Document is not a GDD document
