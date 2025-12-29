-- Simple and aggressive fix for code_chunks chunk_type constraint
-- Run this if the comprehensive script doesn't work

-- Method 1: Try dropping by exact name first
ALTER TABLE code_chunks DROP CONSTRAINT IF EXISTS code_chunks_chunk_type_check;

-- Method 2: If that doesn't work, find and drop by searching for chunk_type in definition
DO $$
DECLARE
    constraint_record RECORD;
BEGIN
    -- Find all constraints that check chunk_type
    FOR constraint_record IN 
        SELECT conname, pg_get_constraintdef(oid) as def
        FROM pg_constraint 
        WHERE conrelid = 'code_chunks'::regclass
        AND pg_get_constraintdef(oid) LIKE '%chunk_type%'
    LOOP
        RAISE NOTICE 'Found constraint: % with definition: %', constraint_record.conname, constraint_record.def;
        EXECUTE 'ALTER TABLE code_chunks DROP CONSTRAINT IF EXISTS ' || quote_ident(constraint_record.conname) || ' CASCADE';
        RAISE NOTICE 'Dropped: %', constraint_record.conname;
    END LOOP;
END $$;

-- Method 3: Force add the new constraint (will fail if old one still exists, which is good - tells us the problem)
ALTER TABLE code_chunks 
ADD CONSTRAINT code_chunks_chunk_type_check 
CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum'));

-- Verify it worked
SELECT 
    conname,
    pg_get_constraintdef(oid) as definition
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND conname = 'code_chunks_chunk_type_check';

