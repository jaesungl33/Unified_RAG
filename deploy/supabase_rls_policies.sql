-- Row Level Security (RLS) Policies for Unified RAG App
-- Run this in Supabase SQL Editor after running supabase_schema.sql

-- ============================================================================
-- Enable RLS on all tables
-- ============================================================================

ALTER TABLE gdd_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE gdd_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_chunks ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Drop existing policies if they exist (for idempotency)
-- ============================================================================

DROP POLICY IF EXISTS "Allow anon SELECT on gdd_documents" ON gdd_documents;
DROP POLICY IF EXISTS "Allow anon SELECT on gdd_chunks" ON gdd_chunks;
DROP POLICY IF EXISTS "Allow anon SELECT on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow anon SELECT on code_chunks" ON code_chunks;

DROP POLICY IF EXISTS "Allow service INSERT on gdd_documents" ON gdd_documents;
DROP POLICY IF EXISTS "Allow service INSERT on gdd_chunks" ON gdd_chunks;
DROP POLICY IF EXISTS "Allow service INSERT on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service INSERT on code_chunks" ON code_chunks;

DROP POLICY IF EXISTS "Allow service UPDATE on gdd_documents" ON gdd_documents;
DROP POLICY IF EXISTS "Allow service UPDATE on gdd_chunks" ON gdd_chunks;
DROP POLICY IF EXISTS "Allow service UPDATE on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service UPDATE on code_chunks" ON code_chunks;

DROP POLICY IF EXISTS "Allow service DELETE on gdd_documents" ON gdd_documents;
DROP POLICY IF EXISTS "Allow service DELETE on gdd_chunks" ON gdd_chunks;
DROP POLICY IF EXISTS "Allow service DELETE on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service DELETE on code_chunks" ON code_chunks;

-- ============================================================================
-- Policies for anon role (read-only access for frontend)
-- ============================================================================

-- GDD Documents: Allow anon to SELECT
CREATE POLICY "Allow anon SELECT on gdd_documents"
ON gdd_documents FOR SELECT
TO anon
USING (true);

-- GDD Chunks: Allow anon to SELECT
CREATE POLICY "Allow anon SELECT on gdd_chunks"
ON gdd_chunks FOR SELECT
TO anon
USING (true);

-- Code Files: Allow anon to SELECT
CREATE POLICY "Allow anon SELECT on code_files"
ON code_files FOR SELECT
TO anon
USING (true);

-- Code Chunks: Allow anon to SELECT
CREATE POLICY "Allow anon SELECT on code_chunks"
ON code_chunks FOR SELECT
TO anon
USING (true);

-- ============================================================================
-- Policies for service_role (full access for migrations and admin operations)
-- ============================================================================

-- GDD Documents: Allow service_role to INSERT
CREATE POLICY "Allow service INSERT on gdd_documents"
ON gdd_documents FOR INSERT
TO service_role
WITH CHECK (true);

-- GDD Documents: Allow service_role to UPDATE
CREATE POLICY "Allow service UPDATE on gdd_documents"
ON gdd_documents FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

-- GDD Documents: Allow service_role to DELETE
CREATE POLICY "Allow service DELETE on gdd_documents"
ON gdd_documents FOR DELETE
TO service_role
USING (true);

-- GDD Chunks: Allow service_role to INSERT
CREATE POLICY "Allow service INSERT on gdd_chunks"
ON gdd_chunks FOR INSERT
TO service_role
WITH CHECK (true);

-- GDD Chunks: Allow service_role to UPDATE
CREATE POLICY "Allow service UPDATE on gdd_chunks"
ON gdd_chunks FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

-- GDD Chunks: Allow service_role to DELETE
CREATE POLICY "Allow service DELETE on gdd_chunks"
ON gdd_chunks FOR DELETE
TO service_role
USING (true);

-- Code Files: Allow service_role to INSERT
CREATE POLICY "Allow service INSERT on code_files"
ON code_files FOR INSERT
TO service_role
WITH CHECK (true);

-- Code Files: Allow service_role to UPDATE
CREATE POLICY "Allow service UPDATE on code_files"
ON code_files FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

-- Code Files: Allow service_role to DELETE
CREATE POLICY "Allow service DELETE on code_files"
ON code_files FOR DELETE
TO service_role
USING (true);

-- Code Chunks: Allow service_role to INSERT
CREATE POLICY "Allow service INSERT on code_chunks"
ON code_chunks FOR INSERT
TO service_role
WITH CHECK (true);

-- Code Chunks: Allow service_role to UPDATE
CREATE POLICY "Allow service UPDATE on code_chunks"
ON code_chunks FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

-- Code Chunks: Allow service_role to DELETE
CREATE POLICY "Allow service DELETE on code_chunks"
ON code_chunks FOR DELETE
TO service_role
USING (true);

