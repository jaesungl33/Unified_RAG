-- Update code_chunks table to allow struct, interface, and enum chunk types
-- This migration extends the chunk_type constraint to support all C# type declarations

-- First, drop the existing constraint
ALTER TABLE code_chunks 
DROP CONSTRAINT IF EXISTS code_chunks_chunk_type_check;

-- Add new constraint that allows method, class, struct, interface, and enum
ALTER TABLE code_chunks 
ADD CONSTRAINT code_chunks_chunk_type_check 
CHECK (chunk_type IN ('method', 'class', 'struct', 'interface', 'enum'));

-- Verify the constraint
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'code_chunks'::regclass 
AND conname = 'code_chunks_chunk_type_check';

