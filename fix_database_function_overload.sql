-- ============================================================================
-- Fix Database Function Overload Issue
-- ============================================================================
-- This script fixes the PostgREST overload resolution error for match_gdd_chunks
-- 
-- Problem: Your database has two versions of match_gdd_chunks:
--   1. 4 parameters: (query_embedding, match_threshold, match_count, doc_id_filter)
--   2. 7 parameters: (adds section_path_filter, content_type_filter, doc_category_filter)
--
-- Solution: Drop the 7-parameter version and keep the 4-parameter version
-- ============================================================================

-- First, let's see what functions exist
SELECT 
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments,
    p.oid as function_oid
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'match_gdd_chunks'
AND n.nspname = 'public'
ORDER BY p.oid;

-- Drop the 7-parameter version (the one with extra filters)
-- This keeps the simpler 4-parameter version that the code uses
DROP FUNCTION IF EXISTS public.match_gdd_chunks(
    query_embedding vector(1024),
    match_threshold double precision,
    match_count integer,
    doc_id_filter text,
    section_path_filter text,
    content_type_filter text,
    doc_category_filter text
);

-- Verify only one version remains
SELECT 
    p.proname as function_name,
    pg_get_function_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'match_gdd_chunks'
AND n.nspname = 'public';

-- If you need the 7-parameter version later, you can rename it instead:
-- ALTER FUNCTION public.match_gdd_chunks(
--     query_embedding vector(1024),
--     match_threshold double precision,
--     match_count integer,
--     doc_id_filter text,
--     section_path_filter text,
--     content_type_filter text,
--     doc_category_filter text
-- ) RENAME TO match_gdd_chunks_filtered;

