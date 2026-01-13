-- Setup Supabase for Code Files
-- Run this script in your Supabase SQL Editor to set up code file storage

-- ============================================================================
-- Step 1: Enable pgvector extension (if not already enabled)
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Step 2: Create Code Files Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS code_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    normalized_path TEXT NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Step 3: Create Code Chunks Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS code_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL REFERENCES code_files(file_path) ON DELETE CASCADE,
    chunk_type TEXT NOT NULL CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum')),
    class_name TEXT,
    method_name TEXT, -- NULL for class chunks
    source_code TEXT NOT NULL,
    code TEXT, -- For methods: the method code
    embedding vector(1024), -- Qwen text-embedding-v4 has 1024 dimensions
    doc_comment TEXT,
    constructor_declaration TEXT, -- For classes
    method_declarations TEXT, -- For classes
    code_references TEXT, -- Renamed from 'references' (PostgreSQL keyword)
    metadata JSONB, -- Store additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Step 4: Create Indexes for Performance
-- ============================================================================

-- Index for vector similarity search on code chunks
CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx ON code_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for filtering by file_path
CREATE INDEX IF NOT EXISTS code_chunks_file_path_idx ON code_chunks(file_path);

-- Index for filtering by chunk_type
CREATE INDEX IF NOT EXISTS code_chunks_type_idx ON code_chunks(chunk_type);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS code_chunks_file_type_idx ON code_chunks(file_path, chunk_type);

-- Index for code_files lookups
CREATE INDEX IF NOT EXISTS code_files_file_path_idx ON code_files(file_path);
CREATE INDEX IF NOT EXISTS code_files_file_name_idx ON code_files(file_name);

-- ============================================================================
-- Step 5: Create Vector Search Function
-- ============================================================================
CREATE OR REPLACE FUNCTION match_code_chunks(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    file_path_filter TEXT DEFAULT NULL,
    chunk_type_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    file_path TEXT,
    chunk_type TEXT,
    class_name TEXT,
    method_name TEXT,
    source_code TEXT,
    similarity float,
    metadata JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id,
        cc.file_path,
        cc.chunk_type,
        cc.class_name,
        cc.method_name,
        cc.source_code,
        1 - (cc.embedding <=> query_embedding) as similarity,
        cc.metadata
    FROM code_chunks cc
    WHERE 
        cc.embedding IS NOT NULL
        AND (file_path_filter IS NULL OR cc.file_path ILIKE '%' || file_path_filter || '%')
        AND (chunk_type_filter IS NULL OR cc.chunk_type = chunk_type_filter)
        AND (1 - (cc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY cc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- Step 6: Create Helper Functions
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Step 7: Create Triggers
-- ============================================================================

-- Trigger to update updated_at for code_files
CREATE TRIGGER update_code_files_updated_at
BEFORE UPDATE ON code_files
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update updated_at for code_chunks
CREATE TRIGGER update_code_chunks_updated_at
BEFORE UPDATE ON code_chunks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Step 8: Set up Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on code_files
ALTER TABLE code_files ENABLE ROW LEVEL SECURITY;

-- Enable RLS on code_chunks
ALTER TABLE code_chunks ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for idempotency)
DROP POLICY IF EXISTS "Allow anon SELECT on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow anon SELECT on code_chunks" ON code_chunks;
DROP POLICY IF EXISTS "Allow service INSERT on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service INSERT on code_chunks" ON code_chunks;
DROP POLICY IF EXISTS "Allow service UPDATE on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service UPDATE on code_chunks" ON code_chunks;
DROP POLICY IF EXISTS "Allow service DELETE on code_files" ON code_files;
DROP POLICY IF EXISTS "Allow service DELETE on code_chunks" ON code_chunks;

-- Policies for anon role (read-only access for frontend queries)
CREATE POLICY "Allow anon SELECT on code_files"
ON code_files FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon SELECT on code_chunks"
ON code_chunks FOR SELECT
TO anon
USING (true);

-- Policies for service_role (full access for backend operations)
CREATE POLICY "Allow service INSERT on code_files"
ON code_files FOR INSERT
TO service_role
WITH CHECK (true);

CREATE POLICY "Allow service UPDATE on code_files"
ON code_files FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow service DELETE on code_files"
ON code_files FOR DELETE
TO service_role
USING (true);

CREATE POLICY "Allow service INSERT on code_chunks"
ON code_chunks FOR INSERT
TO service_role
WITH CHECK (true);

CREATE POLICY "Allow service UPDATE on code_chunks"
ON code_chunks FOR UPDATE
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Allow service DELETE on code_chunks"
ON code_chunks FOR DELETE
TO service_role
USING (true);

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check if tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('code_files', 'code_chunks');

-- Check if indexes exist
SELECT indexname 
FROM pg_indexes 
WHERE tablename IN ('code_files', 'code_chunks');

-- Check if function exists
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name = 'match_code_chunks';

-- Check if RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('code_files', 'code_chunks');

-- ============================================================================
-- Success Message
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Code files Supabase setup completed successfully!';
    RAISE NOTICE 'Tables created: code_files, code_chunks';
    RAISE NOTICE 'Indexes created for performance';
    RAISE NOTICE 'Vector search function: match_code_chunks';
    RAISE NOTICE 'RLS policies enabled';
END $$;

