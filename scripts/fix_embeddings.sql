-- SQL script to fix embeddings in Supabase
-- Run this in Supabase SQL Editor
-- This converts string embeddings to proper vector format

-- First, let's check what we're working with
SELECT 
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    COUNT(CASE WHEN pg_typeof(embedding)::text = 'vector' THEN 1 END) as chunks_with_vector_type,
    COUNT(CASE WHEN pg_typeof(embedding)::text != 'vector' THEN 1 END) as chunks_with_wrong_type
FROM gdd_chunks;

-- Create a function to fix embeddings
CREATE OR REPLACE FUNCTION fix_embeddings()
RETURNS TABLE(updated_count int, error_count int) AS $$
DECLARE
    chunk_record RECORD;
    embedding_text text;
    embedding_vector vector(1024);
    updated int := 0;
    errors int := 0;
BEGIN
    -- Loop through all chunks
    FOR chunk_record IN 
        SELECT id, chunk_id, embedding
        FROM gdd_chunks
        WHERE embedding IS NOT NULL
    LOOP
        BEGIN
            -- Get embedding as text
            embedding_text := chunk_record.embedding::text;
            
            -- Check if it's already a vector (starts with '[' and is parseable)
            -- If it's a string representation of array, convert it
            IF embedding_text LIKE '[%' AND embedding_text LIKE '%]' THEN
                -- Try to cast directly to vector
                BEGIN
                    embedding_vector := embedding_text::vector(1024);
                    
                    -- Update with proper vector format
                    UPDATE gdd_chunks 
                    SET embedding = embedding_vector
                    WHERE id = chunk_record.id;
                    
                    updated := updated + 1;
                    
                    IF updated % 100 = 0 THEN
                        RAISE NOTICE 'Updated % chunks...', updated;
                    END IF;
                    
                EXCEPTION WHEN OTHERS THEN
                    errors := errors + 1;
                    IF errors <= 5 THEN
                        RAISE NOTICE 'Failed to convert chunk %: %', chunk_record.chunk_id, SQLERRM;
                    END IF;
                END;
            ELSIF pg_typeof(chunk_record.embedding)::text = 'vector' THEN
                -- Already correct, skip
                NULL;
            ELSE
                -- Unknown format, try to convert
                BEGIN
                    embedding_vector := embedding_text::vector(1024);
                    UPDATE gdd_chunks 
                    SET embedding = embedding_vector
                    WHERE id = chunk_record.id;
                    updated := updated + 1;
                EXCEPTION WHEN OTHERS THEN
                    errors := errors + 1;
                END;
            END IF;
            
        EXCEPTION WHEN OTHERS THEN
            errors := errors + 1;
        END;
    END LOOP;
    
    RETURN QUERY SELECT updated, errors;
END;
$$ LANGUAGE plpgsql;

-- Run the function
SELECT * FROM fix_embeddings();

-- Drop the temporary function
DROP FUNCTION fix_embeddings();

-- Verify the fix
-- Check embedding types (pgvector stores as 'vector' type)
SELECT 
    chunk_id,
    pg_typeof(embedding)::text as embedding_type,
    CASE 
        WHEN pg_typeof(embedding)::text = 'vector' THEN '✓ Correct (vector type)'
        ELSE '✗ Wrong type: ' || pg_typeof(embedding)::text
    END as status
FROM gdd_chunks
WHERE embedding IS NOT NULL
LIMIT 10;

-- Test vector search function
SELECT COUNT(*) as test_results
FROM match_gdd_chunks(
    (SELECT embedding FROM gdd_chunks WHERE embedding IS NOT NULL LIMIT 1),
    0.0,
    5,
    NULL
);

