-- ============================================================================
-- Script 2: GDD RAG Schema Upgrade (v2) - Section-First Chunking
-- ============================================================================
-- This migration adds columns for section-aware chunking and hybrid retrieval
-- Run this AFTER the base schema is created
-- All changes are backward compatible (existing data remains valid)

-- Add new columns to gdd_chunks for section-aware retrieval
ALTER TABLE gdd_chunks 
ADD COLUMN IF NOT EXISTS section_path TEXT,
ADD COLUMN IF NOT EXISTS section_title TEXT,
ADD COLUMN IF NOT EXISTS subsection_title TEXT,
ADD COLUMN IF NOT EXISTS section_index INTEGER,
ADD COLUMN IF NOT EXISTS paragraph_index INTEGER,
ADD COLUMN IF NOT EXISTS content_type TEXT,
ADD COLUMN IF NOT EXISTS doc_category TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[];

-- Create indexes for hybrid filtering
CREATE INDEX IF NOT EXISTS gdd_chunks_section_path_idx ON gdd_chunks(section_path);
CREATE INDEX IF NOT EXISTS gdd_chunks_content_type_idx ON gdd_chunks(content_type);
CREATE INDEX IF NOT EXISTS gdd_chunks_doc_category_idx ON gdd_chunks(doc_category);
CREATE INDEX IF NOT EXISTS gdd_chunks_tags_idx ON gdd_chunks USING GIN(tags);

-- Composite index for common section-based queries
CREATE INDEX IF NOT EXISTS gdd_chunks_doc_section_idx ON gdd_chunks(doc_id, section_path);

-- Update match_gdd_chunks function to support section filtering
CREATE OR REPLACE FUNCTION match_gdd_chunks(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    doc_id_filter TEXT DEFAULT NULL,
    section_path_filter TEXT DEFAULT NULL,
    content_type_filter TEXT DEFAULT NULL,
    doc_category_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id TEXT,
    doc_id TEXT,
    content TEXT,
    similarity float,
    metadata JSONB,
    section_path TEXT,
    section_title TEXT,
    content_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        gc.chunk_id,
        gc.doc_id,
        gc.content,
        1 - (gc.embedding <=> query_embedding) as similarity,
        gc.metadata,
        gc.section_path,
        gc.section_title,
        gc.content_type
    FROM gdd_chunks gc
    WHERE 
        gc.embedding IS NOT NULL
        AND (doc_id_filter IS NULL OR gc.doc_id = doc_id_filter)
        AND (section_path_filter IS NULL OR gc.section_path ILIKE '%' || section_path_filter || '%')
        AND (content_type_filter IS NULL OR gc.content_type = content_type_filter)
        AND (doc_category_filter IS NULL OR gc.doc_category = doc_category_filter)
        AND (1 - (gc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY gc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Add doc_category to gdd_documents for document-level categorization
ALTER TABLE gdd_documents
ADD COLUMN IF NOT EXISTS doc_category TEXT;

CREATE INDEX IF NOT EXISTS gdd_documents_category_idx ON gdd_documents(doc_category);

-- Comments for documentation
COMMENT ON COLUMN gdd_chunks.section_path IS 'Hierarchical section path (e.g., "5. Interface / 5.2 Result Screen / Reward Panel")';
COMMENT ON COLUMN gdd_chunks.section_title IS 'Main section title (e.g., "5. Interface")';
COMMENT ON COLUMN gdd_chunks.subsection_title IS 'Subsection title if applicable (e.g., "5.2 Result Screen")';
COMMENT ON COLUMN gdd_chunks.section_index IS 'Numeric index of section within document';
COMMENT ON COLUMN gdd_chunks.paragraph_index IS 'Numeric index of paragraph within section';
COMMENT ON COLUMN gdd_chunks.content_type IS 'Type of content: ui, logic, flow, table, monetization, etc.';
COMMENT ON COLUMN gdd_chunks.doc_category IS 'Document category for filtering (e.g., "UI Design", "Character System")';
COMMENT ON COLUMN gdd_chunks.tags IS 'Array of tags for flexible filtering';
