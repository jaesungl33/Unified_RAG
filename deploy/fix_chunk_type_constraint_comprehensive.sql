-- Comprehensive fix for code_chunks chunk_type constraint
-- This script handles all edge cases and ensures the constraint is properly updated

-- Step 1: List ALL constraints on code_chunks table to see what we're dealing with
SELECT 
    conname as constraint_name,
    contype as constraint_type,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass
ORDER BY conname;

-- Step 2: Drop ALL possible variations of the chunk_type constraint
-- (Sometimes constraints can have slightly different names or be defined differently)
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN 
        SELECT conname 
        FROM pg_constraint 
        WHERE conrelid = 'code_chunks'::regclass 
        AND pg_get_constraintdef(oid) LIKE '%chunk_type%'
    LOOP
        EXECUTE 'ALTER TABLE code_chunks DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
        RAISE NOTICE 'Dropped constraint: %', r.conname;
    END LOOP;
END $$;

-- Step 3: Verify all chunk_type constraints are dropped
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND pg_get_constraintdef(oid) LIKE '%chunk_type%';

-- Step 4: Add the new constraint that allows all chunk types
ALTER TABLE code_chunks 
ADD CONSTRAINT code_chunks_chunk_type_check 
CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum'));

-- Step 5: Verify the new constraint
SELECT 
    conname as constraint_name,
    pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND conname = 'code_chunks_chunk_type_check';

-- Expected final result for Step 5:
-- constraint_name: code_chunks_chunk_type_check
-- constraint_definition: CHECK ((chunk_type = ANY (ARRAY['method'::text, 'class'::text, 'struct'::text, 'interface'::text, 'enum'::text])))

